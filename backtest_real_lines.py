#!/usr/bin/env python3
"""
BACKTEST: Using REAL DraftKings Lines + Outcomes
================================================
Uses your actual tracking data with real minimum lines and results.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"


def run_backtest():
    print("\n" + "=" * 70)
    print("🔬 BACKTEST: Real Lines from Tracking Data")
    print("=" * 70)
    
    # Load both tracking files
    all_games = []
    
    # File 1: tracking_results.csv
    f1 = DATA_DIR / "tracking_results.csv"
    if f1.exists():
        df1 = pd.read_csv(f1)
        df1 = df1[df1['status'] == 'COMPLETE'].copy()
        df1 = df1[df1['result'].isin(['WIN', 'LOSS'])].copy()
        for _, row in df1.iterrows():
            all_games.append({
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'minimum_line': row.get('minimum_total', 0),
                'expected_total': row.get('expected_total', 0),
                'confidence': row.get('confidence_pct', 0),
                'cushion': row.get('buffer', 0),
                'actual_total': row.get('actual_total', 0),
                'result': row.get('result', ''),
                'source': 'tracking_results'
            })
        print(f"✅ Loaded {len(df1)} completed games from tracking_results.csv")
    
    # File 2: mc_tracking_results.csv  
    f2 = DATA_DIR / "mc_tracking_results.csv"
    if f2.exists():
        df2 = pd.read_csv(f2)
        df2 = df2[df2['status'] == 'COMPLETE'].copy()
        df2 = df2[df2['result'].isin(['WIN', 'LOSS'])].copy()
        for _, row in df2.iterrows():
            all_games.append({
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'minimum_line': row.get('minimum_total', 0),
                'expected_total': row.get('sim_mean', 0),
                'confidence': row.get('hit_rate', 0),
                'cushion': row.get('sim_mean', 0) - row.get('minimum_total', 0),
                'actual_total': row.get('actual_total', 0),
                'result': row.get('result', ''),
                'source': 'mc_tracking'
            })
        print(f"✅ Loaded {len(df2)} completed games from mc_tracking_results.csv")
    
    if not all_games:
        print("❌ No tracking data found")
        return
    
    games_df = pd.DataFrame(all_games)
    print(f"\n📊 Total completed games with results: {len(games_df)}")
    
    # Current record
    wins = len(games_df[games_df['result'] == 'WIN'])
    losses = len(games_df[games_df['result'] == 'LOSS'])
    print(f"   Overall record: {wins}-{losses} ({wins/(wins+losses)*100:.1f}%)")
    
    # Test thresholds
    print("\n" + "=" * 70)
    print("📊 BACKTEST BY HIT RATE THRESHOLD")
    print("=" * 70)
    print(f"{'Hit Rate':<15} {'Record':<12} {'Win %':<10} {'Games':<8}")
    print("-" * 50)
    
    for hr_thresh in [80, 85, 88, 90, 92, 94, 95, 96, 97, 98, 99]:
        subset = games_df[games_df['confidence'] >= hr_thresh]
        if len(subset) >= 3:
            w = len(subset[subset['result'] == 'WIN'])
            l = len(subset[subset['result'] == 'LOSS'])
            total = w + l
            pct = (w / total) * 100 if total > 0 else 0
            print(f"{hr_thresh}%+{'':<11} {w}-{l:<9} {pct:.1f}%{'':<6} {total}")
    
    print("\n" + "=" * 70)
    print("📊 BACKTEST BY CUSHION THRESHOLD")
    print("=" * 70)
    print(f"{'Cushion':<15} {'Record':<12} {'Win %':<10} {'Games':<8}")
    print("-" * 50)
    
    for cush_thresh in [10, 15, 20, 25, 30, 35, 40]:
        subset = games_df[games_df['cushion'] >= cush_thresh]
        if len(subset) >= 3:
            w = len(subset[subset['result'] == 'WIN'])
            l = len(subset[subset['result'] == 'LOSS'])
            total = w + l
            pct = (w / total) * 100 if total > 0 else 0
            print(f"{cush_thresh}+{'':<12} {w}-{l:<9} {pct:.1f}%{'':<6} {total}")
    
    print("\n" + "=" * 70)
    print("📊 BACKTEST BY HIT RATE + CUSHION COMBO")
    print("=" * 70)
    print(f"{'Threshold':<20} {'Record':<12} {'Win %':<10} {'Games':<8}")
    print("-" * 55)
    
    combos = []
    for hr in [88, 90, 92, 94, 95, 96, 98]:
        for cush in [10, 15, 20, 25, 30]:
            subset = games_df[(games_df['confidence'] >= hr) & (games_df['cushion'] >= cush)]
            if len(subset) >= 3:
                w = len(subset[subset['result'] == 'WIN'])
                l = len(subset[subset['result'] == 'LOSS'])
                total = w + l
                pct = (w / total) * 100 if total > 0 else 0
                combos.append((hr, cush, w, l, pct, total))
    
    # Sort by win rate
    combos.sort(key=lambda x: (-x[4], -x[5]))
    
    for hr, cush, w, l, pct, total in combos[:20]:
        label = f"{hr}%+ & {cush}+ cush"
        print(f"{label:<20} {w}-{l:<9} {pct:.1f}%{'':<6} {total}")
    
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDED TIERS (based on real results)")
    print("=" * 70)
    
    # Find best tiers
    # Tier 1: Best win rate with 5+ games
    t1 = [x for x in combos if x[5] >= 5]
    if t1:
        best = t1[0]
        print(f"TIER 1 (LOCK):   {best[0]}%+ & {best[1]}+ cushion → {best[2]}-{best[3]} ({best[4]:.1f}%)")
    
    # Tier 2: 85%+ win rate with 10+ games
    t2 = [x for x in combos if x[5] >= 10 and x[4] >= 85]
    if t2:
        best = t2[0]
        print(f"TIER 2 (SAFE):   {best[0]}%+ & {best[1]}+ cushion → {best[2]}-{best[3]} ({best[4]:.1f}%)")
    
    # Tier 3: Most volume with 75%+ win rate
    t3 = [x for x in combos if x[4] >= 75]
    if t3:
        t3.sort(key=lambda x: -x[5])  # Sort by volume
        best = t3[0]
        print(f"TIER 3 (VOLUME): {best[0]}%+ & {best[1]}+ cushion → {best[2]}-{best[3]} ({best[4]:.1f}%)")
    
    # Show losses
    print("\n" + "=" * 70)
    print("❌ LOSS ANALYSIS")
    print("=" * 70)
    
    losses_df = games_df[games_df['result'] == 'LOSS'].copy()
    losses_df = losses_df.sort_values('confidence', ascending=False)
    
    print(f"\nAll {len(losses_df)} losses:\n")
    for _, row in losses_df.iterrows():
        miss_by = row['minimum_line'] - row['actual_total']
        print(f"   {row['away_team'][:22]:<22} @ {row['home_team'][:22]:<22}")
        print(f"      HR: {row['confidence']:.1f}% | Cushion: {row['cushion']:.1f}")
        print(f"      Line: {row['minimum_line']} | Actual: {row['actual_total']:.0f} | Missed by: {miss_by:.1f}")
        print()


if __name__ == "__main__":
    run_backtest()
