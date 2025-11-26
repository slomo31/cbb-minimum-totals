"""
Rest Days Calculator
Analyzes rest days and schedule fatigue impact on totals
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CONFIDENCE_WEIGHTS


class RestDaysCalculator:
    """Calculate rest days impact on totals prediction"""
    
    # Weight for this factor
    MAX_SCORE = CONFIDENCE_WEIGHTS['rest_schedule']  # 10 points
    
    # Impact thresholds
    BACK_TO_BACK_IMPACT = -3.0  # Reduces total expectation
    SHORT_REST_IMPACT = -1.5   # 1 day rest
    NORMAL_REST_IMPACT = 0.0   # 2-3 days rest
    LONG_REST_IMPACT = 1.0     # 4+ days rest (may be rusty but fresh)
    VERY_LONG_REST_IMPACT = 0.0  # 7+ days (could go either way)
    
    def __init__(self, completed_games_df=None):
        self.completed_games = completed_games_df
        
    def load_completed_games(self, filepath):
        """Load completed games from CSV"""
        self.completed_games = pd.read_csv(filepath)
        return self.completed_games
    
    def get_last_game_date(self, team_name, before_date=None):
        """Get the date of a team's most recent game"""
        if self.completed_games is None:
            return None
        
        if before_date is None:
            before_date = datetime.now().date()
        elif isinstance(before_date, str):
            before_date = datetime.strptime(before_date, '%Y-%m-%d').date()
        
        # Find games involving this team
        mask = (
            self.completed_games['home_team'].str.lower().str.contains(team_name.lower(), na=False) |
            self.completed_games['away_team'].str.lower().str.contains(team_name.lower(), na=False)
        )
        
        team_games = self.completed_games[mask].copy()
        
        if team_games.empty:
            return None
        
        # Convert dates and filter
        try:
            team_games['game_date_parsed'] = pd.to_datetime(team_games['game_date']).dt.date
            team_games = team_games[team_games['game_date_parsed'] < before_date]
            
            if team_games.empty:
                return None
            
            return team_games['game_date_parsed'].max()
        except Exception as e:
            print(f"Error parsing dates for {team_name}: {e}")
            return None
    
    def calculate_rest_days(self, team_name, game_date):
        """Calculate days of rest for a team before a game"""
        if isinstance(game_date, str):
            game_date = datetime.strptime(game_date, '%Y-%m-%d').date()
        
        last_game = self.get_last_game_date(team_name, game_date)
        
        if last_game is None:
            # No previous game found - assume normal rest
            return {
                'team': team_name,
                'game_date': game_date,
                'last_game': None,
                'days_rest': None,
                'rest_category': 'UNKNOWN'
            }
        
        days_rest = (game_date - last_game).days
        
        # Categorize rest
        if days_rest <= 1:
            category = 'BACK_TO_BACK'
        elif days_rest == 2:
            category = 'SHORT'
        elif days_rest <= 4:
            category = 'NORMAL'
        elif days_rest <= 7:
            category = 'EXTENDED'
        else:
            category = 'VERY_LONG'
        
        return {
            'team': team_name,
            'game_date': game_date,
            'last_game': last_game,
            'days_rest': days_rest,
            'rest_category': category
        }
    
    def calculate_rest_impact(self, home_team, away_team, game_date):
        """Calculate combined rest impact on expected total"""
        home_rest = self.calculate_rest_days(home_team, game_date)
        away_rest = self.calculate_rest_days(away_team, game_date)
        
        # Calculate impact for each team
        def get_impact(rest_info):
            if rest_info['rest_category'] == 'UNKNOWN':
                return 0.0
            elif rest_info['rest_category'] == 'BACK_TO_BACK':
                return self.BACK_TO_BACK_IMPACT
            elif rest_info['rest_category'] == 'SHORT':
                return self.SHORT_REST_IMPACT
            elif rest_info['rest_category'] == 'NORMAL':
                return self.NORMAL_REST_IMPACT
            elif rest_info['rest_category'] == 'EXTENDED':
                return self.LONG_REST_IMPACT
            else:  # VERY_LONG
                return self.VERY_LONG_REST_IMPACT
        
        home_impact = get_impact(home_rest)
        away_impact = get_impact(away_rest)
        
        # Combined impact (both teams affect the total)
        combined_impact = home_impact + away_impact
        
        # Determine overall rest situation
        if home_rest['rest_category'] == 'BACK_TO_BACK' or away_rest['rest_category'] == 'BACK_TO_BACK':
            situation = 'FATIGUE_RISK'
        elif home_rest['rest_category'] == 'SHORT' and away_rest['rest_category'] == 'SHORT':
            situation = 'BOTH_TIRED'
        elif home_rest['rest_category'] == 'UNKNOWN' and away_rest['rest_category'] == 'UNKNOWN':
            situation = 'UNKNOWN'
        elif combined_impact > 0:
            situation = 'FAVORABLE'
        elif combined_impact < 0:
            situation = 'UNFAVORABLE'
        else:
            situation = 'NEUTRAL'
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_rest': home_rest,
            'away_rest': away_rest,
            'home_impact': home_impact,
            'away_impact': away_impact,
            'combined_impact': combined_impact,
            'situation': situation
        }
    
    def score_matchup(self, home_team, away_team, game_date, minimum_total):
        """
        Score a matchup for rest/schedule factor
        
        Returns score from 0-10 based on rest impact
        """
        impact = self.calculate_rest_impact(home_team, away_team, game_date)
        
        situation = impact['situation']
        combined = impact['combined_impact']
        
        # Base score based on situation
        if situation == 'UNKNOWN':
            base_score = self.MAX_SCORE / 2  # Neutral
            confidence = 'LOW'
        elif situation == 'FATIGUE_RISK':
            base_score = 3
            confidence = 'LOW'
        elif situation == 'BOTH_TIRED':
            base_score = 4
            confidence = 'MEDIUM'
        elif situation == 'UNFAVORABLE':
            base_score = 5
            confidence = 'MEDIUM'
        elif situation == 'NEUTRAL':
            base_score = 6
            confidence = 'MEDIUM'
        elif situation == 'FAVORABLE':
            base_score = 8
            confidence = 'HIGH'
        else:
            base_score = 5
            confidence = 'MEDIUM'
        
        # Adjust based on specific impact
        score = base_score + combined
        score = max(0, min(self.MAX_SCORE, score))
        
        # Build details string
        home_days = impact['home_rest']['days_rest']
        away_days = impact['away_rest']['days_rest']
        home_cat = impact['home_rest']['rest_category']
        away_cat = impact['away_rest']['rest_category']
        
        details_parts = []
        if home_days is not None:
            details_parts.append(f"Home: {home_days}d rest ({home_cat})")
        if away_days is not None:
            details_parts.append(f"Away: {away_days}d rest ({away_cat})")
        details = ", ".join(details_parts) if details_parts else "No rest data available"
        
        return {
            'score': round(score, 1),
            'max_score': self.MAX_SCORE,
            'confidence': confidence,
            'situation': situation,
            'total_adjustment': round(combined, 1),
            'home_rest_days': home_days,
            'away_rest_days': away_days,
            'details': details
        }


def main():
    """Test the rest days calculator"""
    from config.season_config import DATA_DIR, COMPLETED_GAMES_FILE
    
    data_dir = Path(__file__).parent.parent / DATA_DIR
    games_file = data_dir / COMPLETED_GAMES_FILE
    
    calculator = RestDaysCalculator()
    
    if games_file.exists():
        calculator.load_completed_games(games_file)
        
        print("=" * 60)
        print("REST DAYS CALCULATOR TEST")
        print("=" * 60)
        
        # Test with sample date (tomorrow)
        test_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test individual team rest
        test_teams = ['Duke', 'Kentucky', 'Kansas', 'UCLA']
        
        for team in test_teams:
            rest = calculator.calculate_rest_days(team, test_date)
            print(f"\n{team} (game on {test_date}):")
            print(f"  Last Game: {rest['last_game']}")
            print(f"  Days Rest: {rest['days_rest']}")
            print(f"  Category: {rest['rest_category']}")
        
        # Test matchup scoring
        print("\n" + "=" * 60)
        print("MATCHUP REST SCORING")
        print("=" * 60)
        
        result = calculator.score_matchup('Duke', 'Kentucky', test_date, 140.5)
        print(f"\nDuke vs Kentucky (min: 140.5):")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print(f"Games file not found: {games_file}")
        print("Run game_results_collector.py first")
        
        # Test with no data
        calculator = RestDaysCalculator()
        result = calculator.score_matchup('Duke', 'Kentucky', '2025-11-27', 140.5)
        print(f"\nWithout historical data:")
        for key, value in result.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
