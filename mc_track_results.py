#!/usr/bin/env python3
"""
Monte Carlo Results Tracker
Tracks WIN/LOSS for Monte Carlo picks separately from legacy system
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
MC_PICKS_FILE = DATA_DIR / 'monte_carlo_picks.csv'
MC_TRACKING_FILE = DATA_DIR / 'mc_tracking_results.csv'

NCAA_API = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"


def load_mc_picks():
    """Load today's Monte Carlo picks"""
    if MC_PICKS_FILE.exists():
        return pd.read_csv(MC_PICKS_FILE)
    return pd.DataFrame()


def load_mc_tracking():
    """Load existing tracking data"""
    if MC_TRACKING_FILE.exists():
        return pd.read_csv(MC_TRACKING_FILE)
    return pd.DataFrame()


def save_mc_tracking(df):
    """Save tracking data"""
    df.to_csv(MC_TRACKING_FILE, index=False)


def fetch_final_scores(date_str=None):
    """Fetch final scores from NCAA API"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y/%m/%d')
    
    url = f"{NCAA_API}/{date_str}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            games = data.get('games', [])
            
            results = {}
            for game in games:
                if game.get('gameState') == 'final':
                    home = game.get('home', {})
                    away = game.get('away', {})
                    
                    home_name = home.get('names', {}).get('full', '')
                    away_name = away.get('names', {}).get('full', '')
                    home_score = int(home.get('score', 0))
                    away_score = int(away.get('score', 0))
                    total = home_score + away_score
                    
                    # Store by both team names for matching
                    key = f"{away_name} @ {home_name}"
                    results[key] = {
                        'home_team': home_name,
                        'away_team': away_name,
                        'home_score': home_score,
                        'away_score': away_score,
                        'total': total
                    }
            
            return results
    except Exception as e:
        print(f"Error fetching scores: {e}")
    
    return {}


def fuzzy_match(name1, name2):
    """Simple fuzzy matching for team names"""
    n1 = name1.lower().replace('/', ' ').split()
    n2 = name2.lower().replace('/', ' ').split()
    
    # Check if any significant word matches
    common = set(n1) & set(n2)
    # Remove common words
    common -= {'the', 'of', 'at', 'state', 'university'}
    
    return len(common) >= 1


def update_tracking():
    """Update Monte Carlo tracking with final scores"""
    picks = load_mc_picks()
    tracking = load_mc_tracking()
    
    if picks.empty:
        print("No Monte Carlo picks found")
        return
    
    # Get final scores
    scores = fetch_final_scores()
    print(f"Fetched {len(scores)} final scores")
    
    # Initialize tracking if empty
    if tracking.empty:
        tracking = picks.copy()
        tracking['status'] = 'PENDING'
        tracking['result'] = ''
        tracking['actual_total'] = 0
        tracking['date_added'] = datetime.now().strftime('%Y-%m-%d')
    
    # Update each pending pick
    updated = 0
    for idx, row in tracking.iterrows():
        if row['status'] == 'PENDING':
            home = row['home_team']
            away = row['away_team']
            min_total = row['minimum_total']
            
            # Try to find matching game in scores
            for key, score_data in scores.items():
                if (fuzzy_match(home, score_data['home_team']) and 
                    fuzzy_match(away, score_data['away_team'])):
                    
                    actual = score_data['total']
                    tracking.at[idx, 'actual_total'] = actual
                    tracking.at[idx, 'status'] = 'COMPLETE'
                    
                    if actual >= min_total:
                        tracking.at[idx, 'result'] = 'WIN'
                    else:
                        tracking.at[idx, 'result'] = 'LOSS'
                    
                    updated += 1
                    break
    
    save_mc_tracking(tracking)
    print(f"Updated {updated} games")
    
    # Print summary
    complete = tracking[tracking['status'] == 'COMPLETE']
    if not complete.empty:
        yes_complete = complete[complete['decision'] == 'YES']
        wins = len(yes_complete[yes_complete['result'] == 'WIN'])
        losses = len(yes_complete[yes_complete['result'] == 'LOSS'])
        
        print(f"\n📊 MONTE CARLO RESULTS")
        print(f"   YES picks: {wins}-{losses}")
        if wins + losses > 0:
            print(f"   Win rate: {wins/(wins+losses)*100:.1f}%")
        
        # Show any losses
        loss_games = yes_complete[yes_complete['result'] == 'LOSS']
        if not loss_games.empty:
            print(f"\n❌ LOSSES:")
            for _, game in loss_games.iterrows():
                print(f"   {game['away_team']} @ {game['home_team']}")
                print(f"      Min: {game['minimum_total']} | Actual: {game['actual_total']} | Hit Rate: {game['hit_rate']:.1f}%")


if __name__ == "__main__":
    print("=" * 60)
    print("🎲 MONTE CARLO RESULTS TRACKER")
    print("=" * 60)
    update_tracking()
