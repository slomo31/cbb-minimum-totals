#!/usr/bin/env python3
"""
Backtest V3 against a specific date's games
Usage: python backtest_date.py 2025/11/26
"""

import sys
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

def fetch_games_for_date(date_str: str) -> list:
    """Fetch completed games from NCAA API for a specific date."""
    url = f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{date_str}"
    
    print(f"Fetching games for {date_str}...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for game_wrapper in data.get('games', []):
            game = game_wrapper.get('game', game_wrapper)
            
            if game.get('gameState') == 'final' or game.get('finalMessage') == 'FINAL':
                home = game.get('home', {})
                away = game.get('away', {})
                
                home_name = home.get('names', {}).get('short', '')
                away_name = away.get('names', {}).get('short', '')
                
                try:
                    home_score = int(home.get('score', 0))
                    away_score = int(away.get('score', 0))
                except:
                    continue
                
                if home_name and away_name:
                    games.append({
                        'home_team': home_name,
                        'away_team': away_name,
                        'home_score': home_score,
                        'away_score': away_score,
                        'total': home_score + away_score
                    })
        
        print(f"   Found {len(games)} completed games")
        return games
        
    except Exception as e:
        print(f"   Error: {e}")
        return []


def main():
    # Default to 11/26/2025
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = "2025/11/26"
    
    print("=" * 70)
    print(f"🔄 V3 BACKTEST - {date_str}")
    print("=" * 70)
    
    # Fetch games for the date
    actual_games = fetch_games_for_date(date_str)
    
    if not actual_games:
        print("No games found for this date")
        return
    
    # Import V3 simulator
    try:
        from monte_carlo_cbb_v3 import MonteCarloSimulatorV3
        sim = MonteCarloSimulatorV3()
    except Exception as e:
        print(f"Error loading V3: {e}")
        return
    
    # Standard minimums are typically 12 points below the main line
    # We'll test various minimum thresholds
    
    print(f"\nAnalyzing {len(actual_games)} games...")
    print("-" * 70)
    
    # For each game, simulate with a reasonable minimum (total - 12)
    results = []
    
    for game in actual_games:
        home = game['home_team']
        away = game['away_team']
        actual_total = game['total']
        
        # Estimate what the minimum line would have been
        # Typically minimums are ~12 below the standard line
        # We'll use the actual total - 10 as a proxy for what a "safe" minimum would be
        # This tests: would V3 have correctly identified this as safe or risky?
        
        test_minimums = [
            actual_total - 20,  # Very safe (should be YES)
            actual_total - 10,  # Moderately safe
            actual_total - 5,   # Close
            actual_total,       # Exact (should be NO/MAYBE)
            actual_total + 5,   # Would have lost
        ]
        
        # Run simulation
        eval_result = sim.simulate_game(home, away, n_simulations=5000)
        
        if eval_result['mean_total'] is None:
            continue
        
        sim_mean = eval_result['mean_total']
        
        results.append({
            'away': away,
            'home': home,
            'actual': actual_total,
            'v3_sim_mean': sim_mean,
            'error': actual_total - sim_mean,
            'data_quality': eval_result['data_quality'],
        })
    
    # Print results
    print(f"\n{'Game':<45} {'Actual':>7} {'V3 Mean':>8} {'Error':>7} {'Quality':<8}")
    print("-" * 80)
    
    errors = []
    for r in sorted(results, key=lambda x: abs(x['error']), reverse=True)[:30]:
        game = f"{r['away'][:20]} @ {r['home'][:20]}"
        error_str = f"{r['error']:+.1f}"
        print(f"{game:<45} {r['actual']:>7} {r['v3_sim_mean']:>8.1f} {error_str:>7} {r['data_quality']:<8}")
        errors.append(r['error'])
    
    # Summary statistics
    print("\n" + "=" * 70)
    print("📊 V3 PREDICTION ACCURACY")
    print("=" * 70)
    
    import numpy as np
    errors = [r['error'] for r in results]
    abs_errors = [abs(e) for e in errors]
    
    print(f"   Games analyzed: {len(results)}")
    print(f"   Mean Error: {np.mean(errors):+.1f} (positive = actual higher than predicted)")
    print(f"   Std Error: {np.std(errors):.1f}")
    print(f"   Mean Absolute Error: {np.mean(abs_errors):.1f}")
    print(f"   Median Absolute Error: {np.median(abs_errors):.1f}")
    
    # Accuracy at different thresholds
    print(f"\n   Accuracy within thresholds:")
    for threshold in [10, 15, 20, 25]:
        within = sum(1 for e in abs_errors if e <= threshold)
        pct = within / len(abs_errors) * 100
        print(f"     Within ±{threshold} points: {within}/{len(abs_errors)} ({pct:.1f}%)")
    
    # Simulate betting performance
    print("\n" + "=" * 70)
    print("💰 SIMULATED BETTING PERFORMANCE")
    print("=" * 70)
    
    # Test: If we bet OVER (actual - 12) on all games where V3 said YES (88%+)
    wins = 0
    losses = 0
    yes_count = 0
    
    for game in actual_games:
        home = game['home_team']
        away = game['away_team']
        actual_total = game['total']
        
        # Typical minimum is ~12 below expected
        # Approximate what the minimum line would have been
        # Use V3's prediction minus 12
        eval_result = sim.evaluate_game(
            home_team=home,
            away_team=away,
            minimum_total=actual_total - 12,  # Simulate betting 12 below actual
            n_simulations=5000
        )
        
        if eval_result['decision'] == 'YES':
            yes_count += 1
            # Would have won (actual >= minimum)
            wins += 1
    
    print(f"   If betting minimums 12 below actual totals:")
    print(f"   V3 YES picks: {yes_count}")
    print(f"   All would be wins (by definition of test)")
    
    # More realistic test: use a fixed minimum threshold
    print(f"\n   Testing with fixed minimum of 130:")
    wins_130 = 0
    losses_130 = 0
    yes_130 = 0
    
    for game in actual_games:
        home = game['home_team']
        away = game['away_team']
        actual_total = game['total']
        
        eval_result = sim.evaluate_game(
            home_team=home,
            away_team=away,
            minimum_total=130,
            n_simulations=5000
        )
        
        if eval_result['decision'] == 'YES':
            yes_130 += 1
            if actual_total >= 130:
                wins_130 += 1
            else:
                losses_130 += 1
                print(f"     ❌ LOSS: {away[:15]} @ {home[:15]}: {actual_total} < 130 (V3: {eval_result['hit_rate']:.0f}%)")
    
    if yes_130 > 0:
        print(f"   V3 YES picks (min 130): {yes_130}")
        print(f"   Wins: {wins_130}, Losses: {losses_130}")
        print(f"   Win Rate: {wins_130/yes_130*100:.1f}%")


if __name__ == "__main__":
    main()
