#!/usr/bin/env python3
"""
Backtest V2 Monte Carlo against yesterday's picks
Shows what V2 would have predicted vs what V1 predicted vs actual results
"""

import pandas as pd
from pathlib import Path

# Import V2 simulator
from monte_carlo_cbb import MonteCarloSimulatorV2

def main():
    data_dir = Path(__file__).parent / 'data'
    
    # Load yesterday's tracking results
    tracking_file = data_dir / 'mc_tracking_results.csv'
    if not tracking_file.exists():
        print("No tracking file found")
        return
    
    df = pd.read_csv(tracking_file)
    
    # Only look at completed games
    completed = df[df['status'] == 'COMPLETE'].copy()
    
    if completed.empty:
        print("No completed games to backtest")
        return
    
    print("=" * 70)
    print("🔄 V2 BACKTEST - Yesterday's Games")
    print("=" * 70)
    
    # Initialize V2 simulator
    games_csv = data_dir / 'ncaa_games_history.csv'
    sim = MonteCarloSimulatorV2(str(games_csv))
    
    print(f"\nBacktesting {len(completed)} completed games...")
    print("-" * 70)
    
    results = []
    
    for _, row in completed.iterrows():
        home = row['home_team']
        away = row['away_team']
        minimum = row['minimum_total']
        standard = row.get('standard_total', None)
        actual = row['actual_total']
        v1_decision = row['decision']
        v1_hit_rate = row['hit_rate']
        v1_result = row['result']
        
        # Run V2 evaluation
        v2_eval = sim.evaluate_game(
            home_team=home,
            away_team=away,
            minimum_total=minimum,
            standard_total=standard,
            n_simulations=10000
        )
        
        actual_hit = actual >= minimum
        
        results.append({
            'away_team': away,
            'home_team': home,
            'minimum': minimum,
            'actual': actual,
            'actual_hit': actual_hit,
            'v1_decision': v1_decision,
            'v1_hit_rate': v1_hit_rate,
            'v1_result': v1_result,
            'v2_decision': v2_eval['decision'],
            'v2_hit_rate': v2_eval['hit_rate'],
            'v2_sim_mean': v2_eval['sim_mean'],
            'defense_warning': v2_eval['defense_warning'],
        })
    
    # Print comparison
    print(f"\n{'Game':<45} {'Min':>6} {'Actual':>7} {'V1':>12} {'V2':>12} {'Def':>4}")
    print("-" * 90)
    
    v1_yes_correct = 0
    v1_yes_wrong = 0
    v2_yes_correct = 0
    v2_yes_wrong = 0
    
    for r in results:
        game = f"{r['away_team'][:20]} @ {r['home_team'][:20]}"
        hit_str = "✅" if r['actual_hit'] else "❌"
        def_str = "🛡️" if r['defense_warning'] else ""
        
        v1_str = f"{r['v1_decision']} ({r['v1_hit_rate']:.0f}%)"
        v2_str = f"{r['v2_decision']} ({r['v2_hit_rate']:.0f}%)"
        
        print(f"{game:<45} {r['minimum']:>6} {r['actual']:>6}{hit_str} {v1_str:>12} {v2_str:>12} {def_str:>4}")
        
        # Count V1 YES performance
        if r['v1_decision'] == 'YES':
            if r['actual_hit']:
                v1_yes_correct += 1
            else:
                v1_yes_wrong += 1
        
        # Count V2 YES performance
        if r['v2_decision'] == 'YES':
            if r['actual_hit']:
                v2_yes_correct += 1
            else:
                v2_yes_wrong += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 COMPARISON SUMMARY")
    print("=" * 70)
    
    print(f"\n🔵 V1 YES picks: {v1_yes_correct + v1_yes_wrong}")
    print(f"   Correct: {v1_yes_correct}")
    print(f"   Wrong: {v1_yes_wrong}")
    if v1_yes_correct + v1_yes_wrong > 0:
        print(f"   Win Rate: {v1_yes_correct / (v1_yes_correct + v1_yes_wrong) * 100:.1f}%")
    
    print(f"\n🟢 V2 YES picks: {v2_yes_correct + v2_yes_wrong}")
    print(f"   Correct: {v2_yes_correct}")
    print(f"   Wrong: {v2_yes_wrong}")
    if v2_yes_correct + v2_yes_wrong > 0:
        print(f"   Win Rate: {v2_yes_correct / (v2_yes_correct + v2_yes_wrong) * 100:.1f}%")
    
    # Show what V2 would have avoided
    avoided_losses = [r for r in results if r['v1_decision'] == 'YES' and r['v2_decision'] != 'YES' and not r['actual_hit']]
    if avoided_losses:
        print(f"\n✅ V2 would have AVOIDED these V1 losses:")
        for r in avoided_losses:
            print(f"   {r['away_team']} @ {r['home_team']}: {r['actual']} < {r['minimum']}")
    
    # Show wins V2 would have missed
    missed_wins = [r for r in results if r['v1_decision'] == 'YES' and r['v2_decision'] != 'YES' and r['actual_hit']]
    if missed_wins:
        print(f"\n⚠️ V2 would have SKIPPED these V1 wins:")
        for r in missed_wins:
            print(f"   {r['away_team']} @ {r['home_team']}: {r['actual']} >= {r['minimum']} (V2: {r['v2_decision']} {r['v2_hit_rate']:.0f}%)")


if __name__ == "__main__":
    main()
