"""
Minimum Total Predictor
Core prediction engine - works with or without team stats
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CONFIDENCE_THRESHOLDS, DATA_DIR, TEAM_STATS_FILE


class MinimumTotalPredictor:
    """
    Prediction engine for minimum alternate totals
    Uses statistical analysis when available, falls back to line analysis
    """
    
    # CBB averages
    LEAGUE_AVG_TOTAL = 145.0
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / DATA_DIR
        self.team_stats = None
        self._load_data()
        
    def _load_data(self):
        """Load team stats if available"""
        stats_file = self.data_dir / TEAM_STATS_FILE
        if stats_file.exists():
            self.team_stats = pd.read_csv(stats_file)
            print(f"Loaded team stats: {len(self.team_stats)} teams")
        else:
            print(f"Note: No team stats file - using line-based analysis only")
    
    def get_team_avg(self, team_name):
        """Get team's average total from stats"""
        if self.team_stats is None:
            return None
        
        team_lower = team_name.lower()
        for _, row in self.team_stats.iterrows():
            if team_lower in str(row.get('team', '')).lower():
                return row.get('avg_total_points')
        return None
    
    def analyze_game(self, home_team, away_team, minimum_total, game_date=None):
        """
        Analyze a game and predict if it will go OVER minimum total
        """
        if game_date is None:
            game_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get team averages if available
        home_avg = self.get_team_avg(home_team)
        away_avg = self.get_team_avg(away_team)
        
        # Calculate expected total
        if home_avg and away_avg:
            # Use team data
            expected_total = (home_avg + away_avg) / 2 + 2  # +2 for home court
            data_quality = "TEAM_STATS"
        else:
            # Use line-based estimation
            # Minimum totals are typically 10-20% below the standard line
            # Standard line is usually close to expected total
            expected_total = minimum_total * 1.12  # Estimate ~12% above minimum
            data_quality = "LINE_ESTIMATE"
        
        # Calculate buffer (how far expected is above minimum)
        buffer = expected_total - minimum_total
        
        # Calculate confidence based on buffer
        # Larger buffer = higher confidence the game goes OVER
        if buffer >= 20:
            confidence = 92
        elif buffer >= 15:
            confidence = 87
        elif buffer >= 12:
            confidence = 83
        elif buffer >= 10:
            confidence = 80
        elif buffer >= 8:
            confidence = 77
        elif buffer >= 5:
            confidence = 73
        elif buffer >= 3:
            confidence = 68
        else:
            confidence = 60 + buffer * 2
        
        # Adjust confidence if we have real team data
        if data_quality == "TEAM_STATS":
            confidence = min(95, confidence + 3)
        
        confidence = max(50, min(95, confidence))
        
        # Make decision
        if confidence >= CONFIDENCE_THRESHOLDS['YES']:
            decision = 'YES'
            reason = f"High confidence ({confidence:.0f}%) - BET 3%"
        elif confidence >= CONFIDENCE_THRESHOLDS['MAYBE']:
            decision = 'MAYBE'
            reason = f"Medium confidence ({confidence:.0f}%) - Consider 2%"
        else:
            decision = 'NO'
            reason = f"Low confidence ({confidence:.0f}%) - SKIP"
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'game_date': game_date,
            'minimum_total': minimum_total,
            'expected_total': round(expected_total, 1),
            'buffer': round(buffer, 1),
            'confidence_pct': round(confidence, 1),
            'decision': decision,
            'decision_reason': reason,
            'data_quality': data_quality,
            'analysis_time': datetime.now().isoformat()
        }
    
    def analyze_upcoming_games(self, upcoming_df=None):
        """Analyze all upcoming games"""
        if upcoming_df is None:
            upcoming_file = self.data_dir / 'upcoming_games.csv'
            if upcoming_file.exists():
                upcoming_df = pd.read_csv(upcoming_file)
            else:
                print("No upcoming games file found")
                return pd.DataFrame()
        
        if upcoming_df.empty:
            return pd.DataFrame()
        
        print(f"\nAnalyzing {len(upcoming_df)} upcoming games...")
        print("=" * 70)
        
        predictions = []
        
        for idx, game in upcoming_df.iterrows():
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            minimum_total = game.get('minimum_total')
            game_date = game.get('game_date', datetime.now().strftime('%Y-%m-%d'))
            
            if pd.isna(minimum_total) or not home_team or not away_team:
                continue
            
            print(f"\n{idx+1}. {away_team} @ {home_team}")
            print(f"   Minimum Total: {minimum_total}")
            
            try:
                result = self.analyze_game(home_team, away_team, minimum_total, game_date)
                result['game_id'] = game.get('game_id')
                result['game_time'] = game.get('game_time')
                predictions.append(result)
                
                print(f"   Expected: {result['expected_total']} | Buffer: {result['buffer']:+.1f}")
                print(f"   Confidence: {result['confidence_pct']:.0f}% | Decision: {result['decision']}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        return pd.DataFrame(predictions)
    
    def print_predictions(self, predictions_df):
        """Print formatted predictions"""
        if predictions_df.empty:
            print("No predictions to display")
            return
        
        print("\n" + "=" * 70)
        print("CBB MINIMUM TOTALS PREDICTIONS")
        print("=" * 70)
        
        for decision in ['YES', 'MAYBE', 'NO']:
            picks = predictions_df[predictions_df['decision'] == decision]
            if picks.empty:
                continue
            
            icon = '🟢' if decision == 'YES' else '🟡' if decision == 'MAYBE' else '🔴'
            print(f"\n{icon} {decision} PICKS ({len(picks)})")
            print("-" * 50)
            
            for _, pick in picks.iterrows():
                print(f"\n{pick['away_team']} @ {pick['home_team']}")
                print(f"  Line: {pick['minimum_total']} | Expected: {pick['expected_total']} | Buffer: {pick['buffer']:+.1f}")
                print(f"  Confidence: {pick['confidence_pct']:.0f}%")
        
        # Summary
        yes_count = len(predictions_df[predictions_df['decision'] == 'YES'])
        maybe_count = len(predictions_df[predictions_df['decision'] == 'MAYBE'])
        print(f"\n{'='*70}")
        print(f"SUMMARY: {yes_count} YES picks, {maybe_count} MAYBE picks")
        print(f"{'='*70}")


def main():
    predictor = MinimumTotalPredictor()
    predictions = predictor.analyze_upcoming_games()
    
    if not predictions.empty:
        predictor.print_predictions(predictions)
        
        # Save
        output_file = predictor.data_dir / 'predictions.csv'
        predictions.to_csv(output_file, index=False)
        print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()
