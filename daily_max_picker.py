#!/usr/bin/env python3
"""
CBB ELITE MAXIMUM (UNDER) DAILY PICKER V1
==========================================
Finds today's elite under picks for parlays.

Maximum line = Standard total + 12 (DraftKings alternate)

Usage:
    python daily_max_picker.py
    python daily_max_picker.py --date 2025-01-15
"""

import sys
import argparse
from datetime import datetime
import requests
import pandas as pd
from pathlib import Path

# Import Monte Carlo engine and filter
from monte_carlo_max import MonteCarloMaxSimulator
from elite_cbb_max_v1 import EliteCBBMaxFilter

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"


def fetch_todays_odds(date_str: str = None) -> list:
    """Fetch today's odds from The Odds API."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if date_str == today:
        url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',
            'markets': 'totals',
            'bookmakers': 'draftkings'
        }
    else:
        url = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',
            'markets': 'totals',
            'date': f"{date_str}T12:00:00Z",
            'bookmakers': 'draftkings'
        }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        print(f"📡 API calls remaining: {remaining}")
        
        if date_str == today:
            data = response.json()
        else:
            data = response.json().get('data', [])
        
        return data
    except Exception as e:
        print(f"❌ Error fetching odds: {e}")
        return []


def parse_games_with_maximums(odds_data: list) -> list:
    """Parse odds data to extract games with maximum lines."""
    games = []
    
    for game in odds_data:
        game_info = {
            'home_team': game.get('home_team', ''),
            'away_team': game.get('away_team', ''),
            'commence_time': game.get('commence_time', ''),
        }
        
        for bookmaker in game.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market.get('key') == 'totals':
                    for outcome in market.get('outcomes', []):
                        if outcome.get('name') == 'Over':
                            standard_total = outcome.get('point')
                            if standard_total:
                                game_info['standard_total'] = standard_total
                                # Maximum is standard + 12
                                game_info['maximum_total'] = standard_total + 12
                            break
        
        if game_info.get('maximum_total'):
            games.append(game_info)
    
    return games


def run_daily_max_picker(date_str: str = None):
    """Run the daily maximum (under) picker."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print("\n" + "=" * 70)
    print(f"🏀 CBB ELITE MAXIMUM (UNDER) PICKER V1 - {date_str}")
    print("=" * 70)
    
    # Initialize
    sim = MonteCarloMaxSimulator()
    elite_filter = EliteCBBMaxFilter()
    
    print(f"\n📊 Filters: Sim ≥ 155 & HR 80-90% (blowout risks excluded)")
    print(f"   Looking for games that WON'T exceed maximum lines")
    
    # Fetch odds
    print(f"\n📡 Fetching odds...")
    odds_data = fetch_todays_odds(date_str)
    
    if not odds_data:
        print("❌ No odds data available")
        return []
    
    games = parse_games_with_maximums(odds_data)
    print(f"   Found {len(games)} games with lines")
    
    # Evaluate each game
    print(f"\n🎲 Running Monte Carlo simulations...")
    
    all_results = []
    
    for i, game in enumerate(games):
        # Run simulation
        result = sim.evaluate_under(
            home_team=game['home_team'],
            away_team=game['away_team'],
            maximum_total=game['maximum_total'],
            standard_total=game['standard_total'],
            n_simulations=10000
        )
        
        # Check elite filter
        elite_result = elite_filter.evaluate(
            home_team=game['home_team'],
            away_team=game['away_team'],
            under_hit_rate=result['under_hit_rate'],
            sim_mean=result['sim_mean'],
            maximum_line=game['maximum_total'],
            date_str=date_str
        )
        
        game_result = {
            **game,
            'under_hit_rate': result['under_hit_rate'],
            'sim_mean': result['sim_mean'],
            'cushion': result['cushion'],
            'tier': elite_result['tier'],
            'tier_label': elite_result['tier_label'],
            'elite_reason': elite_result['reason'],
        }
        
        all_results.append(game_result)
        
        if (i + 1) % 20 == 0:
            print(f"   Processed {i + 1}/{len(games)} games...")
    
    # Print results
    print("\n" + "=" * 70)
    print(f"🎯 CBB ELITE MAXIMUM (UNDER) PICKS")
    print("=" * 70)
    print("TIERS (backtested on 1,390 games):")
    print("  🔒 TIER 1: Sim ≥ 155 & HR 80-85% → 106-10 (91.4%)")
    print("  ✅ TIER 2: Sim ≥ 160 & HR 80-88% → 56-9 (86.2%)")
    print("  ⚠️ TIER 3: Max line ≥ 165 & HR 80%+ → 150-18 (89.3%)")
    print("=" * 70)
    
    # Get qualified picks
    qualified = [r for r in all_results if r.get('tier')]
    
    if not qualified:
        print("\n   ⚠️  No qualified picks today (none meet 98%+ & 35+ cushion)")
        print("   Wait for better opportunities.")
        
        # Show near misses
        near_misses = [r for r in all_results 
                      if r['under_hit_rate'] >= 97 and r['cushion'] >= 30
                      and not r.get('tier')]
        
        if near_misses:
            print(f"\n   📋 Near Misses ({len(near_misses)}):")
            for r in sorted(near_misses, key=lambda x: x['under_hit_rate'], reverse=True)[:5]:
                print(f"      {r['away_team'][:20]} @ {r['home_team'][:20]}")
                print(f"         {r['under_hit_rate']:.1f}% | Cushion: {r['cushion']:.1f} | {r['elite_reason']}")
    else:
        # Group by tier
        for tier in [1, 2, 3]:
            tier_picks = [r for r in qualified if r['tier'] == tier]
            if tier_picks:
                tier_labels = {
                    1: '🔒 TIER 1 - BEST (91.4%)',
                    2: '✅ TIER 2 - SAFE (86.2%)',
                    3: '⚠️ TIER 3 - VOLUME (89.3%)',
                }
                print(f"\n{tier_labels[tier]} - {len(tier_picks)} pick(s)\n")
                
                for pick in sorted(tier_picks, key=lambda x: x['under_hit_rate'], reverse=True):
                    print(f"   {pick['away_team'][:25]:25} @ {pick['home_team'][:25]}")
                    print(f"      UNDER {pick['maximum_total']} maximum")
                    print(f"      Under Rate: {pick['under_hit_rate']:.1f}%")
                    print(f"      Sim Mean: {pick['sim_mean']:.1f} (Cushion: {pick['cushion']:.1f})")
                    print(f"      Standard Line: {pick['standard_total']}")
                    print()
    
    print("=" * 70)
    print("💡 TIP: Combine with minimum picks for balanced parlay exposure")
    print("=" * 70)
    
    # Save to CSV
    save_max_picks_csv(all_results, date_str)
    
    return qualified


def save_max_picks_csv(all_results: list, date_str: str):
    """Save maximum picks to CSV for dashboard."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    rows = []
    for r in all_results:
        rows.append({
            'date': date_str,
            'game_time': r.get('commence_time', ''),
            'away_team': r['away_team'],
            'home_team': r['home_team'],
            'standard_total': r['standard_total'],
            'maximum_total': r['maximum_total'],
            'under_hit_rate': round(r['under_hit_rate'], 1),
            'sim_mean': round(r['sim_mean'], 1),
            'cushion': round(r['cushion'], 1),
            'tier': r.get('tier') or 0,
            'tier_label': r.get('tier_label', 'NO BET'),
            'reason': r.get('elite_reason', ''),
        })
    
    df = pd.DataFrame(rows)
    
    # Sort: qualified first, then by under_hit_rate
    df['sort_key'] = df['tier'].apply(lambda x: x if x > 0 else 99)
    df = df.sort_values(['sort_key', 'under_hit_rate'], ascending=[True, False])
    df = df.drop('sort_key', axis=1)
    
    csv_path = data_dir / "max_picks.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Saved {len(df)} games to {csv_path}")
    print(f"   Qualified picks: {len(df[df['tier'] > 0])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CBB Elite Maximum (Under) Daily Picker')
    parser.add_argument('--date', type=str, help='Date to check (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    
    run_daily_max_picker(args.date)