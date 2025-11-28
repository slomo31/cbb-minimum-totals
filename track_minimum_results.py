"""
Track Minimum Totals Results - FIXED
Uses NCAA API for scores (same as MC tracker)
"""
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import requests


NCAA_API = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"


def fetch_final_scores(date_str):
    """Fetch final scores from NCAA API"""
    url = f"{NCAA_API}/{date_str}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            games = data.get('games', [])
            
            results = {}
            for game_wrapper in games:
                game = game_wrapper.get('game', game_wrapper)
                
                if game.get('gameState') == 'final' or game.get('finalMessage') == 'FINAL':
                    home = game.get('home', {})
                    away = game.get('away', {})
                    
                    home_names = home.get('names', {})
                    away_names = away.get('names', {})
                    
                    home_name = home_names.get('short', '') or home_names.get('full', '')
                    away_name = away_names.get('short', '') or away_names.get('full', '')
                    
                    try:
                        home_score = int(home.get('score', 0))
                        away_score = int(away.get('score', 0))
                    except:
                        continue
                    
                    total = home_score + away_score
                    
                    if home_name and away_name:
                        results[f"{away_name}@{home_name}"] = {
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
    """Fuzzy match team names"""
    if not name1 or not name2:
        return False
    
    n1 = name1.lower().replace('/', ' ').replace('-', ' ')
    n2 = name2.lower().replace('/', ' ').replace('-', ' ')
    
    if n1 in n2 or n2 in n1:
        return True
    
    words1 = set(n1.split())
    words2 = set(n2.split())
    common_words = {'the', 'of', 'at', 'state', 'university', 'college'}
    words1 -= common_words
    words2 -= common_words
    
    overlap = words1 & words2
    return len(overlap) >= 1


class ResultsTracker:
    """Track betting results for minimum totals picks"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.tracking_file = self.data_dir / "tracking_results.csv"
        
    def load_tracking(self):
        if self.tracking_file.exists():
            return pd.read_csv(self.tracking_file)
        return pd.DataFrame()
    
    def save_tracking(self, df):
        df.to_csv(self.tracking_file, index=False)
    
    def add_picks_to_tracking(self, predictions_file=None):
        """Add today's picks to tracking"""
        if predictions_file is None:
            predictions_file = self.data_dir / "predictions.csv"
        
        if not predictions_file.exists():
            print("❌ No predictions file found")
            return
        
        predictions = pd.read_csv(predictions_file)
        tracking = self.load_tracking()
        
        picks = predictions[predictions['decision'].isin(['YES', 'MAYBE'])].copy()
        
        if picks.empty:
            print("No YES/MAYBE picks to track")
            return
        
        picks['pick_date'] = datetime.now().strftime('%Y-%m-%d')
        picks['status'] = 'PENDING'
        picks['actual_total'] = 0.0
        picks['result'] = ''
        
        if not tracking.empty and 'game_id' in tracking.columns and 'game_id' in picks.columns:
            existing_ids = set(tracking['game_id'].astype(str))
            picks = picks[~picks['game_id'].astype(str).isin(existing_ids)]
        
        if picks.empty:
            print("All picks already in tracking")
            return
        
        tracking = pd.concat([tracking, picks], ignore_index=True)
        self.save_tracking(tracking)
        print(f"✅ Added {len(picks)} picks to tracking")
    
    def update_results(self):
        """Update pending picks with final scores"""
        tracking = self.load_tracking()
        
        if tracking.empty:
            print("No tracking data")
            return
        
        pending = tracking[tracking['status'] == 'PENDING']
        if pending.empty:
            print("No pending picks")
            return
        
        print(f"Updating {len(pending)} pending picks...")
        
        # Fetch scores for last 3 days
        all_scores = {}
        for days_ago in range(0, 3):
            date = datetime.now() - timedelta(days=days_ago)
            date_str = date.strftime('%Y/%m/%d')
            print(f"📅 Checking {date_str}...")
            
            scores = fetch_final_scores(date_str)
            print(f"   Found {len(scores)} final games")
            all_scores.update(scores)
        
        # Update matches
        updated = 0
        for idx, row in tracking.iterrows():
            if row['status'] != 'PENDING':
                continue
            
            home = str(row.get('home_team', ''))
            away = str(row.get('away_team', ''))
            min_total = float(row.get('minimum_total', 0))
            
            for key, score_data in all_scores.items():
                if (fuzzy_match(home, score_data['home_team']) and 
                    fuzzy_match(away, score_data['away_team'])):
                    
                    actual = score_data['total']
                    tracking.at[idx, 'actual_total'] = float(actual)
                    tracking.at[idx, 'status'] = 'COMPLETE'
                    
                    if actual >= min_total:
                        tracking.at[idx, 'result'] = 'WIN'
                        print(f"   ✅ {away} @ {home}: {actual} >= {min_total}")
                    else:
                        tracking.at[idx, 'result'] = 'LOSS'
                        print(f"   ❌ {away} @ {home}: {actual} < {min_total}")
                    
                    updated += 1
                    break
        
        self.save_tracking(tracking)
        print(f"✅ Updated {updated} picks")
    
    def print_stats(self):
        """Print performance statistics"""
        tracking = self.load_tracking()
        
        if tracking.empty:
            print("No tracking data")
            return
        
        complete = tracking[tracking['status'] == 'COMPLETE']
        pending = tracking[tracking['status'] == 'PENDING']
        
        print("=" * 60)
        print("📊 LEGACY SYSTEM PERFORMANCE")
        print("=" * 60)
        
        print(f"Total picks tracked: {len(tracking)}")
        print(f"Completed: {len(complete)}")
        print(f"Pending: {len(pending)}")
        
        if not complete.empty:
            # Overall
            wins = len(complete[complete['result'] == 'WIN'])
            losses = len(complete[complete['result'] == 'LOSS'])
            win_rate = wins / len(complete) * 100 if len(complete) > 0 else 0
            
            print(f"\n📈 OVERALL: {wins}-{losses} ({win_rate:.1f}%)")
            
            # By decision type
            for decision in ['YES', 'MAYBE']:
                subset = complete[complete['decision'] == decision]
                if not subset.empty:
                    w = len(subset[subset['result'] == 'WIN'])
                    l = len(subset[subset['result'] == 'LOSS'])
                    wr = w / len(subset) * 100 if len(subset) > 0 else 0
                    print(f"   🟢 {decision}: {w}-{l} ({wr:.1f}%)")
            
            # Show losses
            losses_df = complete[complete['result'] == 'LOSS']
            if not losses_df.empty:
                print(f"\n❌ LOSSES:")
                for _, row in losses_df.iterrows():
                    print(f"   {row['away_team']} @ {row['home_team']}")
                    print(f"      Line: {row['minimum_total']} | Actual: {row['actual_total']}")
        
        # Show some pending
        if not pending.empty:
            print(f"\n⏳ PENDING ({len(pending)}):")
            for _, row in pending.head(5).iterrows():
                print(f"   {row['away_team']} @ {row['home_team']}")
                print(f"      OVER {row['minimum_total']}")


def main():
    print("=" * 60)
    print("📊 LEGACY SYSTEM - RESULTS TRACKER")
    print("=" * 60)
    
    tracker = ResultsTracker()
    
    print("\n1️⃣ Adding picks to tracking...")
    tracker.add_picks_to_tracking()
    
    print("\n2️⃣ Updating results from completed games...")
    tracker.update_results()
    
    print("\n")
    tracker.print_stats()


if __name__ == "__main__":
    main()
