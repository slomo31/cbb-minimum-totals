#!/usr/bin/env python3
"""
CBB MINIMUM TOTALS - MASTER WORKFLOW (MONTE CARLO VERSION)
==========================================================
Complete workflow: fetch data → run Monte Carlo → output picks

Usage:
    python master_workflow_mc.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    print("=" * 70)
    print("🏀 CBB MINIMUM TOTALS SYSTEM - MONTE CARLO EDITION")
    print(f"   {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print("=" * 70)
    
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # Step 1: Update NCAA game history (incremental)
    print("\n📥 STEP 1: Updating team statistics...")
    print("-" * 50)
    
    try:
        from data_collection.ncaa_stats_fetcher import NCAAStatsFetcher
        fetcher = NCAAStatsFetcher()
        fetcher.fetch_incremental()
        print("   ✅ Team stats updated")
    except Exception as e:
        print(f"   ⚠️ Could not update stats: {e}")
        print("   Continuing with existing data...")
    
    # Check if we have game history
    games_csv = data_dir / 'ncaa_games_history.csv'
    if not games_csv.exists():
        print(f"\n❌ No game history found at {games_csv}")
        print("   Run: python data_collection/ncaa_stats_fetcher.py")
        return
    
    # Step 2: Fetch today's odds
    print("\n📥 STEP 2: Fetching today's odds from DraftKings...")
    print("-" * 50)
    
    try:
        from data_collection.odds_minimum_fetcher import OddsMinimumFetcher
        odds_fetcher = OddsMinimumFetcher()
        games_df = odds_fetcher.fetch_all_games_with_minimums(max_alt_lookups=100)
        
        if games_df.empty:
            print("   ⚠️ No games found for today")
            return
        
        # Filter to games with alternates
        if 'has_alternate' in games_df.columns:
            games_df = games_df[games_df['has_alternate'] == True]
        
        print(f"   ✅ Found {len(games_df)} games with alternate totals")
        
    except Exception as e:
        print(f"   ❌ Error fetching odds: {e}")
        
        # Try loading from file
        upcoming_file = data_dir / 'upcoming_games.csv'
        if upcoming_file.exists():
            import pandas as pd
            games_df = pd.read_csv(upcoming_file)
            if 'has_alternate' in games_df.columns:
                games_df = games_df[games_df['has_alternate'] == True]
            print(f"   ℹ️ Loaded {len(games_df)} games from cached file")
        else:
            print("   ❌ No cached games found. Cannot continue.")
            return
    
    # Step 3: Run Monte Carlo analysis
    print("\n🎲 STEP 3: Running Monte Carlo simulation...")
    print("-" * 50)
    
    from monte_carlo_cbb import MonteCarloSimulator
    
    simulator = MonteCarloSimulator(str(games_csv))
    games = games_df.to_dict('records')
    
    # Run with 5000 sims (balance of speed and accuracy)
    results, summary = simulator.evaluate_all_games(games, n_simulations=5000)
    
    # Step 4: Print report
    print("\n📊 STEP 4: Analysis Results")
    simulator.print_report(results, summary)
    
    # Step 5: Save results
    print("\n💾 STEP 5: Saving results...")
    print("-" * 50)
    
    import pandas as pd
    
    results_df = pd.DataFrame([{
        'game_time': g.get('game_time', ''),
        'away_team': r['away_team'],
        'home_team': r['home_team'],
        'standard_total': r['standard_total'],
        'minimum_total': r['minimum_total'],
        'decision': r['decision'],
        'hit_rate': round(r['hit_rate'], 1),
        'sim_mean': round(r['sim_mean'], 1),
        'sim_range': f"{r['sim_min']:.0f}-{r['sim_max']:.0f}",
        'data_quality': r['data_quality'],
    } for r, g in zip(results, games)])
    
    # Save to CSV
    output_file = data_dir / 'monte_carlo_picks.csv'
    results_df.to_csv(output_file, index=False)
    print(f"   ✅ Saved to {output_file}")
    
    # Also save just YES picks for quick reference
    yes_picks = results_df[results_df['decision'] == 'YES']
    if len(yes_picks) > 0:
        yes_file = data_dir / 'yes_picks_today.csv'
        yes_picks.to_csv(yes_file, index=False)
        print(f"   ✅ YES picks saved to {yes_file}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print(f"   🟢 YES picks: {summary['yes_count']}")
    print(f"   🟡 MAYBE picks: {summary['maybe_count']}")
    print(f"   🔴 SKIP: {summary['no_count']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
