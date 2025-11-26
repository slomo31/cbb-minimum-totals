"""
Offensive Efficiency Analyzer
Analyzes offensive output and efficiency metrics
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CONFIDENCE_WEIGHTS


class OffensiveEfficiencyAnalyzer:
    """Analyze offensive efficiency for totals prediction"""
    
    # CBB average points per game (approximate)
    LEAGUE_AVG_PPG = 72.0
    LEAGUE_AVG_TOTAL = 144.0
    
    # Weight for this factor
    MAX_SCORE = CONFIDENCE_WEIGHTS['offensive_efficiency']  # 30 points
    
    def __init__(self, team_stats_df=None):
        self.team_stats = team_stats_df
        
    def load_team_stats(self, filepath):
        """Load team stats from CSV"""
        self.team_stats = pd.read_csv(filepath)
        return self.team_stats
    
    def get_team_stats(self, team_name):
        """Get stats for a specific team"""
        if self.team_stats is None:
            return None
        
        # Fuzzy match team name
        mask = self.team_stats['team'].str.lower().str.contains(team_name.lower())
        matches = self.team_stats[mask]
        
        if not matches.empty:
            return matches.iloc[0].to_dict()
        return None
    
    def calculate_offensive_rating(self, team_name):
        """Calculate offensive rating for a team"""
        stats = self.get_team_stats(team_name)
        
        if stats is None:
            return None
        
        avg_scored = stats.get('avg_points_scored', 0)
        
        # Calculate rating relative to league average
        # Rating = (Team Avg / League Avg) * 100
        rating = (avg_scored / self.LEAGUE_AVG_PPG) * 100
        
        return {
            'team': team_name,
            'avg_points_scored': avg_scored,
            'offensive_rating': round(rating, 1),
            'rating_vs_avg': round(rating - 100, 1)
        }
    
    def calculate_combined_offensive_potential(self, home_team, away_team):
        """Calculate combined offensive potential for a matchup"""
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        
        if home_stats is None and away_stats is None:
            return None
        
        # Use league average for missing stats
        home_avg = home_stats.get('avg_points_scored', self.LEAGUE_AVG_PPG) if home_stats else self.LEAGUE_AVG_PPG
        away_avg = away_stats.get('avg_points_scored', self.LEAGUE_AVG_PPG) if away_stats else self.LEAGUE_AVG_PPG
        
        # Calculate expected total based on offensive averages
        expected_total = home_avg + away_avg
        
        # Home court advantage (teams typically score ~2 points more at home)
        home_boost = 2.0
        expected_total += home_boost
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_avg_scored': round(home_avg, 1),
            'away_avg_scored': round(away_avg, 1),
            'expected_total': round(expected_total, 1),
            'vs_league_avg': round(expected_total - self.LEAGUE_AVG_TOTAL, 1)
        }
    
    def score_matchup(self, home_team, away_team, minimum_total):
        """
        Score a matchup for offensive efficiency factor
        
        Returns score from 0-30 based on how likely the total will go OVER
        """
        combined = self.calculate_combined_offensive_potential(home_team, away_team)
        
        if combined is None:
            return {
                'score': self.MAX_SCORE / 2,  # Neutral score
                'confidence': 'LOW',
                'details': 'Missing team stats',
                'expected_total': None
            }
        
        expected = combined['expected_total']
        
        # Calculate buffer (how far expected is above minimum)
        buffer = expected - minimum_total
        
        # Score based on buffer size
        # Buffer > 20 points: Full score (30)
        # Buffer 10-20: 25-30
        # Buffer 5-10: 20-25
        # Buffer 0-5: 15-20
        # Buffer < 0: 0-15 (risky)
        
        if buffer >= 20:
            score = self.MAX_SCORE
        elif buffer >= 10:
            score = 25 + (buffer - 10) * 0.5
        elif buffer >= 5:
            score = 20 + (buffer - 5)
        elif buffer >= 0:
            score = 15 + (buffer) * 1
        else:
            # Negative buffer - expected below minimum
            score = max(0, 15 + buffer)
        
        # Determine confidence
        if score >= 25:
            confidence = 'HIGH'
        elif score >= 18:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        return {
            'score': round(score, 1),
            'max_score': self.MAX_SCORE,
            'confidence': confidence,
            'expected_total': expected,
            'minimum_total': minimum_total,
            'buffer': round(buffer, 1),
            'details': f"Expected {expected} vs minimum {minimum_total} (buffer: {buffer:+.1f})"
        }


def main():
    """Test the offensive efficiency analyzer"""
    from config.season_config import DATA_DIR, TEAM_STATS_FILE
    
    data_dir = Path(__file__).parent.parent / DATA_DIR
    stats_file = data_dir / TEAM_STATS_FILE
    
    analyzer = OffensiveEfficiencyAnalyzer()
    
    if stats_file.exists():
        analyzer.load_team_stats(stats_file)
        
        print("=" * 60)
        print("OFFENSIVE EFFICIENCY ANALYZER TEST")
        print("=" * 60)
        
        # Test with sample teams
        test_teams = ['Duke', 'North Carolina', 'Kentucky', 'Kansas']
        
        for team in test_teams:
            rating = analyzer.calculate_offensive_rating(team)
            if rating:
                print(f"\n{team}:")
                print(f"  Avg Points: {rating['avg_points_scored']:.1f}")
                print(f"  Off Rating: {rating['offensive_rating']:.1f}")
        
        # Test matchup scoring
        print("\n" + "=" * 60)
        print("MATCHUP SCORING TEST")
        print("=" * 60)
        
        result = analyzer.score_matchup('Duke', 'North Carolina', 140.5)
        print(f"\nDuke vs North Carolina (Min: 140.5):")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print(f"Stats file not found: {stats_file}")
        print("Run cbb_stats_collector.py first")


if __name__ == "__main__":
    main()
