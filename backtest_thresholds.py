#!/usr/bin/env python3
"""
BACKTEST: Find Optimal Elite Thresholds
========================================
Uses historical-variance Monte Carlo to simulate what thresholds
would have worked on the 1,390 completed games.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"


def load_data():
    """Load Barttorvik stats and game history."""
    bart_file = DATA_DIR / "barttorvik_stats.csv"
    team_stats = {}
    if bart_file.exists():
        df = pd.read_csv(bart_file)
        for _, row in df.iterrows():
            name = row.get('team', '').lower().strip()
            team_stats[name] = {
                'adj_o': row.get('adj_o', 100),
                'adj_d': row.get('adj_d', 100),
                'adj_t': row.get('adj_tempo', 68),
            }
        print(f"✅ Loaded Barttorvik data: {len(team_stats)} teams")
    
    games_file = DATA_DIR / "ncaa_games_history.csv"
    games_df = pd.read_csv(games_file) if games_file.exists() else pd.DataFrame()
    print(f"✅ Loaded game history: {len(games_df)} games")
    
    return team_stats, games_df


def calculate_team_variances(games_df):
    """Calculate team scoring variances from game history."""
    team_variances = {}
    
    if 'home_team' in games_df.columns:
        home_vars = games_df.groupby('home_team')['home_score'].agg(['std', 'count'])
        for team, row in home_vars.iterrows():
            if row['count'] >= 3 and pd.notna(row['std']):
                team_variances[team.lower().strip()] = row['std']
    
    if 'away_team' in games_df.columns:
        away_vars = games_df.groupby('away_team')['away_score'].agg(['std', 'count'])
        for team, row in away_vars.iterrows():
            if row['count'] >= 3 and pd.notna(row['std']):
                name = team.lower().strip()
                if name in team_variances:
                    team_variances[name] = (team_variances[name] + row['std']) / 2
                else:
                    team_variances[name] = row['std']
    
    print(f"✅ Calculated variances for {len(team_variances)} teams")
    return team_variances


def find_team(name, team_stats):
    name_lower = name.lower().strip()
    if name_lower in team_stats:
        return team_stats[name_lower]
    for key, stats in team_stats.items():
        if name_lower in key or key in name_lower:
            return stats
    return {'adj_o': 100, 'adj_d': 100, 'adj_t': 68}


def get_team_std(name, team_variances):
    name_lower = name.lower().strip()
    if name_lower in team_variances:
        return team_variances[name_lower]
    for key, std in team_variances.items():
        if name_lower in key or key in name_lower:
            return std
    return 12.0


def simulate_game(home_team, away_team, team_stats, team_variances, n_sims=10000):
    home_stats = find_team(home_team, team_stats)
    away_stats = find_team(away_team, team_stats)
    
    home_std = get_team_std(home_team, team_variances)
    away_std = get_team_std(away_team, team_variances)
    
    avg_tempo = (home_stats['adj_t'] + away_stats['adj_t']) / 2
    
    home_off = (home_stats['adj_o'] * away_stats['adj_d']) / 100
    home_expected = (home_off / 100) * avg_tempo + 2
    
    away_off = (away_stats['adj_o'] * home_stats['adj_d']) / 100
    away_expected = (away_off / 100) * avg_tempo - 2
    
    home_scores = np.clip(np.random.normal(home_expected, home_std, n_sims), 35, 130)
    away_scores = np.clip(np.random.normal(away_expected, away_std, n_sims), 35, 130)
    
    return home_scores + away_scores


def run_backtest():
    print("\n" + "=" * 70)
    print("🔬 BACKTEST: Finding Optimal Elite Thresholds")
    print("=" * 70)
    
    team_stats, games_df = load_data()
    if games_df.empty:
        print("❌ No game history found")
        return
    
    team_variances = calculate_team_variances(games_df)
    
    threshold_results = defaultdict(lambda: {'wins': 0, 'losses': 0})
    all_results = []
    
    print(f"\n🎲 Running simulations on {len(games_df)} games...")
    
    for i, game in games_df.iterrows():
        home_team = game['home_team']
        away_team = game['away_team']
        actual_total = game['total_points']
        
        totals = simulate_game(home_team, away_team, team_stats, team_variances)
        sim_mean = np.mean(totals)
        
        # Minimum line = estimated standard - 12
        estimated_standard = round(sim_mean / 0.5) * 0.5
        minimum_line = estimated_standard - 12
        
        hit_rate = (np.sum(totals > minimum_line) / len(totals)) * 100
        cushion = sim_mean - minimum_line
        hit_over = actual_total > minimum_line
        
        all_results.append({
            'home_team': home_team, 'away_team': away_team,
            'actual_total': actual_total, 'minimum_line': minimum_line,
            'sim_mean': sim_mean, 'hit_rate': hit_rate,
            'cushion': cushion, 'hit_over': hit_over,
        })
        
        for hr in [88, 90, 92, 94, 95, 96, 97, 98]:
            for cush in [10, 15, 20, 25, 30]:
                if hit_rate >= hr and cushion >= cush:
                    key = (hr, cush)
                    if hit_over:
                        threshold_results[key]['wins'] += 1
                    else:
                        threshold_results[key]['losses'] += 1
        
        if (i + 1) % 300 == 0:
            print(f"   Processed {i + 1}/{len(games_df)} games...")
    
    print("\n" + "=" * 70)
    print("📊 BACKTEST RESULTS BY THRESHOLD")
    print("=" * 70)
    print(f"{'Hit Rate':<12} {'Cushion':<10} {'Record':<12} {'Win %':<10} {'Games':<8}")
    print("-" * 70)
    
    sorted_results = []
    for (hr, cush), data in threshold_results.items():
        total = data['wins'] + data['losses']
        if total >= 10:
            win_pct = (data['wins'] / total) * 100
            sorted_results.append((hr, cush, data['wins'], data['losses'], win_pct, total))
    
    sorted_results.sort(key=lambda x: (-x[4], -x[5]))
    
    for hr, cush, wins, losses, win_pct, total in sorted_results:
        print(f"{hr}%+{'':<8} {cush}+{'':<7} {wins}-{losses:<8} {win_pct:.1f}%{'':<6} {total}")
    
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDED NEW TIERS")
    print("=" * 70)
    
    # Tier 1: Best win rate, 20+ games
    t1 = [x for x in sorted_results if x[5] >= 20]
    if t1:
        print(f"TIER 1 (LOCK):   {t1[0][0]}%+ & {t1[0][1]}+ cushion → {t1[0][2]}-{t1[0][3]} ({t1[0][4]:.1f}%)")
    
    # Tier 2: 85%+ win rate, 50+ games
    t2 = [x for x in sorted_results if x[5] >= 50 and x[4] >= 85]
    if t2:
        print(f"TIER 2 (SAFE):   {t2[0][0]}%+ & {t2[0][1]}+ cushion → {t2[0][2]}-{t2[0][3]} ({t2[0][4]:.1f}%)")
    
    # Tier 3: 80%+ win rate, 100+ games
    t3 = [x for x in sorted_results if x[5] >= 100 and x[4] >= 80]
    if t3:
        print(f"TIER 3 (VOLUME): {t3[0][0]}%+ & {t3[0][1]}+ cushion → {t3[0][2]}-{t3[0][3]} ({t3[0][4]:.1f}%)")
    
    # Save results
    pd.DataFrame(all_results).to_csv(DATA_DIR / "backtest_detailed.csv", index=False)
    print(f"\n💾 Saved to data/backtest_detailed.csv")


if __name__ == "__main__":
    run_backtest()
