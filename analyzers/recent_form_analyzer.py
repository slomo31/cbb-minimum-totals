"""
Recent Form Analyzer
Analyzes recent scoring trends and streaks
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CONFIDENCE_WEIGHTS


class RecentFormAnalyzer:
    """Analyze recent form/trends for totals prediction"""
    
    # Weight for this factor
    MAX_SCORE = CONFIDENCE_WEIGHTS['recent_form']  # 20 points
    
    # Thresholds
    HOT_STREAK_THRESHOLD = 1.10  # 10% above season average
    COLD_STREAK_THRESHOLD = 0.90  # 10% below season average
    
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
    
    def analyze_team_form(self, team_name):
        """Analyze a team's recent form"""
        stats = self.get_team_stats(team_name)
        
        if stats is None:
            return None
        
        # Get season and recent averages
        season_avg_total = stats.get('avg_total_points', 0)
        last_5_avg = stats.get('last_5_avg_total', season_avg_total)
        last_5_scored = stats.get('last_5_avg_scored', stats.get('avg_points_scored', 0))
        last_5_allowed = stats.get('last_5_avg_allowed', stats.get('avg_points_allowed', 0))
        
        if season_avg_total == 0:
            return None
        
        # Calculate form trend
        form_ratio = last_5_avg / season_avg_total
        form_change = last_5_avg - season_avg_total
        
        # Determine trend
        if form_ratio >= self.HOT_STREAK_THRESHOLD:
            trend = 'HOT'
            trend_impact = 'POSITIVE'
        elif form_ratio <= self.COLD_STREAK_THRESHOLD:
            trend = 'COLD'
            trend_impact = 'NEGATIVE'
        else:
            trend = 'NEUTRAL'
            trend_impact = 'NEUTRAL'
        
        return {
            'team': team_name,
            'season_avg_total': round(season_avg_total, 1),
            'last_5_avg_total': round(last_5_avg, 1),
            'last_5_avg_scored': round(last_5_scored, 1),
            'last_5_avg_allowed': round(last_5_allowed, 1),
            'form_ratio': round(form_ratio, 3),
            'form_change': round(form_change, 1),
            'trend': trend,
            'trend_impact': trend_impact
        }
    
    def analyze_matchup_form(self, home_team, away_team):
        """Analyze combined recent form for a matchup"""
        home_form = self.analyze_team_form(home_team)
        away_form = self.analyze_team_form(away_team)
        
        if home_form is None and away_form is None:
            return None
        
        # Use neutral values for missing data
        home_ratio = home_form['form_ratio'] if home_form else 1.0
        away_ratio = away_form['form_ratio'] if away_form else 1.0
        home_change = home_form['form_change'] if home_form else 0.0
        away_change = away_form['form_change'] if away_form else 0.0
        
        # Combined form impact
        combined_ratio = (home_ratio + away_ratio) / 2
        combined_change = home_change + away_change
        
        # Determine combined trend
        hot_count = 0
        cold_count = 0
        
        if home_form and home_form['trend'] == 'HOT':
            hot_count += 1
        if home_form and home_form['trend'] == 'COLD':
            cold_count += 1
        if away_form and away_form['trend'] == 'HOT':
            hot_count += 1
        if away_form and away_form['trend'] == 'COLD':
            cold_count += 1
        
        if hot_count >= 2:
            combined_trend = 'BOTH_HOT'
            impact = 'VERY_POSITIVE'
        elif hot_count == 1 and cold_count == 0:
            combined_trend = 'ONE_HOT'
            impact = 'POSITIVE'
        elif cold_count >= 2:
            combined_trend = 'BOTH_COLD'
            impact = 'VERY_NEGATIVE'
        elif cold_count == 1 and hot_count == 0:
            combined_trend = 'ONE_COLD'
            impact = 'NEGATIVE'
        elif hot_count == 1 and cold_count == 1:
            combined_trend = 'MIXED'
            impact = 'NEUTRAL'
        else:
            combined_trend = 'NEUTRAL'
            impact = 'NEUTRAL'
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_form': home_form,
            'away_form': away_form,
            'combined_ratio': round(combined_ratio, 3),
            'combined_change': round(combined_change, 1),
            'combined_trend': combined_trend,
            'impact_on_total': impact
        }
    
    def calculate_form_adjusted_total(self, home_team, away_team, base_total):
        """Calculate form-adjusted expected total"""
        matchup = self.analyze_matchup_form(home_team, away_team)
        
        if matchup is None:
            return base_total
        
        # Adjust based on form
        form_adjustment = matchup['combined_change']
        adjusted = base_total + form_adjustment
        
        return round(adjusted, 1)
    
    def score_matchup(self, home_team, away_team, minimum_total):
        """
        Score a matchup for recent form factor
        
        Returns score from 0-20 based on form impact
        """
        matchup = self.analyze_matchup_form(home_team, away_team)
        
        if matchup is None:
            return {
                'score': self.MAX_SCORE / 2,  # Neutral
                'confidence': 'LOW',
                'details': 'Missing form data',
                'form_adjusted_total': None
            }
        
        impact = matchup['impact_on_total']
        combined_ratio = matchup['combined_ratio']
        
        # Calculate base expected total
        home_season = matchup['home_form']['season_avg_total'] if matchup['home_form'] else 144
        away_season = matchup['away_form']['season_avg_total'] if matchup['away_form'] else 144
        base_total = (home_season + away_season) / 2
        
        # Form-adjusted total
        form_adjusted = self.calculate_form_adjusted_total(home_team, away_team, base_total)
        buffer = form_adjusted - minimum_total
        
        # Score based on impact and buffer
        if impact == 'VERY_POSITIVE':
            base_score = 16
        elif impact == 'POSITIVE':
            base_score = 14
        elif impact == 'NEUTRAL' or impact == 'MIXED':
            base_score = 10
        elif impact == 'NEGATIVE':
            base_score = 7
        else:  # VERY_NEGATIVE
            base_score = 4
        
        # Adjust based on buffer
        if buffer >= 15:
            score = min(self.MAX_SCORE, base_score + 4)
        elif buffer >= 10:
            score = min(self.MAX_SCORE, base_score + 3)
        elif buffer >= 5:
            score = min(self.MAX_SCORE, base_score + 2)
        elif buffer >= 0:
            score = base_score
        else:
            score = max(0, base_score + buffer / 2)
        
        # Confidence
        if score >= 16:
            confidence = 'HIGH'
        elif score >= 10:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        return {
            'score': round(score, 1),
            'max_score': self.MAX_SCORE,
            'confidence': confidence,
            'form_adjusted_total': form_adjusted,
            'combined_trend': matchup['combined_trend'],
            'impact': impact,
            'buffer': round(buffer, 1),
            'details': f"{matchup['combined_trend']} form ({impact}), adjusted total: {form_adjusted}"
        }


def main():
    """Test the recent form analyzer"""
    from config.season_config import DATA_DIR, TEAM_STATS_FILE
    
    data_dir = Path(__file__).parent.parent / DATA_DIR
    stats_file = data_dir / TEAM_STATS_FILE
    
    analyzer = RecentFormAnalyzer()
    
    if stats_file.exists():
        analyzer.load_team_stats(stats_file)
        
        print("=" * 60)
        print("RECENT FORM ANALYZER TEST")
        print("=" * 60)
        
        # Test individual team form
        test_teams = ['Duke', 'Kansas', 'UCLA', 'Houston']
        
        for team in test_teams:
            form = analyzer.analyze_team_form(team)
            if form:
                print(f"\n{team}:")
                print(f"  Season Avg Total: {form['season_avg_total']}")
                print(f"  Last 5 Avg Total: {form['last_5_avg_total']}")
                print(f"  Form Trend: {form['trend']} ({form['form_change']:+.1f})")
        
        # Test matchup
        print("\n" + "=" * 60)
        print("MATCHUP FORM ANALYSIS")
        print("=" * 60)
        
        result = analyzer.score_matchup('Duke', 'Kansas', 145.5)
        print(f"\nDuke vs Kansas (min: 145.5):")
        for key, value in result.items():
            if key not in ['form_adjusted_total']:
                print(f"  {key}: {value}")
    else:
        print(f"Stats file not found: {stats_file}")
        print("Run cbb_stats_collector.py first")


if __name__ == "__main__":
    main()
