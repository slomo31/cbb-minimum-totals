#!/usr/bin/env python3
"""
Backtest V3 Monte Carlo against yesterday's picks
Compares V1, V2, and V3 performance
"""

import pandas as pd
from pathlib import Path

def main():
    data_dir = Path(__file__).parent / 'data'
    
    # Load tracking results
    tracking_file = data_dir / 'mc_tracking_results.csv'
    if not tracking_file.exists():
        print("No tracking file found")
        return
    
    df = pd.read_csv(tracking_file)
    completed = df[df['status'] == 'COMPLETE'].copy()
    
    if completed.empty:
        print("No completed games to backtest")
        return
    
    print("=" * 80)
    print("🔄 V3 BACKTEST - Comparing V1, V2, V3")
    print("=" * 80)
    
    # Import both simulators
    try:
        from monte_carlo_cbb import MonteCarloSimulatorV2
        v2_available = True
        v2_sim = MonteCarloSimulatorV2()
    except:
        v2_available = False
        print("⚠️ V2 not available")
    
    try:
        from monte_carlo_cbb_v3 import MonteCarloSimulatorV3
        v3_available = True
        v3_sim = MonteCarloSimulatorV3()
    except Exception as e:
        v3_available = False
        print(f"⚠️ V3 not available: {e}")
        return
    
    print(f"\nBacktesting {len(completed)} completed games...")
    print("-" * 80)
    
    results = []
    
    for _, row in completed.iterrows():
        home = row['home_team']
        away = row['away_team']
        minimum = row['minimum_total']
        standard = row.get('standard_total', None)
        actual = row['actual_total']
        v1_decision = row['decision']
        v1_hit_rate = row['hit_rate']
        
        actual_hit = actual >= minimum
        
        # Run V2
        if v2_available:
            v2_eval = v2_sim.evaluate_game(home, away, minimum, standard, n_simulations=10000)
            v2_decision = v2_eval['decision']
            v2_hit_rate = v2_eval['hit_rate']
            v2_mean = v2_eval['sim_mean']
        else:
            v2_decision = 'N/A'
            v2_hit_rate = 0
            v2_mean = 0
        
        # Run V3
        v3_eval = v3_sim.evaluate_game(home, away, minimum, standard, n_simulations=10000)
        v3_decision = v3_eval['decision']
        v3_hit_rate = v3_eval['hit_rate']
        v3_mean = v3_eval['sim_mean']
        v3_expected = v3_eval.get('matchup_details', {}).get('total_expected', 0)
        
        results.append({
            'away_team': away,
            'home_team': home,
            'minimum': minimum,
            'actual': actual,
            'actual_hit': actual_hit,
            'v1_decision': v1_decision,
            'v1_hit_rate': v1_hit_rate,
            'v2_decision': v2_decision,
            'v2_hit_rate': v2_hit_rate,
            'v2_mean': v2_mean,
            'v3_decision': v3_decision,
            'v3_hit_rate': v3_hit_rate,
            'v3_mean': v3_mean,
            'v3_expected': v3_expected,
        })
    
    # Print comparison table
    print(f"\n{'Game':<40} {'Min':>6} {'Act':>6} {'V1':>10} {'V2':>10} {'V3':>10} {'V3 Exp':>7}")
    print("-" * 95)
    
    for r in results:
        game = f"{r['away_team'][:18]} @ {r['home_team'][:18]}"
        hit_str = "✅" if r['actual_hit'] else "❌"
        
        v1_str = f"{r['v1_decision'][:1]}({r['v1_hit_rate']:.0f}%)"
        v2_str = f"{r['v2_decision'][:1]}({r['v2_hit_rate']:.0f}%)" if v2_available else "N/A"
        v3_str = f"{r['v3_decision'][:1]}({r['v3_hit_rate']:.0f}%)"
        
        print(f"{game:<40} {r['minimum']:>6.1f} {r['actual']:>5.0f}{hit_str} {v1_str:>10} {v2_str:>10} {v3_str:>10} {r['v3_expected']:>7.1f}")
    
    # Calculate stats for each version
    print("\n" + "=" * 80)
    print("📊 COMPARISON SUMMARY")
    print("=" * 80)
    
    # V1 stats
    v1_yes = [r for r in results if r['v1_decision'] == 'YES']
    v1_correct = sum(1 for r in v1_yes if r['actual_hit'])
    v1_wrong = len(v1_yes) - v1_correct
    
    print(f"\n🔵 V1 (Original):")
    print(f"   YES picks: {len(v1_yes)}")
    print(f"   Correct: {v1_correct}, Wrong: {v1_wrong}")
    if v1_yes:
        print(f"   Win Rate: {v1_correct/len(v1_yes)*100:.1f}%")
    
    # V2 stats
    if v2_available:
        v2_yes = [r for r in results if r['v2_decision'] == 'YES']
        v2_correct = sum(1 for r in v2_yes if r['actual_hit'])
        v2_wrong = len(v2_yes) - v2_correct
        
        print(f"\n🟡 V2 (Defense Adjusted):")
        print(f"   YES picks: {len(v2_yes)}")
        print(f"   Correct: {v2_correct}, Wrong: {v2_wrong}")
        if v2_yes:
            print(f"   Win Rate: {v2_correct/len(v2_yes)*100:.1f}%")
    
    # V3 stats
    v3_yes = [r for r in results if r['v3_decision'] == 'YES']
    v3_correct = sum(1 for r in v3_yes if r['actual_hit'])
    v3_wrong = len(v3_yes) - v3_correct
    
    print(f"\n🟢 V3 (Barttorvik + Game History):")
    print(f"   YES picks: {len(v3_yes)}")
    print(f"   Correct: {v3_correct}, Wrong: {v3_wrong}")
    if v3_yes:
        print(f"   Win Rate: {v3_correct/len(v3_yes)*100:.1f}%")
    
    # V3 expected vs actual analysis
    print(f"\n📈 V3 Expected vs Actual:")
    errors = []
    for r in results:
        if r['v3_expected'] > 0:
            error = r['actual'] - r['v3_expected']
            errors.append(error)
            if abs(error) > 20:
                over_under = "over" if error > 0 else "under"
                print(f"   ⚠️ {r['away_team'][:15]} @ {r['home_team'][:15]}: {error:+.1f} ({over_under})")
    
    if errors:
        print(f"\n   Mean Error: {np.mean(errors):+.1f}")
        print(f"   Std Error: {np.std(errors):.1f}")
        print(f"   Mean Absolute Error: {np.mean(np.abs(errors)):.1f}")
    
    # Show what V3 avoided/missed vs V1
    print(f"\n✅ V3 Improvements over V1:")
    avoided = [r for r in results if r['v1_decision'] == 'YES' and r['v3_decision'] != 'YES' and not r['actual_hit']]
    for r in avoided:
        print(f"   Avoided loss: {r['away_team'][:20]} @ {r['home_team'][:20]} ({r['actual']:.0f} < {r['minimum']:.0f})")
    
    missed = [r for r in results if r['v1_decision'] == 'YES' and r['v3_decision'] != 'YES' and r['actual_hit']]
    if missed:
        print(f"\n⚠️ V3 Skipped V1 Wins:")
        for r in missed:
            print(f"   {r['away_team'][:20]} @ {r['home_team'][:20]} ({r['actual']:.0f} >= {r['minimum']:.0f}) - V3: {r['v3_decision']} {r['v3_hit_rate']:.0f}%")


if __name__ == "__main__":
    import numpy as np
    main()
