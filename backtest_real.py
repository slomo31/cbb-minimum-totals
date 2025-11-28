#!/usr/bin/env python3
"""
Backtest V3 against historical odds from The Odds API
Uses real main lines and calculates minimums as (main - 12)
"""

import sys
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"

def fetch_historical_odds(date_str: str) -> dict:
    """
    Fetch historical odds from The Odds API.
    date_str format: 2025-11-26
    """
    # Convert to ISO format for API
    iso_date = f"{date_str}T12:00:00Z"
    
    url = f"https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'totals',
        'date': iso_date,
        'bookmakers': 'draftkings'  # Focus on DraftKings
    }
    
    print(f"Fetching historical odds for {date_str}...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check remaining requests
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        print(f"   API requests remaining: {remaining}")
        
        games = data.get('data', [])
        print(f"   Found {len(games)} games with odds")
        
        return games
        
    except Exception as e:
        print(f"   Error: {e}")
        return []


def fetch_actual_scores(date_str: str) -> dict:
    """
    Fetch actual scores from NCAA API.
    date_str format: 2025-11-26
    Returns dict of {(home_team, away_team): total_score}
    """
    # Convert date format for NCAA API
    ncaa_date = date_str.replace('-', '/')
    url = f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{ncaa_date}"
    
    print(f"Fetching actual scores...")
    
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
                scores[(home_name, away_name)] = total
            except:
                continue
        
        print(f"   Found {len(scores)} completed games with scores")
        return scores
        
    except Exception as e:
        print(f"   Error: {e}")
        return {}


def normalize_team_name(name: str) -> str:
    """Normalize team name for matching."""
    # Common replacements
    replacements = {
        'Falcons': '', 'Keydets': '', 'Bulldogs': '', 'Tigers': '',
        'Bears': '', 'Eagles': '', 'Hawks': '', 'Wildcats': '',
        'Panthers': '', 'Lions': '', 'Wolves': '', 'Cardinals': '',
        'State': 'St.', 'Saint': 'St.',
    }
    
    result = name.strip()
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result.strip()


def match_game(odds_home: str, odds_away: str, scores: dict) -> int:
    """Try to match odds game to actual scores."""
    
    # Direct match
    if (odds_home, odds_away) in scores:
        return scores[(odds_home, odds_away)]
    
    # Try normalized matching
    odds_home_norm = normalize_team_name(odds_home).lower()
    odds_away_norm = normalize_team_name(odds_away).lower()
    
    for (home, away), total in scores.items():
        home_norm = normalize_team_name(home).lower()
        away_norm = normalize_team_name(away).lower()
        
        # Check if key words match
        home_match = any(w in home_norm for w in odds_home_norm.split() if len(w) > 3) or \
                     any(w in odds_home_norm for w in home_norm.split() if len(w) > 3)
        away_match = any(w in away_norm for w in odds_away_norm.split() if len(w) > 3) or \
                     any(w in odds_away_norm for w in away_norm.split() if len(w) > 3)
        
        if home_match and away_match:
            return total
    
    return None


def main():
    # Get date from command line or default
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = "2025-11-26"
    
    print("=" * 70)
    print(f"🎯 V3.1 REAL BACKTEST - {date_str}")
    print("   Using historical odds from The Odds API")
    print("=" * 70)
    
    # Fetch historical odds
    odds_games = fetch_historical_odds(date_str)
    if not odds_games:
        print("No odds data found")
        return
    
    # Fetch actual scores
    scores = fetch_actual_scores(date_str)
    if not scores:
        print("No score data found")
        return
    
    # Import V3 simulator
    try:
        from monte_carlo_cbb_v3 import MonteCarloSimulatorV3
        sim = MonteCarloSimulatorV3()
    except Exception as e:
        print(f"Error loading V3: {e}")
        return
    
    print(f"\nAnalyzing games...")
    print("-" * 70)
    
    results = []
    
    for game in odds_games:
        home_team = game.get('home_team', '')
        away_team = game.get('away_team', '')
        
        # Get DraftKings total line
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
            # Try any bookmaker
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'totals':
                        for outcome in market.get('outcomes', []):
                            if outcome.get('name') == 'Over':
                                dk_total = outcome.get('point')
                                break
        
        if dk_total is None:
            continue
        
        # Calculate minimum (main line - 12)
        minimum = dk_total - 12
        
        # Find actual score
        actual = match_game(home_team, away_team, scores)
        if actual is None:
            continue
        
        # Run V3.1 evaluation
        result = sim.evaluate_game(home_team, away_team, minimum, dk_total, n_simulations=5000)
        
        results.append({
            'away': away_team,
            'home': home_team,
            'main_line': dk_total,
            'minimum': minimum,
            'actual': actual,
            'hit': actual >= minimum,
            'decision': result['decision'],
            'hit_rate': result['hit_rate'],
            'sim_mean': result['sim_mean'],
        })
    
    # Print results
    print(f"\n{'Game':<40} {'Main':>6} {'Min':>6} {'Actual':>7} {'V3.1':>12} {'Result':>8}")
    print("-" * 85)
    
    for r in sorted(results, key=lambda x: x['hit_rate'], reverse=True):
        game = f"{r['away'][:18]} @ {r['home'][:18]}"
        hit_str = "✅" if r['hit'] else "❌"
        decision_str = f"{r['decision'][:1]}({r['hit_rate']:.0f}%)"
        
        # Highlight losses in YES picks
        if r['decision'] == 'YES' and not r['hit']:
            result_str = "❌ LOSS"
        elif r['decision'] == 'YES' and r['hit']:
            result_str = "✅ WIN"
        else:
            result_str = "-"
        
        print(f"{game:<40} {r['main_line']:>6.1f} {r['minimum']:>6.1f} {r['actual']:>6}{hit_str} {decision_str:>12} {result_str:>8}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 V3.1 BETTING PERFORMANCE")
    print("=" * 70)
    
    yes_picks = [r for r in results if r['decision'] == 'YES']
    yes_wins = sum(1 for r in yes_picks if r['hit'])
    yes_losses = len(yes_picks) - yes_wins
    
    maybe_picks = [r for r in results if r['decision'] == 'MAYBE']
    maybe_wins = sum(1 for r in maybe_picks if r['hit'])
    maybe_losses = len(maybe_picks) - maybe_wins
    
    print(f"\n🟢 YES Picks: {len(yes_picks)}")
    print(f"   Wins: {yes_wins}")
    print(f"   Losses: {yes_losses}")
    if yes_picks:
        print(f"   Win Rate: {yes_wins/len(yes_picks)*100:.1f}%")
    
    print(f"\n🟡 MAYBE Picks: {len(maybe_picks)}")
    print(f"   Wins: {maybe_wins}")
    print(f"   Losses: {maybe_losses}")
    if maybe_picks:
        print(f"   Win Rate: {maybe_wins/len(maybe_picks)*100:.1f}%")
    
    # Show any YES losses
    yes_losses_list = [r for r in yes_picks if not r['hit']]
    if yes_losses_list:
        print(f"\n❌ YES PICK LOSSES:")
        for r in yes_losses_list:
            print(f"   {r['away']} @ {r['home']}: {r['actual']} < {r['minimum']} (line was {r['main_line']})")


if __name__ == "__main__":
    main()
