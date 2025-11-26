#!/usr/bin/env python3
"""
Master Workflow
Main entry point for daily CBB minimum totals prediction workflow
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.season_config import DATA_DIR, is_season_active
from data_collection.cbb_stats_collector import CBBStatsCollector
from data_collection.odds_minimum_fetcher import OddsMinimumFetcher
from core.minimum_total_predictor import MinimumTotalPredictor
from decision.yes_no_decider import YesNoDecider


def print_header():
    """Print workflow header"""
    print("=" * 70)
    print("   CBB MINIMUM TOTALS PREDICTION SYSTEM")
    print("   Daily Workflow")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def step_1_collect_stats():
    """Step 1: Collect/update team statistics"""
    print("\n" + "=" * 70)
    print("STEP 1: COLLECTING TEAM STATISTICS")
    print("=" * 70)
    
    try:
        collector = CBBStatsCollector()
        stats = collector.collect_all_stats()
        
        if stats is not None and not stats.empty:
            print(f"\n✅ Collected stats for {len(stats)} teams")
            return True
        else:
            # Try to load existing stats
            existing = collector.load_existing_stats()
            if existing is not None and not existing.empty:
                print(f"\n⚠️ Using existing stats ({len(existing)} teams)")
                return True
            else:
                print("\n❌ No stats available")
                return False
    except Exception as e:
        print(f"\n❌ Error collecting stats: {e}")
        return False


def step_2_fetch_odds():
    """Step 2: Fetch minimum alternate totals from DraftKings"""
    print("\n" + "=" * 70)
    print("STEP 2: FETCHING ODDS FROM DRAFTKINGS")
    print("=" * 70)
    
    try:
        fetcher = OddsMinimumFetcher()
        games = fetcher.fetch_all_games_with_minimums()
        
        if games is not None and not games.empty:
            print(f"\n✅ Found {len(games)} games with minimum totals")
            return games
        else:
            print("\n❌ No upcoming games found")
            return None
    except Exception as e:
        print(f"\n❌ Error fetching odds: {e}")
        return None


def step_3_generate_predictions(games_df):
    """Step 3: Generate predictions for all games"""
    print("\n" + "=" * 70)
    print("STEP 3: GENERATING PREDICTIONS")
    print("=" * 70)
    
    try:
        predictor = MinimumTotalPredictor()
        predictions = predictor.analyze_upcoming_games(games_df)
        
        if predictions is not None and not predictions.empty:
            print(f"\n✅ Generated predictions for {len(predictions)} games")
            
            # Save predictions
            output_file = PROJECT_ROOT / DATA_DIR / 'predictions.csv'
            predictions.to_csv(output_file, index=False)
            print(f"   Saved to {output_file}")
            
            return predictions
        else:
            print("\n❌ No predictions generated")
            return None
    except Exception as e:
        print(f"\n❌ Error generating predictions: {e}")
        import traceback
        traceback.print_exc()
        return None


def step_4_make_decisions(predictions_df):
    """Step 4: Make YES/NO betting decisions"""
    print("\n" + "=" * 70)
    print("STEP 4: MAKING BETTING DECISIONS")
    print("=" * 70)
    
    try:
        decider = YesNoDecider()
        results = decider.evaluate_predictions(predictions_df)
        
        # Print report
        print(decider.format_report())
        
        # Save decisions
        decider.save_decisions()
        
        return results
    except Exception as e:
        print(f"\n❌ Error making decisions: {e}")
        return None


def run_workflow(skip_stats=False, skip_odds=False):
    """Run the complete daily workflow"""
    print_header()
    
    # Check if season is active
    if not is_season_active():
        print("\n⚠️ WARNING: CBB season may not be active")
        print("   Predictions may be limited")
    
    # Step 1: Collect stats
    if not skip_stats:
        stats_ok = step_1_collect_stats()
        if not stats_ok:
            print("\n⚠️ Continuing without fresh stats...")
    
    # Step 2: Fetch odds
    if not skip_odds:
        games_df = step_2_fetch_odds()
        if games_df is None or games_df.empty:
            print("\n❌ Cannot continue without games data")
            return None
    else:
        # Load existing odds
        odds_file = PROJECT_ROOT / DATA_DIR / 'upcoming_games.csv'
        if odds_file.exists():
            import pandas as pd
            games_df = pd.read_csv(odds_file)
            print(f"\nUsing cached odds: {len(games_df)} games")
        else:
            print("\n❌ No cached odds available")
            return None
    
    # Step 3: Generate predictions
    predictions = step_3_generate_predictions(games_df)
    if predictions is None or predictions.empty:
        print("\n❌ No predictions to evaluate")
        return None
    
    # Step 4: Make decisions
    decisions = step_4_make_decisions(predictions)
    
    # Final summary
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    
    if decisions:
        yes_count = len(decisions['yes'])
        maybe_count = len(decisions['maybe'])
        print(f"\n📊 Final Results:")
        print(f"   YES Picks: {yes_count}")
        print(f"   MAYBE Picks: {maybe_count}")
        print(f"   Total Actionable: {yes_count + maybe_count}")
    
    print(f"\n🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return decisions


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CBB Minimum Totals Prediction Workflow')
    parser.add_argument('--skip-stats', action='store_true', help='Skip stats collection')
    parser.add_argument('--skip-odds', action='store_true', help='Use cached odds')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    
    args = parser.parse_args()
    
    if args.test:
        print("Running in TEST mode...")
        run_workflow(skip_stats=True, skip_odds=True)
    else:
        run_workflow(skip_stats=args.skip_stats, skip_odds=args.skip_odds)


if __name__ == "__main__":
    main()
