"""
Pace Analyzer
Analyzes game pace/tempo for totals prediction
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CONFIDENCE_WEIGHTS


class PaceAnalyzer:
    """Analyze pace/tempo factors for totals prediction"""
    
    # CBB average possessions per game (approximate)
    LEAGUE_AVG_POSSESSIONS = 67.0
    LEAGUE_AVG_TOTAL = 144.0
    
    # High pace threshold (possessions per game)
    HIGH_PACE_THRESHOLD = 70.0
    LOW_PACE_THRESHOLD = 64.0
    
    # Weight for this factor
    MAX_SCORE = CONFIDENCE_WEIGHTS['pace_tempo']  # 25 points
    
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
        
        mask = self.team_stats['team'].str.lower().str.contains(team_name.lower())
        matches = self.team_stats[mask]
        
        if not matches.empty:
            return matches.iloc[0].to_dict()
        return None
    
    def estimate_pace(self, team_name):
        """
        Estimate team's pace based on scoring data
        
        Since we don't have direct possession data, we estimate pace
        from total points scored/allowed
        """
        stats = self.get_team_stats(team_name)
        
        if stats is None:
            return None
        
        # Get scoring averages
        avg_scored = stats.get('avg_points_scored', 0)
        avg_allowed = stats.get('avg_points_allowed', 0)
        avg_total = stats.get('avg_total_points', 0)
        
        if avg_total == 0:
            avg_total = avg_scored + avg_allowed
        
        # Estimate pace factor based on total points
        # Higher totals = faster pace
        pace_factor = (avg_total / self.LEAGUE_AVG_TOTAL) * self.LEAGUE_AVG_POSSESSIONS
        
        # Classify pace
        if pace_factor >= self.HIGH_PACE_THRESHOLD:
            pace_category = 'FAST'
        elif pace_factor <= self.LOW_PACE_THRESHOLD:
            pace_category = 'SLOW'
        else:
            pace_category = 'AVERAGE'
        
        return {
            'team': team_name,
            'estimated_pace': round(pace_factor, 1),
            'avg_total': round(avg_total, 1),
            'pace_category': pace_category,
            'vs_league_avg': round(pace_factor - self.LEAGUE_AVG_POSSESSIONS, 1)
        }
    
    def calculate_matchup_pace(self, home_team, away_team):
        """Calculate expected pace for a matchup"""
        home_pace = self.estimate_pace(home_team)
        away_pace = self.estimate_pace(away_team)
        
        if home_pace is None and away_pace is None:
            return None
        
        # Use league average for missing data
        home_est = home_pace['estimated_pace'] if home_pace else self.LEAGUE_AVG_POSSESSIONS
        away_est = away_pace['estimated_pace'] if away_pace else self.LEAGUE_AVG_POSSESSIONS
        
        # Combined pace is average (both teams control tempo)
        combined_pace = (home_est + away_est) / 2
        
        # Determine matchup pace category
        if combined_pace >= self.HIGH_PACE_THRESHOLD:
            matchup_type = 'UPTEMPO'
        elif combined_pace <= self.LOW_PACE_THRESHOLD:
            matchup_type = 'SLOWDOWN'
        else:
            matchup_type = 'NEUTRAL'
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_pace': home_est,
            'away_pace': away_est,
            'combined_pace': round(combined_pace, 1),
            'matchup_type': matchup_type,
            'pace_vs_avg': round(combined_pace - self.LEAGUE_AVG_POSSESSIONS, 1)
        }
    
    def calculate_pace_adjusted_total(self, home_team, away_team):
        """Calculate pace-adjusted expected total"""
        matchup = self.calculate_matchup_pace(home_team, away_team)
        
        if matchup is None:
            return self.LEAGUE_AVG_TOTAL
        
        # Adjust expected total based on pace
        # Formula: League Average * (Combined Pace / League Pace)
        pace_factor = matchup['combined_pace'] / self.LEAGUE_AVG_POSSESSIONS
        adjusted_total = self.LEAGUE_AVG_TOTAL * pace_factor
        
        return round(adjusted_total, 1)
    
    def score_matchup(self, home_team, away_team, minimum_total):
        """
        Score a matchup for pace factor
        
        Returns score from 0-25 based on pace impact on going OVER
        """
        matchup = self.calculate_matchup_pace(home_team, away_team)
        
        if matchup is None:
            return {
                'score': self.MAX_SCORE / 2,  # Neutral
                'confidence': 'LOW',
                'details': 'Missing pace data',
                'pace_adjusted_total': None
            }
        
        combined_pace = matchup['combined_pace']
        matchup_type = matchup['matchup_type']
        
        # Calculate pace-adjusted expected total
        pace_adjusted = self.calculate_pace_adjusted_total(home_team, away_team)
        
        # Buffer from minimum
        buffer = pace_adjusted - minimum_total
        
        # Score based on pace and buffer
        # UPTEMPO games: Higher base score
        # SLOWDOWN games: Lower base score
        
        if matchup_type == 'UPTEMPO':
            base_score = 18  # Start higher
        elif matchup_type == 'SLOWDOWN':
            base_score = 10  # Start lower
        else:
            base_score = 14  # Neutral start
        
        # Adjust based on buffer
        if buffer >= 15:
            score = min(self.MAX_SCORE, base_score + 7)
        elif buffer >= 10:
            score = min(self.MAX_SCORE, base_score + 5)
        elif buffer >= 5:
            score = min(self.MAX_SCORE, base_score + 3)
        elif buffer >= 0:
            score = base_score
        else:
            # Negative buffer
            score = max(0, base_score + buffer)
        
        # Confidence
        if score >= 20:
            confidence = 'HIGH'
        elif score >= 14:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        return {
            'score': round(score, 1),
            'max_score': self.MAX_SCORE,
            'confidence': confidence,
            'pace_adjusted_total': pace_adjusted,
            'matchup_type': matchup_type,
            'combined_pace': combined_pace,
            'buffer': round(buffer, 1),
            'details': f"{matchup_type} matchup (pace: {combined_pace:.1f}), adjusted total: {pace_adjusted}"
        }


def main():
    """Test the pace analyzer"""
    from config.season_config import DATA_DIR, TEAM_STATS_FILE
    
    data_dir = Path(__file__).parent.parent / DATA_DIR
    stats_file = data_dir / TEAM_STATS_FILE
    
    analyzer = PaceAnalyzer()
    
    if stats_file.exists():
        analyzer.load_team_stats(stats_file)
        
        print("=" * 60)
        print("PACE ANALYZER TEST")
        print("=" * 60)
        
        # Test individual team pace
        test_teams = ['Gonzaga', 'Virginia', 'Duke', 'Kentucky']
        
        for team in test_teams:
            pace = analyzer.estimate_pace(team)
            if pace:
                print(f"\n{team}:")
                print(f"  Estimated Pace: {pace['estimated_pace']}")
                print(f"  Category: {pace['pace_category']}")
        
        # Test matchup
        print("\n" + "=" * 60)
        print("MATCHUP PACE ANALYSIS")
        print("=" * 60)
        
        matchup = analyzer.calculate_matchup_pace('Gonzaga', 'Virginia')
        if matchup:
            print(f"\nGonzaga vs Virginia:")
            for key, value in matchup.items():
                print(f"  {key}: {value}")
        
        # Test scoring
        result = analyzer.score_matchup('Gonzaga', 'Virginia', 130.5)
        print(f"\nPace Score (min: 130.5):")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print(f"Stats file not found: {stats_file}")
        print("Run cbb_stats_collector.py first")


if __name__ == "__main__":
    main()
