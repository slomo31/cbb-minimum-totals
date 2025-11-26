"""
Track Minimum Totals Results
Records WIN/LOSS for each pick and calculates performance
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import requests


class ResultsTracker:
    """Track betting results for minimum totals picks"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.tracking_file = self.data_dir / "tracking_results.csv"
        self.decisions_dir = Path(__file__).parent / "output_archive" / "decisions"
        
    def load_tracking(self):
        """Load existing tracking data"""
        if self.tracking_file.exists():
            return pd.read_csv(self.tracking_file)
        return pd.DataFrame()
    
    def save_tracking(self, df):
        """Save tracking data"""
        df.to_csv(self.tracking_file, index=False)
        print(f"✅ Saved tracking to {self.tracking_file}")
    
    def add_picks_to_tracking(self, predictions_file=None):
        """Add today's picks to tracking (before games start)"""
        if predictions_file is None:
            predictions_file = self.data_dir / "predictions.csv"
        
        if not predictions_file.exists():
            print("❌ No predictions file found")
            return
        
        predictions = pd.read_csv(predictions_file)
        tracking = self.load_tracking()
        
        # Only add YES and MAYBE picks
        picks = predictions[predictions['decision'].isin(['YES', 'MAYBE'])].copy()
        
        if picks.empty:
            print("No YES/MAYBE picks to track")
            return
        
        # Add tracking columns
        picks['pick_date'] = datetime.now().strftime('%Y-%m-%d')
        picks['status'] = 'PENDING'
        picks['actual_total'] = None
        picks['result'] = None
        
        # Check for duplicates
        if not tracking.empty:
            existing_ids = set(tracking['game_id'].astype(str))
            picks = picks[~picks['game_id'].astype(str).isin(existing_ids)]
        
        if picks.empty:
            print("All picks already in tracking")
            return
        
        # Append new picks
        tracking = pd.concat([tracking, picks], ignore_index=True)
        self.save_tracking(tracking)
        print(f"✅ Added {len(picks)} picks to tracking")
    
    def get_scores_from_espn(self, game_date):
        """Fetch final scores from ESPN for a specific date"""
        date_str = game_date.replace('-', '')
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={date_str}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            scores = {}
            
            for event in data.get('events', []):
                status = event.get('status', {}).get('type', {}).get('name', '')
                if status != 'STATUS_FINAL':
                    continue
                
                competitors = event.get('competitions', [{}])[0].get('competitors', [])
                if len(competitors) != 2:
                    continue
                
                home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
                away = next((c for c in competitors if c.get('homeAway') == 'away'), {})
                
                home_team = home.get('team', {}).get('displayName', '')
                away_team = away.get('team', {}).get('displayName', '')
                home_score = int(home.get('score', 0))
                away_score = int(away.get('score', 0))
                total = home_score + away_score
                
                # Store by team names (we'll match loosely)
                key = f"{away_team} @ {home_team}"
                scores[key] = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'total': total
                }
            
            return scores
        except Exception as e:
            print(f"Error fetching scores: {e}")
            return {}
    
    def update_results(self):
        """Update pending picks with actual results"""
        tracking = self.load_tracking()
        
        if tracking.empty:
            print("No picks to update")
            return
        
        pending = tracking[tracking['status'] == 'PENDING']
        
        if pending.empty:
            print("No pending picks")
            return
        
        print(f"Updating {len(pending)} pending picks...")
        
        # Get unique dates
        dates = pending['game_date'].dropna().unique()
        
        updated = 0
        for game_date in dates:
            print(f"\n📅 Checking {game_date}...")
            scores = self.get_scores_from_espn(game_date)
            
            if not scores:
                print("   No final scores yet")
                continue
            
            print(f"   Found {len(scores)} final games")
            
            # Match picks to scores
            for idx, pick in pending[pending['game_date'] == game_date].iterrows():
                home = pick.get('home_team', '')
                away = pick.get('away_team', '')
                minimum = pick.get('minimum_total', 0)
                
                # Try to find matching score
                matched = None
                for key, score in scores.items():
                    if (home.lower()[:10] in score['home_team'].lower() or 
                        score['home_team'].lower()[:10] in home.lower()):
                        if (away.lower()[:10] in score['away_team'].lower() or
                            score['away_team'].lower()[:10] in away.lower()):
                            matched = score
                            break
                
                if matched:
                    actual_total = matched['total']
                    result = 'WIN' if actual_total > minimum else 'LOSS'
                    
                    tracking.loc[idx, 'actual_total'] = actual_total
                    tracking.loc[idx, 'result'] = result
                    tracking.loc[idx, 'status'] = 'COMPLETE'
                    
                    icon = '✅' if result == 'WIN' else '❌'
                    print(f"   {icon} {away[:20]} @ {home[:20]}: {actual_total} vs {minimum} = {result}")
                    updated += 1
        
        if updated > 0:
            self.save_tracking(tracking)
        
        print(f"\n✅ Updated {updated} picks")
    
    def print_stats(self):
        """Print performance statistics"""
        tracking = self.load_tracking()
        
        if tracking.empty:
            print("No tracking data yet")
            return
        
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE STATISTICS")
        print("=" * 60)
        
        complete = tracking[tracking['status'] == 'COMPLETE']
        pending = tracking[tracking['status'] == 'PENDING']
        
        print(f"\nTotal picks tracked: {len(tracking)}")
        print(f"Completed: {len(complete)}")
        print(f"Pending: {len(pending)}")
        
        if not complete.empty:
            # Overall stats
            wins = len(complete[complete['result'] == 'WIN'])
            losses = len(complete[complete['result'] == 'LOSS'])
            win_rate = wins / len(complete) * 100
            
            print(f"\n📈 OVERALL: {wins}-{losses} ({win_rate:.1f}%)")
            
            # By decision type
            for decision in ['YES', 'MAYBE']:
                subset = complete[complete['decision'] == decision]
                if not subset.empty:
                    w = len(subset[subset['result'] == 'WIN'])
                    l = len(subset[subset['result'] == 'LOSS'])
                    wr = w / len(subset) * 100 if len(subset) > 0 else 0
                    icon = '🟢' if decision == 'YES' else '🟡'
                    print(f"   {icon} {decision}: {w}-{l} ({wr:.1f}%)")
            
            # Recent results
            print("\n📋 RECENT RESULTS:")
            recent = complete.tail(10).sort_values('game_date', ascending=False)
            for _, pick in recent.iterrows():
                icon = '✅' if pick['result'] == 'WIN' else '❌'
                print(f"   {icon} {pick['away_team'][:20]} @ {pick['home_team'][:20]}")
                print(f"      Line: {pick['minimum_total']} | Actual: {pick['actual_total']} | {pick['result']}")
        
        # Pending picks
        if not pending.empty:
            print(f"\n⏳ PENDING PICKS ({len(pending)}):")
            for _, pick in pending.head(10).iterrows():
                print(f"   {pick['away_team'][:25]} @ {pick['home_team'][:25]}")
                print(f"      OVER {pick['minimum_total']} ({pick['confidence_pct']:.0f}% conf)")
        
        print("=" * 60)


def main():
    tracker = ResultsTracker()
    
    print("=" * 60)
    print("CBB MINIMUM TOTALS - RESULTS TRACKER")
    print("=" * 60)
    
    # Add today's picks
    print("\n1️⃣ Adding picks to tracking...")
    tracker.add_picks_to_tracking()
    
    # Update results
    print("\n2️⃣ Updating results from completed games...")
    tracker.update_results()
    
    # Show stats
    tracker.print_stats()


if __name__ == "__main__":
    main()
