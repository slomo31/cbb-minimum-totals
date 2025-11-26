"""
Game Results Collector
Collects final scores for completed games to update predictions
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CURRENT_SEASON, DATA_DIR, COMPLETED_GAMES_FILE

try:
    import cbbpy.mens_scraper as cbb
except ImportError:
    print("CBBpy not installed. Run: pip install cbbpy")
    cbb = None


class GameResultsCollector:
    """Collect final scores for CBB games"""
    
    def __init__(self, season=CURRENT_SEASON):
        self.season = season
        self.data_dir = Path(__file__).parent.parent / DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        
    def get_games_for_date(self, date_str):
        """Get all games for a specific date"""
        if cbb is None:
            print("CBBpy not available")
            return pd.DataFrame()
        
        try:
            # CBBpy uses date format: YYYY-MM-DD
            # Get scoreboard for date
            games_info, games_box, games_pbp = cbb.get_games_date(date_str)
            return games_info
        except Exception as e:
            print(f"Error getting games for {date_str}: {e}")
            return pd.DataFrame()
    
    def get_game_result(self, game_id):
        """Get the final result for a specific game"""
        if cbb is None:
            return None
        
        try:
            game_info = cbb.get_game_info(game_id)
            return game_info
        except Exception as e:
            print(f"Error getting game {game_id}: {e}")
            return None
    
    def parse_game_score(self, game_info):
        """Parse game info to extract final score"""
        if game_info is None or game_info.empty:
            return None
        
        result = {
            'game_id': None,
            'home_team': None,
            'away_team': None,
            'home_score': None,
            'away_score': None,
            'total_score': None,
            'game_date': None,
            'status': None
        }
        
        try:
            if isinstance(game_info, pd.DataFrame) and len(game_info) > 0:
                row = game_info.iloc[0]
                
                result['game_id'] = row.get('game_id')
                result['home_team'] = row.get('home_team')
                result['away_team'] = row.get('away_team')
                result['home_score'] = row.get('home_score')
                result['away_score'] = row.get('away_score')
                
                if result['home_score'] is not None and result['away_score'] is not None:
                    result['total_score'] = int(result['home_score']) + int(result['away_score'])
                
                result['game_date'] = row.get('game_date')
                result['status'] = row.get('status', 'Final')
                
        except Exception as e:
            print(f"Error parsing game info: {e}")
        
        return result
    
    def collect_results_for_date_range(self, start_date, end_date=None):
        """Collect results for a range of dates"""
        if end_date is None:
            end_date = datetime.now().date()
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        all_results = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"Collecting results for {date_str}...")
            
            try:
                games = self.get_games_for_date(date_str)
                
                if games is not None and not games.empty:
                    for _, game in games.iterrows():
                        result = {
                            'game_id': game.get('game_id'),
                            'game_date': date_str,
                            'home_team': game.get('home_team'),
                            'away_team': game.get('away_team'),
                            'home_score': game.get('home_score'),
                            'away_score': game.get('away_score'),
                            'total_score': None,
                            'status': game.get('status', 'Final')
                        }
                        
                        # Calculate total
                        try:
                            if result['home_score'] is not None and result['away_score'] is not None:
                                result['total_score'] = int(result['home_score']) + int(result['away_score'])
                        except:
                            pass
                        
                        all_results.append(result)
                    
                    print(f"  Found {len(games)} games")
                else:
                    print(f"  No games found")
                    
            except Exception as e:
                print(f"  Error: {e}")
            
            current_date += timedelta(days=1)
            time.sleep(1)  # Rate limiting
        
        return pd.DataFrame(all_results)
    
    def collect_yesterday_results(self):
        """Collect results from yesterday"""
        yesterday = (datetime.now() - timedelta(days=1)).date()
        return self.collect_results_for_date_range(yesterday, yesterday)
    
    def update_tracking_with_results(self, tracking_file=None):
        """Update tracking file with actual game results"""
        if tracking_file is None:
            tracking_file = self.data_dir.parent / 'output_archive' / 'decisions' / 'tracking_results.csv'
        
        if not tracking_file.exists():
            print(f"Tracking file not found: {tracking_file}")
            return None
        
        # Load tracking data
        tracking_df = pd.read_csv(tracking_file)
        
        # Filter pending games
        pending = tracking_df[tracking_df['result'] == 'PENDING'].copy()
        
        if pending.empty:
            print("No pending games to update")
            return tracking_df
        
        print(f"Updating {len(pending)} pending games...")
        
        for idx, row in pending.iterrows():
            game_date = row.get('game_date')
            home_team = row.get('home_team')
            away_team = row.get('away_team')
            minimum_total = row.get('minimum_total')
            
            # Try to find the game result
            results = self.collect_results_for_date_range(game_date, game_date)
            
            if not results.empty:
                # Find matching game
                mask = (
                    (results['home_team'].str.lower().str.contains(home_team.lower(), na=False)) |
                    (results['away_team'].str.lower().str.contains(away_team.lower(), na=False))
                )
                matches = results[mask]
                
                if not matches.empty:
                    game = matches.iloc[0]
                    total_score = game.get('total_score')
                    
                    if total_score is not None:
                        tracking_df.loc[idx, 'actual_total'] = total_score
                        
                        if total_score > minimum_total:
                            tracking_df.loc[idx, 'result'] = 'WIN'
                        else:
                            tracking_df.loc[idx, 'result'] = 'LOSS'
                        
                        print(f"  {away_team} @ {home_team}: {total_score} total ({'WIN' if total_score > minimum_total else 'LOSS'})")
        
        # Save updated tracking
        tracking_df.to_csv(tracking_file, index=False)
        print(f"\nUpdated tracking saved to {tracking_file}")
        
        return tracking_df
    
    def save_completed_games(self, df):
        """Save completed games to CSV"""
        if df.empty:
            return
        
        output_path = self.data_dir / COMPLETED_GAMES_FILE
        
        # Append to existing if file exists
        if output_path.exists():
            existing = pd.read_csv(output_path)
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['game_id'], keep='last')
            combined.to_csv(output_path, index=False)
        else:
            df.to_csv(output_path, index=False)
        
        print(f"Saved completed games to {output_path}")


def main():
    """Main function to collect game results"""
    collector = GameResultsCollector()
    
    print("=" * 60)
    print("CBB GAME RESULTS COLLECTOR")
    print("=" * 60)
    
    # Collect yesterday's results
    print("\nCollecting yesterday's results...")
    results = collector.collect_yesterday_results()
    
    if not results.empty:
        collector.save_completed_games(results)
        
        print(f"\nCollected {len(results)} games")
        print("\nSample results:")
        for _, game in results.head(5).iterrows():
            if game['total_score']:
                print(f"  {game['away_team']} @ {game['home_team']}: {game['total_score']} total")
    else:
        print("No results found for yesterday")
    
    # Update tracking file
    print("\n" + "=" * 60)
    print("UPDATING TRACKING FILE")
    print("=" * 60)
    collector.update_tracking_with_results()


if __name__ == "__main__":
    main()
