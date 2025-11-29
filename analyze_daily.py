#!/usr/bin/env python3
"""
Daily Analysis Script for CBB Minimum System Backtest Results

Analyzes:
- Picks per day distribution
- Multi-pick day records (like today's 3-1)
- Best/worst days
- Day of week patterns
"""

import csv
import sys
from collections import defaultdict
from datetime import datetime

def analyze_daily_results(csv_file: str):
    """Analyze backtest results by day."""
    
    # Load results
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        results = list(reader)
    
    # Filter to YES picks only
    yes_picks = [r for r in results if r['decision'] == 'YES']
    
    # Group by date
    daily = defaultdict(list)
    for r in yes_picks:
        daily[r['date']].append(r)
    
    print("=" * 70)
    print("📊 DAILY ANALYSIS - YES PICKS")
    print("=" * 70)
    
    # === PICKS PER DAY DISTRIBUTION ===
    print("\n📈 PICKS PER DAY DISTRIBUTION")
    print("-" * 50)
    
    picks_count = defaultdict(int)
    for date, picks in daily.items():
        picks_count[len(picks)] += 1
    
    for num_picks in sorted(picks_count.keys()):
        days = picks_count[num_picks]
        print(f"  {num_picks} picks: {days} days")
    
    total_days = len(daily)
    total_picks = len(yes_picks)
    print(f"\n  Average: {total_picks/total_days:.1f} picks/day")
    
    # === DAILY RECORDS ===
    print("\n📅 DAILY RECORDS (Days with 2+ picks)")
    print("-" * 70)
    
    multi_pick_days = [(date, picks) for date, picks in daily.items() if len(picks) >= 2]
    multi_pick_days.sort(key=lambda x: x[0])
    
    daily_records = defaultdict(int)  # "3-1" -> count
    
    for date, picks in multi_pick_days:
        wins = sum(1 for p in picks if p['hit'] == 'True')
        losses = len(picks) - wins
        record = f"{wins}-{losses}"
        daily_records[record] += 1
        
        # Show details for days with losses
        if losses > 0:
            pct = wins / len(picks) * 100
            print(f"  {date}: {record} ({pct:.0f}%)")
            for p in picks:
                status = "✅" if p['hit'] == 'True' else "❌"
                missed = float(p['minimum']) - float(p['actual']) if p['hit'] == 'False' else 0
                miss_str = f" (missed by {missed:.1f})" if missed > 0 else ""
                print(f"    {status} {p['away'][:20]} @ {p['home'][:20]}: {p['actual']} vs {p['minimum']}{miss_str}")
    
    print("\n📊 MULTI-PICK DAY SUMMARY")
    print("-" * 50)
    
    # Sort by record quality
    perfect_days = 0
    loss_days = 0
    
    for record, count in sorted(daily_records.items(), key=lambda x: (-int(x[0].split('-')[0]), int(x[0].split('-')[1]))):
        wins, losses = map(int, record.split('-'))
        total = wins + losses
        pct = wins / total * 100
        status = "✅" if losses == 0 else "⚠️"
        print(f"  {status} {record}: {count} days ({pct:.0f}% win rate)")
        
        if losses == 0:
            perfect_days += count
        else:
            loss_days += count
    
    print(f"\n  Perfect days: {perfect_days}")
    print(f"  Days with losses: {loss_days}")
    
    # === WORST DAYS ===
    print("\n❌ WORST DAYS (Most losses)")
    print("-" * 50)
    
    worst_days = []
    for date, picks in daily.items():
        wins = sum(1 for p in picks if p['hit'] == 'True')
        losses = len(picks) - wins
        if losses > 0:
            worst_days.append((date, wins, losses, picks))
    
    worst_days.sort(key=lambda x: (-x[2], -len(x[3])))  # Sort by losses desc, then total picks
    
    for date, wins, losses, picks in worst_days[:10]:
        print(f"  {date}: {wins}-{losses}")
        for p in picks:
            if p['hit'] == 'False':
                missed = float(p['minimum']) - float(p['actual'])
                print(f"    ❌ {p['away'][:18]} @ {p['home'][:18]}: missed by {missed:.1f}")
    
    # === DAY OF WEEK ANALYSIS ===
    print("\n📆 DAY OF WEEK ANALYSIS")
    print("-" * 50)
    
    dow_stats = defaultdict(lambda: {'picks': 0, 'wins': 0})
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    for r in yes_picks:
        date_obj = datetime.strptime(r['date'], '%Y-%m-%d')
        dow = date_obj.weekday()
        dow_stats[dow]['picks'] += 1
        if r['hit'] == 'True':
            dow_stats[dow]['wins'] += 1
    
    for dow in range(7):
        stats = dow_stats[dow]
        if stats['picks'] > 0:
            losses = stats['picks'] - stats['wins']
            pct = stats['wins'] / stats['picks'] * 100
            print(f"  {dow_names[dow]}: {stats['picks']:3} picks, {stats['wins']}-{losses} ({pct:.1f}%)")
    
    # === LOSING STREAKS ===
    print("\n📉 LOSS PATTERNS")
    print("-" * 50)
    
    # Check for consecutive losses
    sorted_picks = sorted(yes_picks, key=lambda x: (x['date'], x['home']))
    
    current_streak = 0
    max_streak = 0
    streak_start = None
    
    for p in sorted_picks:
        if p['hit'] == 'False':
            if current_streak == 0:
                streak_start = p['date']
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    print(f"  Max consecutive losses: {max_streak}")
    
    # Back-to-back loss days
    loss_dates = set()
    for date, picks in daily.items():
        if any(p['hit'] == 'False' for p in picks):
            loss_dates.add(date)
    
    sorted_loss_dates = sorted(loss_dates)
    back_to_back = 0
    for i in range(1, len(sorted_loss_dates)):
        d1 = datetime.strptime(sorted_loss_dates[i-1], '%Y-%m-%d')
        d2 = datetime.strptime(sorted_loss_dates[i], '%Y-%m-%d')
        if (d2 - d1).days == 1:
            back_to_back += 1
    
    print(f"  Back-to-back loss days: {back_to_back}")
    
    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("📊 OVERALL SUMMARY")
    print("=" * 70)
    
    total_wins = sum(1 for p in yes_picks if p['hit'] == 'True')
    total_losses = len(yes_picks) - total_wins
    
    print(f"  Total picks: {len(yes_picks)}")
    print(f"  Record: {total_wins}-{total_losses} ({total_wins/len(yes_picks)*100:.1f}%)")
    print(f"  Days with picks: {len(daily)}")
    print(f"  Avg picks/day: {len(yes_picks)/len(daily):.1f}")
    print(f"  Days with losses: {len(loss_dates)}")
    print(f"  Perfect days: {len(daily) - len(loss_dates)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to most recent backtest
        csv_file = "backtest_results_2025_26.csv"
    else:
        csv_file = sys.argv[1]
    
    analyze_daily_results(csv_file)
