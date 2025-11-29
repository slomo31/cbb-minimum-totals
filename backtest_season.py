#!/usr/bin/env python3
"""
Comprehensive Season Backtest for V3.1 Monte Carlo System
Tests against all games with historical odds data
"""

import sys
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"

def fetch_historical_odds(date_str: str) -> list:
    """Fetch historical odds from The Odds API."""
    iso_date = f"{date_str}T12:00:00Z"
    
    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'totals',
        'date': iso_date,
        'bookmakers': 'draftkings'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 422:
            return []  # No data for this date
        response.raise_for_status()
        data = response.json()
        
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        print(f"   API remaining: {remaining}")
        
        return data.get('data', [])
    except Exception as e:
        print(f"   Odds API error: {e}")
        return []


def fetch_actual_scores(date_str: str) -> dict:
    """Fetch actual scores from NCAA API."""
    ncaa_date = date_str.replace('-', '/')
    url = f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{ncaa_date}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        scores = {}
        for game_wrapper in data.get('games', []):
            game = game_wrapper.get('game', game_wrapper)
            
            if game.get('gameState') != 'final' and game.get('finalMessage') != 'FINAL':
                continue
            
            home = game.get('home', {})
            away = game.get('away', {})
            
            home_name = home.get('names', {}).get('short', '')
            away_name = away.get('names', {}).get('short', '')
            
            try:
                total = int(home.get('score', 0)) + int(away.get('score', 0))
                scores[(home_name, away_name)] = {
                    'total': total,
                    'home_score': int(home.get('score', 0)),
                    'away_score': int(away.get('score', 0))
                }
            except:
                continue
        
        return scores
    except Exception as e:
        return {}


def match_game(odds_home: str, odds_away: str, scores: dict) -> dict:
    """Try to match odds game to actual scores."""
    
    # Normalize for matching
    def normalize(name):
        return name.lower().replace('state', 'st').replace('university', '').strip()
    
    odds_home_norm = normalize(odds_home)
    odds_away_norm = normalize(odds_away)
    
    for (home, away), data in scores.items():
        home_norm = normalize(home)
        away_norm = normalize(away)
        
        # Check for keyword matches
        home_words = set(odds_home_norm.split())
        away_words = set(odds_away_norm.split())
        score_home_words = set(home_norm.split())
        score_away_words = set(away_norm.split())
        
        home_match = len(home_words & score_home_words) > 0 or \
                     any(w in home_norm for w in home_words if len(w) > 3) or \
                     any(w in odds_home_norm for w in score_home_words if len(w) > 3)
        away_match = len(away_words & score_away_words) > 0 or \
                     any(w in away_norm for w in away_words if len(w) > 3) or \
                     any(w in odds_away_norm for w in score_away_words if len(w) > 3)
        
        if home_match and away_match:
            return data
    
    return None


def backtest_date(sim, date_str: str) -> dict:
    """Backtest a single date."""
    
    print(f"\n📅 {date_str}")
    
    # Fetch odds
    odds_games = fetch_historical_odds(date_str)
    if not odds_games:
        print(f"   No odds data")
        return None
    
    # Fetch scores
    scores = fetch_actual_scores(date_str)
    if not scores:
        print(f"   No score data")
        return None
    
    print(f"   {len(odds_games)} games with odds, {len(scores)} with scores")
    
    results = []
    
    for game in odds_games:
        home_team = game.get('home_team', '')
        away_team = game.get('away_team', '')
        
        # Get total line
        dk_total = None
        for bookmaker in game.get('bookmakers', []):
            if bookmaker.get('key') == 'draftkings':
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'totals':
                        for outcome in market.get('outcomes', []):
                            if outcome.get('name') == 'Over':
                                dk_total = outcome.get('point')
                                break
        
        if dk_total is None:
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'totals':
                        for outcome in market.get('outcomes', []):
                            if outcome.get('name') == 'Over':
                                dk_total = outcome.get('point')
                                break
        
        if dk_total is None:
            continue
        
        minimum = dk_total - 12
        
        # Find actual score
        actual_data = match_game(home_team, away_team, scores)
        if actual_data is None:
            continue
        
        actual = actual_data['total']
        
        # Run V3.1 evaluation
        try:
            result = sim.evaluate_game(home_team, away_team, minimum, dk_total, n_simulations=5000)
        except Exception as e:
            continue
        
        results.append({
            'date': date_str,
            'away': away_team,
            'home': home_team,
            'main_line': dk_total,
            'minimum': minimum,
            'actual': actual,
            'hit': actual >= minimum,
            'decision': result['decision'],
            'hit_rate': result['hit_rate'],
            'sim_mean': result['sim_mean'],
            'flag_count': result.get('flag_count', 0),
            'percentile_10th': result.get('percentile_10th', 0),
        })
    
    return results


def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python backtest_season.py <season>")
        print("  season: '2024-25' or '2025-26'")
        sys.exit(1)
    
    season = sys.argv[1]
    
    if season == '2024-25':
        # Last season: Nov 4, 2024 - April 7, 2025
        start_date = datetime(2024, 11, 4)
        end_date = datetime(2025, 4, 7)
    elif season == '2025-26':
        # Current season: Nov 4, 2025 - today
        start_date = datetime(2025, 11, 4)
        end_date = datetime.now()
    else:
        print(f"Unknown season: {season}")
        sys.exit(1)
    
    print("=" * 70)
    print(f"🏀 V3.1 COMPREHENSIVE BACKTEST - {season} SEASON")
    print("=" * 70)
    
    # Load simulator
    try:
        from monte_carlo_cbb_v3 import MonteCarloSimulatorV3
        sim = MonteCarloSimulatorV3()
    except Exception as e:
        print(f"Error loading V3.1: {e}")
        sys.exit(1)
    
    all_results = []
    dates_tested = 0
    
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        
        results = backtest_date(sim, date_str)
        if results:
            all_results.extend(results)
            dates_tested += 1
        
        current += timedelta(days=1)
        
        # Rate limiting - be nice to API
        time.sleep(0.5)
        
        # Progress update every 10 days
        if dates_tested % 10 == 0 and dates_tested > 0:
            yes_so_far = [r for r in all_results if r['decision'] == 'YES']
            wins_so_far = sum(1 for r in yes_so_far if r['hit'])
            print(f"\n   📊 Progress: {dates_tested} days, {len(yes_so_far)} YES picks, {wins_so_far} wins")
    
    # Final results
    print("\n" + "=" * 70)
    print("📊 FINAL RESULTS")
    print("=" * 70)
    
    print(f"\nDates tested: {dates_tested}")
    print(f"Total games analyzed: {len(all_results)}")
    
    # YES picks
    yes_picks = [r for r in all_results if r['decision'] == 'YES']
    yes_wins = sum(1 for r in yes_picks if r['hit'])
    yes_losses = len(yes_picks) - yes_wins
    
    print(f"\n🟢 YES PICKS: {len(yes_picks)}")
    print(f"   Wins: {yes_wins}")
    print(f"   Losses: {yes_losses}")
    if yes_picks:
        print(f"   Win Rate: {yes_wins/len(yes_picks)*100:.1f}%")
    
    # MAYBE picks
    maybe_picks = [r for r in all_results if r['decision'] == 'MAYBE']
    maybe_wins = sum(1 for r in maybe_picks if r['hit'])
    maybe_losses = len(maybe_picks) - maybe_wins
    
    print(f"\n🟡 MAYBE PICKS: {len(maybe_picks)}")
    print(f"   Wins: {maybe_wins}")
    print(f"   Losses: {maybe_losses}")
    if maybe_picks:
        print(f"   Win Rate: {maybe_wins/len(maybe_picks)*100:.1f}%")
    
    # Show all YES losses
    yes_losses_list = [r for r in yes_picks if not r['hit']]
    if yes_losses_list:
        print(f"\n❌ YES PICK LOSSES ({len(yes_losses_list)}):")
        print("-" * 70)
        for r in sorted(yes_losses_list, key=lambda x: x['date']):
            miss = r['minimum'] - r['actual']
            print(f"   {r['date']}: {r['away'][:20]} @ {r['home'][:20]}")
            print(f"      Actual: {r['actual']} vs Min: {r['minimum']} (missed by {miss:.1f})")
            print(f"      Hit Rate: {r['hit_rate']:.1f}%, Flags: {r['flag_count']}, Sim Avg: {r['sim_mean']:.1f}")
    
    # Save detailed results
    output_file = f"backtest_results_{season.replace('-', '_')}.csv"
    try:
        import csv
        with open(output_file, 'w', newline='') as f:
            if all_results:
                writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
                writer.writeheader()
                writer.writerows(all_results)
        print(f"\n💾 Detailed results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save CSV: {e}")


if __name__ == "__main__":
    main()
