#!/usr/bin/env python3
"""
CBB MAXIMUM (UNDER) RESULTS TRACKER
====================================
Tracks results of Monte Carlo maximum (under) picks.

Reads picks from data/max_picks.csv and checks final scores.
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import requests

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"


def fetch_scores(date_str: str) -> dict:
    """Fetch final scores for a date from The Odds API."""
    url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/scores"
    params = {
        'apiKey': ODDS_API_KEY,
        'daysFrom': 3,
        'dateFormat': 'iso'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            games = response.json()
            scores = {}
            for game in games:
                if game.get('completed'):
                    home = game.get('home_team', '')
                    away = game.get('away_team', '')
                    home_score = 0
                    away_score = 0
                    for score in game.get('scores', []):
                        if score['name'] == home:
                            home_score = int(score['score'])
                        elif score['name'] == away:
                            away_score = int(score['score'])
                    
                    key = f"{away} @ {home}".lower()
                    scores[key] = {
                        'home_score': home_score,
                        'away_score': away_score,
                        'total': home_score + away_score
                    }
            return scores
    except Exception as e:
        print(f"Error fetching scores: {e}")
    
    return {}


def normalize_team_name(name: str) -> str:
    """Normalize team name for matching."""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [' hilltoppers', ' cardinals', ' billikens', ' shockers', 
                   ' wildcats', ' bulldogs', ' bears', ' tigers', ' eagles',
                   ' hawks', ' owls', ' panthers', ' lions', ' wolves']:
        name = name.replace(suffix, '')
    return name.strip()


def find_score(scores: dict, away_team: str, home_team: str) -> dict:
    """Find score for a matchup with fuzzy matching."""
    away_norm = normalize_team_name(away_team)
    home_norm = normalize_team_name(home_team)
    
    for key, score in scores.items():
        key_lower = key.lower()
        if away_norm in key_lower and home_norm in key_lower:
            return score
        # Try partial match
        parts = key.split(' @ ')
        if len(parts) == 2:
            if (away_norm in parts[0] or parts[0] in away_norm) and \
               (home_norm in parts[1] or parts[1] in home_norm):
                return score
    
    return None


def track_max_results(picks_file: str = None, days_back: int = 7):
    """Track results for maximum (under) picks."""
    if picks_file is None:
        picks_file = Path(__file__).parent / "data" / "max_picks.csv"
    
    picks_path = Path(picks_file)
    if not picks_path.exists():
        print(f"❌ No picks file found at {picks_path}")
        return
    
    # Load picks
    df = pd.read_csv(picks_path)
    
    if 'date' not in df.columns:
        print("❌ No date column in picks file")
        return
    
    # Filter to qualified picks only
    qualified = df[df['tier'].notna() & (df['tier'] > 0)].copy()
    
    if qualified.empty:
        print("❌ No qualified picks found")
        return
    
    print("\n" + "=" * 70)
    print("📊 CBB MAXIMUM (UNDER) RESULTS TRACKER")
    print("=" * 70)
    
    # Fetch scores
    print("\n📡 Fetching scores...")
    scores = fetch_scores(datetime.now().strftime("%Y-%m-%d"))
    print(f"   Found {len(scores)} completed games")
    
    # Track results
    results = []
    
    for _, row in qualified.iterrows():
        away_team = row.get('away_team', '')
        home_team = row.get('home_team', '')
        maximum_line = row.get('maximum_total', 0)
        tier = int(row.get('tier', 0))
        
        score = find_score(scores, away_team, home_team)
        
        if score:
            actual_total = score['total']
            under_won = actual_total < maximum_line
            margin = maximum_line - actual_total
            
            results.append({
                'date': row.get('date', ''),
                'matchup': f"{away_team} @ {home_team}",
                'tier': tier,
                'maximum_line': maximum_line,
                'actual_total': actual_total,
                'under_won': under_won,
                'margin': margin
            })
    
    if not results:
        print("\n⏳ No results yet - games may not have completed")
        print("\nPending picks:")
        for _, row in qualified.iterrows():
            tier = int(row.get('tier', 0))
            tier_labels = {1: '🔒', 2: '✅', 3: '⚠️'}
            print(f"   {tier_labels.get(tier, '?')} {row.get('away_team', '')} @ {row.get('home_team', '')} - UNDER {row.get('maximum_total', 0)}")
        return
    
    # Print results
    print(f"\n{'='*70}")
    print("RESULTS BY TIER")
    print("="*70)
    
    results_df = pd.DataFrame(results)
    
    for tier in [1, 2, 3]:
        tier_results = results_df[results_df['tier'] == tier]
        if not tier_results.empty:
            wins = tier_results['under_won'].sum()
            total = len(tier_results)
            tier_labels = {
                1: '🔒 TIER 1 - BEST',
                2: '✅ TIER 2 - SAFE',
                3: '⚠️ TIER 3 - VOLUME'
            }
            print(f"\n{tier_labels[tier]}: {wins}-{total-wins} ({wins/total*100:.1f}%)")
            
            for _, r in tier_results.iterrows():
                result_icon = "✅" if r['under_won'] else "❌"
                print(f"   {result_icon} {r['matchup']}")
                print(f"      UNDER {r['maximum_line']} | Actual: {r['actual_total']} | Margin: {r['margin']:+.0f}")
    
    # Summary
    total_wins = results_df['under_won'].sum()
    total_games = len(results_df)
    
    print(f"\n{'='*70}")
    print(f"📈 OVERALL: {total_wins}-{total_games - total_wins} ({total_wins/total_games*100:.1f}%)")
    print("="*70)
    
    # Save results
    results_path = Path(__file__).parent / "data" / "max_results_history.csv"
    if results_path.exists():
        existing = pd.read_csv(results_path)
        combined = pd.concat([existing, results_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=['date', 'matchup'], keep='last')
        combined.to_csv(results_path, index=False)
    else:
        results_df.to_csv(results_path, index=False)
    
    print(f"\n💾 Results saved to {results_path}")


if __name__ == "__main__":
    track_max_results()
