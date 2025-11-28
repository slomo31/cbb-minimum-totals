#!/usr/bin/env python3
"""
CBB MINIMUM TOTALS - MASTER WORKFLOW V3
=======================================
Complete workflow: 
1. Refresh Barttorvik data (daily)
2. Update game history (incremental)
3. Fetch today's odds
4. Run Monte Carlo V3 simulation
5. Output picks

Usage:
    python master_workflow_mc.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent / 'data'


def should_refresh_barttorvik() -> bool:
    """Check if Barttorvik data needs refresh (once per day)."""
    bt_file = DATA_DIR / 'barttorvik_stats.csv'
    refresh_log = DATA_DIR / 'barttorvik_refresh.json'
    
    if not bt_file.exists():
        return True
    
    if refresh_log.exists():
        try:
            with open(refresh_log) as f:
                log = json.load(f)
                last_refresh = datetime.fromisoformat(log.get('last_refresh', '2000-01-01'))
                # Refresh if last refresh was before today
                if last_refresh.date() < datetime.now().date():
                    return True
                return False
        except:
            return True
    
    return True


def refresh_barttorvik():
    """Fetch fresh Barttorvik data."""
    import requests
    import pandas as pd
    
    url = "https://barttorvik.com/2026_team_results.json"
    
    print("   Fetching from Barttorvik...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"   Retrieved {len(data)} teams")
        
        # Column mapping
        COLUMNS = {
            0: 'rank', 1: 'team', 2: 'conference', 3: 'record',
            4: 'adj_o', 5: 'adj_o_rank', 6: 'adj_d', 7: 'adj_d_rank',
            8: 'barthag', 9: 'barthag_rank', 10: 'efg_pct', 11: 'efg_pct_d',
            12: 'to_pct', 13: 'to_pct_d', 14: 'conf_record', 15: 'sos',
            23: 'raw_o', 24: 'raw_d', 25: 'adj_o_no_opp', 26: 'adj_d_no_opp',
            29: 'off_ftrate', 30: 'def_ftrate', 44: 'adj_tempo',
        }
        
        rows = []
        for team_data in data:
            row = {}
            for idx, col_name in COLUMNS.items():
                if idx < len(team_data):
                    row[col_name] = team_data[idx]
            
            # Calculate derived stats
            if 'adj_o' in row and 'adj_tempo' in row:
                row['est_ppg'] = (row['adj_o'] / 100) * row['adj_tempo']
            if 'adj_d' in row and 'adj_tempo' in row:
                row['est_opp_ppg'] = (row['adj_d'] / 100) * row['adj_tempo']
            if 'est_ppg' in row and 'est_opp_ppg' in row:
                row['est_total'] = row['est_ppg'] + row['est_opp_ppg']
            
            # Parse record
            if 'record' in row and '-' in str(row['record']):
                parts = str(row['record']).split('-')
                row['wins'] = int(parts[0])
                row['losses'] = int(parts[1])
                row['games'] = row['wins'] + row['losses']
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save
        DATA_DIR.mkdir(exist_ok=True)
        df.to_csv(DATA_DIR / 'barttorvik_stats.csv', index=False)
        
        # Log refresh time
        with open(DATA_DIR / 'barttorvik_refresh.json', 'w') as f:
            json.dump({'last_refresh': datetime.now().isoformat()}, f)
        
        print(f"   ✅ Saved {len(df)} teams to barttorvik_stats.csv")
        return True
        
    except Exception as e:
        print(f"   ⚠️ Error fetching Barttorvik: {e}")
        return False


def main():
    print("=" * 70)
    print("🏀 CBB MINIMUM TOTALS SYSTEM - V3 (BARTTORVIK + GAME HISTORY)")
    print(f"   {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print("=" * 70)
    
    DATA_DIR.mkdir(exist_ok=True)
    
    # Step 1: Refresh Barttorvik data (daily)
    print("\n📊 STEP 1: Checking Barttorvik data...")
    print("-" * 50)
    
    if should_refresh_barttorvik():
        print("   Barttorvik data needs refresh...")
        refresh_barttorvik()
    else:
        print("   ✅ Barttorvik data is current (already refreshed today)")
    
    # Step 2: Update NCAA game history (incremental)
    print("\n📥 STEP 2: Updating game history...")
    print("-" * 50)
    
    try:
        from data_collection.ncaa_stats_fetcher import NCAAStatsFetcher
        fetcher = NCAAStatsFetcher()
        fetcher.fetch_incremental()
        print("   ✅ Game history updated")
    except Exception as e:
        print(f"   ⚠️ Could not update game history: {e}")
        print("   Continuing with existing data...")
    
    # Check required files exist
    games_csv = DATA_DIR / 'ncaa_games_history.csv'
    bt_csv = DATA_DIR / 'barttorvik_stats.csv'
    
    if not games_csv.exists():
        print(f"\n⚠️ No game history found at {games_csv}")
        print("   V3 will use Barttorvik data only (reduced accuracy)")
    
    if not bt_csv.exists():
        print(f"\n❌ No Barttorvik data found at {bt_csv}")
        print("   Run: python fetch_barttorvik.py")
        return
    
    # Step 3: Fetch today's odds
    print("\n📥 STEP 3: Fetching today's odds from DraftKings...")
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
        upcoming_file = DATA_DIR / 'upcoming_games.csv'
        if upcoming_file.exists():
            import pandas as pd
            games_df = pd.read_csv(upcoming_file)
            if 'has_alternate' in games_df.columns:
                games_df = games_df[games_df['has_alternate'] == True]
            print(f"   ℹ️ Loaded {len(games_df)} games from cached file")
        else:
            print("   ❌ No cached games found. Cannot continue.")
            return
    
    # Step 4: Run Monte Carlo V3 analysis
    print("\n🎲 STEP 4: Running Monte Carlo V3 simulation...")
    print("-" * 50)
    
    from monte_carlo_cbb_v3 import MonteCarloSimulatorV3
    
    simulator = MonteCarloSimulatorV3(str(DATA_DIR))
    games = games_df.to_dict('records')
    
    # Run with 10000 sims for accuracy
    results, summary = simulator.evaluate_all_games(games, n_simulations=10000)
    
    # Step 5: Print report
    print("\n📊 STEP 5: Analysis Results")
    simulator.print_report(results, summary)
    
    # Step 6: Save results
    print("\n💾 STEP 6: Saving results...")
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
        'defense_warning': r.get('defense_warning', False),
        'tempo_warning': r.get('tempo_warning', False),
    } for r, g in zip(results, games)])
    
    # Save all picks
    output_file = DATA_DIR / 'monte_carlo_picks.csv'
    results_df.to_csv(output_file, index=False)
    print(f"   ✅ Saved to {output_file}")
    
    # Save YES picks for quick reference
    yes_picks = results_df[results_df['decision'] == 'YES']
    if len(yes_picks) > 0:
        yes_file = DATA_DIR / 'yes_picks_today.csv'
        yes_picks.to_csv(yes_file, index=False)
        print(f"   ✅ YES picks saved to {yes_file}")
    
    # Save MAYBE picks too
    maybe_picks = results_df[results_df['decision'] == 'MAYBE']
    if len(maybe_picks) > 0:
        maybe_file = DATA_DIR / 'maybe_picks_today.csv'
        maybe_picks.to_csv(maybe_file, index=False)
        print(f"   ✅ MAYBE picks saved to {maybe_file}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE (V3 - Barttorvik + Game History)")
    print(f"   🟢 YES picks: {summary['yes_count']} (88%+ confidence)")
    print(f"   🟡 MAYBE picks: {summary['maybe_count']} (80-88% confidence)")
    print(f"   🔴 SKIP: {summary['no_count']}")
    print(f"   🛡️ Elite defense matchups: {summary['defense_warnings']}")
    print("=" * 70)
    
    # Quick picks display
    if len(yes_picks) > 0:
        print("\n🎯 TODAY'S YES PICKS:")
        for _, row in yes_picks.iterrows():
            flags = ""
            if row.get('defense_warning'): flags += " 🛡️"
            if row.get('tempo_warning'): flags += " 🐢"
            print(f"   {row['away_team']} @ {row['home_team']} OVER {row['minimum_total']}{flags}")
            print(f"      Hit Rate: {row['hit_rate']}% | Sim Mean: {row['sim_mean']}")


if __name__ == "__main__":
    main()
