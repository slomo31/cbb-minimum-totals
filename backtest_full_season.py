#!/usr/bin/env python3
"""
BACKTEST: Full 2024-25 Season with CORRECT season ratings
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
import requests

DATA_DIR = Path(__file__).parent / "data"


def load_2024_25_ratings():
    """Load 2024-25 season ratings from Barttorvik."""
    print("📥 Fetching 2024-25 season ratings...")
    
    url = "https://barttorvik.com/2025_team_results.json"
    response = requests.get(url, timeout=30)
    data = response.json()
    
    team_stats = {}
    for record in data:
        name = record[1].lower().strip()  # Team name at index 1
        team_stats[name] = {
            'adj_o': record[4],   # Adj O
            'adj_d': record[6],   # Adj D
            'adj_t': record[44],  # Tempo
        }
    
    print(f"✅ Loaded 2024-25 ratings: {len(team_stats)} teams")
    return team_stats


def load_games():
    """Load full season games."""
    games_file = DATA_DIR / "barttorvik_2024_25_games.csv"
    games_df = pd.read_csv(games_file) if games_file.exists() else pd.DataFrame()
    print(f"✅ Loaded 2024-25 games: {len(games_df)} games")
    return games_df


def calculate_team_variances(games_df):
    """Calculate team scoring variances."""
    team_variances = {}
    
    home_stats = games_df.groupby('home_team')['home_score'].agg(['std', 'count'])
    away_stats = games_df.groupby('away_team')['away_score'].agg(['std', 'count'])
    
    for team in set(home_stats.index) | set(away_stats.index):
        stds = []
        if team in home_stats.index and home_stats.loc[team, 'count'] >= 3:
            stds.append(home_stats.loc[team, 'std'])
        if team in away_stats.index and away_stats.loc[team, 'count'] >= 3:
            stds.append(away_stats.loc[team, 'std'])
        
        if stds:
            team_variances[team.lower().strip()] = np.mean(stds)
    
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


def simulate_game(home_team, away_team, team_stats, team_variances, n_sims=5000):
    """Run Monte Carlo simulation."""
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
    print("🔬 BACKTEST: Full 2024-25 Season (Correct Ratings)")
    print("=" * 70)
    
    team_stats = load_2024_25_ratings()
    games_df = load_games()
    
    if games_df.empty:
        print("❌ No game data found")
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
        
        # Minimum line = standard - 12
        estimated_standard = round(sim_mean * 2) / 2
        minimum_line = estimated_standard - 12
        
        hit_rate = (np.sum(totals > minimum_line) / len(totals)) * 100
        cushion = sim_mean - minimum_line
        hit_over = actual_total > minimum_line
        
        all_results.append({
            'date': game['date'],
            'home_team': home_team,
            'away_team': away_team,
            'actual_total': actual_total,
            'minimum_line': minimum_line,
            'sim_mean': round(sim_mean, 1),
            'hit_rate': round(hit_rate, 1),
            'cushion': round(cushion, 1),
            'hit_over': hit_over,
        })
        
        for hr in [85, 88, 90, 92, 94, 95, 96, 97, 98, 99]:
            for cush in [10, 15, 20, 25]:
                if hit_rate >= hr and cushion >= cush:
                    key = (hr, cush)
                    if hit_over:
                        threshold_results[key]['wins'] += 1
                    else:
                        threshold_results[key]['losses'] += 1
        
        if (i + 1) % 500 == 0:
            print(f"   Processed {i + 1}/{len(games_df)} games...")
    
    print("\n" + "=" * 70)
    print("📊 BACKTEST RESULTS BY THRESHOLD")
    print("=" * 70)
    print(f"{'Threshold':<20} {'Record':<15} {'Win %':<12} {'Games':<10}")
    print("-" * 60)
    
    sorted_results = []
    for (hr, cush), data in threshold_results.items():
        total = data['wins'] + data['losses']
        if total >= 20:
            win_pct = (data['wins'] / total) * 100
            sorted_results.append((hr, cush, data['wins'], data['losses'], win_pct, total))
    
    sorted_results.sort(key=lambda x: (-x[4], -x[5]))
    
    for hr, cush, w, l, pct, total in sorted_results:
        label = f"{hr}%+ & {cush}+ cush"
        print(f"{label:<20} {w}-{l:<12} {pct:.1f}%{'':<8} {total}")
    
    # Hit rate only
    print("\n" + "=" * 70)
    print("📊 HIT RATE ONLY (ignoring cushion)")
    print("=" * 70)
    
    results_df = pd.DataFrame(all_results)
    
    for hr_thresh in [85, 88, 90, 92, 94, 95, 96, 97, 98, 99]:
        subset = results_df[results_df['hit_rate'] >= hr_thresh]
        if len(subset) >= 20:
            w = subset['hit_over'].sum()
            l = len(subset) - w
            pct = (w / len(subset)) * 100
            print(f"{hr_thresh}%+{'':<15} {int(w)}-{int(l):<12} {pct:.1f}%{'':<8} {len(subset)}")
    
    # Recommended tiers
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDED TIERS")
    print("=" * 70)
    
    if sorted_results:
        t1 = [x for x in sorted_results if x[5] >= 50]
        if t1:
            best = t1[0]
            print(f"TIER 1 (LOCK):   {best[0]}%+ & {best[1]}+ cushion → {best[2]}-{best[3]} ({best[4]:.1f}%) [{best[5]} games]")
        
        t2 = [x for x in sorted_results if x[5] >= 100 and x[4] >= 85]
        if t2:
            best = t2[0]
            print(f"TIER 2 (SAFE):   {best[0]}%+ & {best[1]}+ cushion → {best[2]}-{best[3]} ({best[4]:.1f}%) [{best[5]} games]")
        
        t3 = [x for x in sorted_results if x[5] >= 200 and x[4] >= 80]
        if t3:
            best = t3[0]
            print(f"TIER 3 (VOLUME): {best[0]}%+ & {best[1]}+ cushion → {best[2]}-{best[3]} ({best[4]:.1f}%) [{best[5]} games]")
    
    results_df.to_csv(DATA_DIR / "backtest_full_season_detailed.csv", index=False)
    print(f"\n💾 Saved to data/backtest_full_season_detailed.csv")


if __name__ == "__main__":
    run_backtest()
