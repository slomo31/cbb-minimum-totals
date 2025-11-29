#!/usr/bin/env python3
"""
CBB MAXIMUM TOTALS - MONTE CARLO SIMULATOR
==========================================
Simulates games to find probability of staying UNDER maximum lines.

Maximum line = Standard total + 12 (typical DraftKings alternate)

For unders:
- hit_rate = % of simulations where total < maximum_line
- cushion = maximum_line - sim_mean (how far below we expect to be)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
import json


class MonteCarloMaxSimulator:
    """
    Monte Carlo simulator for maximum total (under) betting.
    Uses same team data as minimum system but calculates under probabilities.
    """
    
    def __init__(self, data_dir: str = "data"):
        """Initialize simulator with team data."""
        self.data_dir = Path(data_dir)
        self.team_stats = {}
        self.game_history = None
        self.team_variance = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load Barttorvik data and game history."""
        # Load Barttorvik team stats
        bart_file = self.data_dir / "barttorvik_stats.csv"
        if bart_file.exists():
            df = pd.read_csv(bart_file)
            for _, row in df.iterrows():
                team_name = row.get('team', row.get('Team', ''))
                if team_name:
                    self.team_stats[team_name.lower()] = {
                        'adj_o': row.get('adj_o', row.get('AdjO', 100)),
                        'adj_d': row.get('adj_d', row.get('AdjD', 100)),
                        'adj_t': row.get('adj_t', row.get('AdjT', 68)),
                        'name': team_name
                    }
            print(f"✅ Loaded Barttorvik data: {len(self.team_stats)} teams")
        
        # Load game history for variance calculation
        games_file = self.data_dir / "ncaa_games_2024_25.csv"
        if games_file.exists():
            self.game_history = pd.read_csv(games_file)
            self._calculate_team_variance()
            print(f"✅ Loaded game history: {len(self.game_history)} games")
    
    def _calculate_team_variance(self):
        """Calculate scoring variance for each team from game history."""
        if self.game_history is None:
            return
        
        # Get all team scores
        team_scores = {}
        
        for _, row in self.game_history.iterrows():
            home = row.get('home_team', '').lower()
            away = row.get('away_team', '').lower()
            home_score = row.get('home_score', 0)
            away_score = row.get('away_score', 0)
            
            if home and home_score > 0:
                if home not in team_scores:
                    team_scores[home] = []
                team_scores[home].append(home_score)
            
            if away and away_score > 0:
                if away not in team_scores:
                    team_scores[away] = []
                team_scores[away].append(away_score)
        
        # Calculate variance for each team
        for team, scores in team_scores.items():
            if len(scores) >= 3:
                self.team_variance[team] = {
                    'mean': np.mean(scores),
                    'std': np.std(scores),
                    'min': min(scores),
                    'max': max(scores),
                    'games': len(scores)
                }
        
        print(f"   Calculated variance for {len(self.team_variance)} teams")
    
    def _find_team(self, team_name: str) -> Optional[Dict]:
        """Find team stats with fuzzy matching."""
        team_lower = team_name.lower()
        
        # Direct match
        if team_lower in self.team_stats:
            return self.team_stats[team_lower]
        
        # Partial match
        for key, stats in self.team_stats.items():
            if team_lower in key or key in team_lower:
                return stats
            # Check common variations
            clean_name = team_lower.replace('state', 'st').replace('saint', 'st')
            clean_key = key.replace('state', 'st').replace('saint', 'st')
            if clean_name in clean_key or clean_key in clean_name:
                return stats
        
        return None
    
    def _get_team_std(self, team_name: str, default: float = 12.0) -> float:
        """Get team's scoring standard deviation."""
        team_lower = team_name.lower()
        
        # Check direct match
        if team_lower in self.team_variance:
            return self.team_variance[team_lower]['std']
        
        # Partial match
        for key, var in self.team_variance.items():
            if team_lower in key or key in team_lower:
                return var['std']
        
        return default
    
    def simulate_game(self, 
                      home_team: str, 
                      away_team: str,
                      n_simulations: int = 10000) -> Dict:
        """
        Run Monte Carlo simulation for a game.
        
        Returns distribution of total scores.
        """
        home_stats = self._find_team(home_team)
        away_stats = self._find_team(away_team)
        
        # Default stats if team not found
        if home_stats is None:
            home_stats = {'adj_o': 100, 'adj_d': 100, 'adj_t': 68, 'name': home_team}
        if away_stats is None:
            away_stats = {'adj_o': 100, 'adj_d': 100, 'adj_t': 68, 'name': away_team}
        
        # Get team variances
        home_std = self._get_team_std(home_team)
        away_std = self._get_team_std(away_team)
        
        # Get efficiency ratings
        home_adj_o = home_stats.get('adj_o', 100)
        home_adj_d = home_stats.get('adj_d', 100)
        away_adj_o = away_stats.get('adj_o', 100)
        away_adj_d = away_stats.get('adj_d', 100)
        
        # Tempo - default to D1 average
        home_tempo = home_stats.get('adj_t', 68)
        away_tempo = away_stats.get('adj_t', 68)
        avg_tempo = (home_tempo + away_tempo) / 2
        
        # Expected points using proper efficiency formula
        # Points = (Team Off * Opp Def / 100) / 100 * Tempo + home court
        home_off_rating = (home_adj_o * away_adj_d) / 100
        home_expected = (home_off_rating / 100) * avg_tempo + 2  # +2 home court
        
        away_off_rating = (away_adj_o * home_adj_d) / 100
        away_expected = (away_off_rating / 100) * avg_tempo - 2  # -2 road
        
        # Run simulations
        np.random.seed(None)  # Random seed for variety
        
        home_scores = np.random.normal(home_expected, home_std, n_simulations)
        away_scores = np.random.normal(away_expected, away_std, n_simulations)
        
        # Floor at reasonable minimums, cap at maximums
        home_scores = np.clip(home_scores, 35, 130)
        away_scores = np.clip(away_scores, 35, 130)
        
        total_scores = home_scores + away_scores
        
        return {
            'totals': total_scores,
            'mean': np.mean(total_scores),
            'std': np.std(total_scores),
            'min': np.min(total_scores),
            'max': np.max(total_scores),
            'home_expected': home_expected,
            'away_expected': away_expected,
            'data_quality': 'high' if home_stats and away_stats else 'low'
        }
    
    def evaluate_under(self,
                       home_team: str,
                       away_team: str,
                       maximum_total: float,
                       standard_total: float = None,
                       n_simulations: int = 10000) -> Dict:
        """
        Evaluate probability of staying UNDER maximum line.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            maximum_total: Maximum line (standard + 12 typically)
            standard_total: Standard total line
            n_simulations: Number of simulations
        
        Returns:
            Dict with under_hit_rate, sim_mean, cushion, etc.
        """
        sim_result = self.simulate_game(home_team, away_team, n_simulations)
        
        # Calculate under hit rate
        under_hits = np.sum(sim_result['totals'] < maximum_total)
        under_hit_rate = (under_hits / n_simulations) * 100
        
        # Cushion = how far below max line we expect
        cushion = maximum_total - sim_result['mean']
        
        return {
            'under_hit_rate': under_hit_rate,
            'sim_mean': sim_result['mean'],
            'sim_std': sim_result['std'],
            'sim_min': sim_result['min'],
            'sim_max': sim_result['max'],
            'cushion': cushion,
            'maximum_total': maximum_total,
            'standard_total': standard_total,
            'data_quality': sim_result['data_quality'],
            'sim_range': f"{int(sim_result['min'])}-{int(sim_result['max'])}"
        }


# Quick test
if __name__ == "__main__":
    sim = MonteCarloMaxSimulator()
    
    # Test with a low-scoring matchup
    result = sim.evaluate_under(
        home_team="Virginia Cavaliers",
        away_team="Wisconsin Badgers",
        maximum_total=140,  # Standard 128 + 12
        standard_total=128,
        n_simulations=10000
    )
    
    print(f"\nVirginia vs Wisconsin (low scorers):")
    print(f"  Under Hit Rate: {result['under_hit_rate']:.1f}%")
    print(f"  Sim Mean: {result['sim_mean']:.1f}")
    print(f"  Cushion: {result['cushion']:.1f}")
    print(f"  Range: {result['sim_range']}")
    
    # Test with a high-scoring matchup
    result = sim.evaluate_under(
        home_team="Duke Blue Devils",
        away_team="Kansas Jayhawks",
        maximum_total=185,  # Standard 173 + 12
        standard_total=173,
        n_simulations=10000
    )
    
    print(f"\nDuke vs Kansas (high scorers):")
    print(f"  Under Hit Rate: {result['under_hit_rate']:.1f}%")
    print(f"  Sim Mean: {result['sim_mean']:.1f}")
    print(f"  Cushion: {result['cushion']:.1f}")
    print(f"  Range: {result['sim_range']}")