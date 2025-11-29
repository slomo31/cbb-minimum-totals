#!/usr/bin/env python3
"""
CBB ELITE OVERS RESULTS TRACKER
================================
Tracks results of Elite Minimum (Over) picks - Tiers 1-4.

Reads picks from data/elite_picks.csv and checks final scores.
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import requests

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"


def fetch_scores_for_date(date_str: str) -> dict:
    """Fetch final scores for a specific date."""
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
                    
                    key = f"{away}|{home}".lower()
                    scores[key] = {
                        'home_team': home,
                        'away_team': away,
                        'home_score': home_score,
                        'away_score': away_score,
                        'total': home_score + away_score
                    }
            return scores
    except Exception as e:
        print(f"Error fetching scores: {e}")
    
    return {}


def normalize_name(name: str) -> str:
    """Normalize team name for matching."""
    name = name.lower().strip()
    # Remove common suffixes
    suffixes = [
        ' bulldogs', ' cardinals', ' tigers', ' wildcats', ' bears',
        ' eagles', ' hawks', ' lions', ' panthers', ' wolves',
        ' billikens', ' hilltoppers', ' shockers', ' rams', ' bulls',
        ' trojans', ' salukis', ' beacons', ' broncos', ' anteaters',
        ' mountaineers', ' mavericks', ' privateers', ' screaming eagles',
        ' jackrabbits', ' antelopes', ' hawkeyes', ' spartans', ' tar heels',
        ' red raiders', ' hokies', ' pirates', ' cougars', ' wolverines',
        ' bearcats', ' ramblers', ' knights', ' golden panthers', ' sun devils'
    ]
    for suffix in suffixes:
        name = name.replace(suffix, '')
    return name.strip()


def find_score(scores: dict, away_team: str, home_team: str) -> dict:
    """Find score for a matchup with fuzzy matching."""
    away_norm = normalize_name(away_team)
    home_norm = normalize_name(home_team)
    
    for key, score in scores.items():
        parts = key.split('|')
        if len(parts) == 2:
            key_away = normalize_name(parts[0])
            key_home = normalize_name(parts[1])
            
            # Check both directions
            if (away_norm in key_away or key_away in away_norm) and \
               (home_norm in key_home or key_home in home_norm):
                return score
            
    return None


def track_elite_results():
    """Track results for Elite Minimum (Over) picks."""
    data_dir = Path(__file__).parent / "data"
    picks_file = data_dir / "elite_picks.csv"
    
    if not picks_file.exists():
        print(f"❌ No picks file found at {picks_file}")
        return
    
    # Load picks
    df = pd.read_csv(picks_file)
    
    # Filter to qualified picks only (tier 1-4)
    qualified = df[df['tier'] > 0].copy()
    
    if qualified.empty:
        print("❌ No qualified Elite picks found")
        return
    
    print("\n" + "=" * 70)
    print("📈 CBB ELITE OVERS RESULTS TRACKER")
    print("=" * 70)
    
    # Fetch scores
    print("\n📡 Fetching scores...")
    scores = fetch_scores_for_date(datetime.now().strftime("%Y-%m-%d"))
    print(f"   Found {len(scores)} completed games")
    
    # Track results
    results = []
    pending = []
    
    for _, row in qualified.iterrows():
        away_team = row.get('away_team', '')
        home_team = row.get('home_team', '')
        minimum_line = row.get('minimum_total', 0)
        tier = int(row.get('tier', 0))
        hit_rate = row.get('hit_rate', 0)
        
        score = find_score(scores, away_team, home_team)
        
        if score:
            actual_total = score['total']
            over_won = actual_total > minimum_line
            margin = actual_total - minimum_line
            
            results.append({
                'date': row.get('date', ''),
                'matchup': f"{away_team} @ {home_team}",
                'tier': tier,
                'minimum_line': minimum_line,
                'actual_total': actual_total,
                'over_won': over_won,
                'margin': margin,
                'hit_rate': hit_rate
            })
        else:
            pending.append({
                'matchup': f"{away_team} @ {home_team}",
                'tier': tier,
                'minimum_line': minimum_line,
                'hit_rate': hit_rate
            })
    
    # Print results by tier
    if results:
        print(f"\n{'='*70}")
        print("RESULTS BY TIER")
        print("="*70)
        
        results_df = pd.DataFrame(results)
        
        for tier in [1, 2, 3, 4]:
            tier_results = results_df[results_df['tier'] == tier]
            if not tier_results.empty:
                wins = tier_results['over_won'].sum()
                total = len(tier_results)
                tier_labels = {
                    1: '🔒 TIER 1 - LOCK (100% backtest)',
                    2: '✅ TIER 2 - VERY SAFE (92.9%)',
                    3: '✅ TIER 3 - SAFE (93.0%)',
                    4: '⚠️ TIER 4 - FLOOR (86.5%)'
                }
                print(f"\n{tier_labels[tier]}: {wins}-{total-wins} ({wins/total*100:.1f}%)")
                
                for _, r in tier_results.iterrows():
                    result_icon = "✅" if r['over_won'] else "❌"
                    print(f"   {result_icon} {r['matchup']}")
                    print(f"      OVER {r['minimum_line']} | Actual: {r['actual_total']} | Margin: {r['margin']:+.0f}")
        
        # Summary
        total_wins = results_df['over_won'].sum()
        total_games = len(results_df)
        
        print(f"\n{'='*70}")
        print(f"📈 OVERALL: {total_wins}-{total_games - total_wins} ({total_wins/total_games*100:.1f}%)")
        print("="*70)
        
        # Show losses in detail
        losses = results_df[~results_df['over_won']]
        if not losses.empty:
            print(f"\n❌ LOSSES:")
            for _, r in losses.iterrows():
                print(f"   {r['matchup']}")
                print(f"      OVER {r['minimum_line']} | Actual: {r['actual_total']} | Missed by: {abs(r['margin']):.1f}")
                print(f"      Tier: {r['tier']} | Confidence: {r['hit_rate']:.1f}%")
        
        # Save results
        history_file = data_dir / "elite_results_history.csv"
        if history_file.exists():
            existing = pd.read_csv(history_file)
            combined = pd.concat([existing, results_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['date', 'matchup'], keep='last')
            combined.to_csv(history_file, index=False)
        else:
            results_df.to_csv(history_file, index=False)
        
        print(f"\n💾 Results saved to {history_file}")
    
    else:
        print("\n⏳ No completed games found for Elite picks")
    
    # Show pending
    if pending:
        print(f"\n⏳ PENDING ({len(pending)}):")
        for p in pending[:5]:
            tier_emoji = {1: '🔒', 2: '✅', 3: '✅', 4: '⚠️'}.get(p['tier'], '?')
            print(f"   {tier_emoji} {p['matchup']} - OVER {p['minimum_line']} (T{p['tier']})")
        if len(pending) > 5:
            print(f"   ... and {len(pending) - 5} more")


if __name__ == "__main__":
    track_elite_results()
