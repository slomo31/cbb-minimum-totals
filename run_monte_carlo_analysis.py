#!/usr/bin/env python3
"""
CBB MINIMUM TOTALS - MONTE CARLO ANALYSIS RUNNER
=================================================
Quick script to run Monte Carlo analysis on today's games.

Usage:
    python run_monte_carlo_analysis.py
    
Or with custom simulation count:
    python run_monte_carlo_analysis.py --sims 10000
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from monte_carlo_cbb import MonteCarloSimulator


def main():
    parser = argparse.ArgumentParser(description='Run Monte Carlo analysis on CBB games')
    parser.add_argument('--sims', type=int, default=5000, 
                        help='Number of simulations per game (default: 5000)')
    parser.add_argument('--games-file', type=str, default=None,
                        help='Path to upcoming games CSV')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🎲 CBB MINIMUM TOTALS - MONTE CARLO SIMULATOR")
    print("=" * 70)
    
    # Initialize simulator
    data_dir = Path(__file__).parent / 'data'
    games_csv = data_dir / 'ncaa_games_history.csv'
    
    if not games_csv.exists():
        print(f"\n❌ Game history not found at {games_csv}")
        print("   Run first: python data_collection/ncaa_stats_fetcher.py")
        return
    
    simulator = MonteCarloSimulator(str(games_csv))
    
    # Load today's games
    if args.games_file:
        upcoming_file = Path(args.games_file)
    else:
        upcoming_file = data_dir / 'upcoming_games.csv'
    
    if not upcoming_file.exists():
        print(f"\n❌ Upcoming games not found at {upcoming_file}")
        print("   Run first: python data_collection/odds_minimum_fetcher.py")
        print("\n   Or run the full workflow:")
        print("   python master_workflow.py")
        return
    
    import pandas as pd
    df = pd.read_csv(upcoming_file)
    
    # Filter to games with alternate totals
    if 'has_alternate' in df.columns:
        df = df[df['has_alternate'] == True]
    
    if len(df) == 0:
        print("\n⚠️ No games with alternate totals found")
        return
    
    print(f"\n📊 Found {len(df)} games with alternate totals")
    print(f"🎲 Running {args.sims:,} simulations per game...\n")
    
    # Convert to list of dicts
    games = df.to_dict('records')
    
    # Run analysis
    results, summary = simulator.evaluate_all_games(games, n_simulations=args.sims)
    
    # Print report
    simulator.print_report(results, summary)
    
    # Save results
    output_file = data_dir / 'monte_carlo_results.csv'
    results_df = pd.DataFrame([{
        'away_team': r['away_team'],
        'home_team': r['home_team'],
        'minimum_total': r['minimum_total'],
        'standard_total': r['standard_total'],
        'decision': r['decision'],
        'hit_rate': r['hit_rate'],
        'main_line_proximity': r['main_line_proximity'],
        'sim_mean': r['sim_mean'],
        'sim_min': r['sim_min'],
        'sim_max': r['sim_max'],
        'data_quality': r['data_quality'],
    } for r in results])
    
    results_df.to_csv(output_file, index=False)
    print(f"\n💾 Results saved to {output_file}")


if __name__ == "__main__":
    main()
