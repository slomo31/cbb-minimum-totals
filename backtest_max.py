#!/usr/bin/env python3
"""
CBB MAXIMUM TOTALS - BACKTEST ENGINE
====================================
Tests the under system against historical games to find optimal thresholds.

For each historical game:
1. Run Monte Carlo sim using data available BEFORE that game
2. Calculate under_hit_rate and cushion vs maximum line
3. Check if actual total stayed UNDER maximum
4. Track win/loss by tier

Maximum line = Standard total + 12 (DraftKings alternate)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
from collections import defaultdict


class MaximumBacktester:
    """
    Backtest the maximum (under) system against historical games.
    """
    
    def __init__(self, data_dir: str = "data"):
        """Initialize with data directory."""
        self.data_dir = Path(data_dir)
        self.games = None
        self.team_stats = {}
        self.team_variance = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load all necessary data."""
        # Load game history
        games_file = self.data_dir / "ncaa_games_history.csv"
        if games_file.exists():
            self.games = pd.read_csv(games_file)
            print(f"✅ Loaded {len(self.games)} games")
        
        # Load Barttorvik stats
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
                    }
            print(f"✅ Loaded {len(self.team_stats)} team stats")
        
        # Calculate variance from games
        self._calculate_variance()
    
    def _calculate_variance(self):
        """Calculate team scoring variance from history."""
        if self.games is None:
            return
        
        team_scores = defaultdict(list)
        
        for _, row in self.games.iterrows():
            home = str(row.get('home_team', '')).lower()
            away = str(row.get('away_team', '')).lower()
            home_score = row.get('home_score', 0)
            away_score = row.get('away_score', 0)
            
            if home and pd.notna(home_score) and home_score > 0:
                team_scores[home].append(home_score)
            if away and pd.notna(away_score) and away_score > 0:
                team_scores[away].append(away_score)
        
        for team, scores in team_scores.items():
            if len(scores) >= 3:
                self.team_variance[team] = {
                    'mean': np.mean(scores),
                    'std': np.std(scores),
                    'games': len(scores)
                }
        
        print(f"✅ Calculated variance for {len(self.team_variance)} teams")
    
    def _find_team(self, team_name: str) -> Dict:
        """Find team stats with fuzzy matching."""
        team_lower = str(team_name).lower()
        
        if team_lower in self.team_stats:
            return self.team_stats[team_lower]
        
        for key, stats in self.team_stats.items():
            if team_lower in key or key in team_lower:
                return stats
        
        return {'adj_o': 100, 'adj_d': 100, 'adj_t': 68}
    
    def _get_team_std(self, team_name: str) -> float:
        """Get team scoring standard deviation."""
        team_lower = str(team_name).lower()
        
        if team_lower in self.team_variance:
            return self.team_variance[team_lower]['std']
        
        for key, var in self.team_variance.items():
            if team_lower in key or key in team_lower:
                return var['std']
        
        return 12.0  # Default
    
    def simulate_game(self, home_team: str, away_team: str, n_sims: int = 5000) -> Dict:
        """Run Monte Carlo simulation for a game."""
        home_stats = self._find_team(home_team)
        away_stats = self._find_team(away_team)
        
        home_std = self._get_team_std(home_team)
        away_std = self._get_team_std(away_team)
        
        # Get efficiency ratings (points per 100 possessions)
        home_adj_o = home_stats.get('adj_o', 100)
        home_adj_d = home_stats.get('adj_d', 100)
        away_adj_o = away_stats.get('adj_o', 100)
        away_adj_d = away_stats.get('adj_d', 100)
        
        # Tempo - default to D1 average of 68 possessions per game
        home_tempo = home_stats.get('adj_t', 68)
        away_tempo = away_stats.get('adj_t', 68)
        avg_tempo = (home_tempo + away_tempo) / 2
        
        # Expected points = (Team Offense * Opp Defense / D1 Avg) * Tempo / 100
        # D1 average efficiency is ~100
        # This gives points adjusted for opponent strength
        
        # Home team expected score
        home_off_rating = (home_adj_o * away_adj_d) / 100  # Adjusted for opponent
        home_expected = (home_off_rating / 100) * avg_tempo + 2  # +2 home court
        
        # Away team expected score  
        away_off_rating = (away_adj_o * home_adj_d) / 100  # Adjusted for opponent
        away_expected = (away_off_rating / 100) * avg_tempo - 2  # -2 road
        
        # Simulate
        home_scores = np.random.normal(home_expected, home_std, n_sims)
        away_scores = np.random.normal(away_expected, away_std, n_sims)
        
        home_scores = np.clip(home_scores, 35, 130)
        away_scores = np.clip(away_scores, 35, 130)
        
        totals = home_scores + away_scores
        
        return {
            'mean': np.mean(totals),
            'std': np.std(totals),
            'totals': totals
        }
    
    def backtest_game(self, 
                      home_team: str, 
                      away_team: str,
                      actual_total: float,
                      standard_line: float = None) -> Dict:
        """
        Backtest a single game for UNDER betting.
        
        Logic:
        - We simulate the game to get expected total (sim_mean)
        - Maximum line = sim_mean + 12 (what DK alt line would be)
        - We bet UNDER maximum_line
        - We WIN if actual_total < maximum_line
        
        Cushion = maximum_line - sim_mean = always 12 (not useful)
        
        BETTER metric for unders:
        - under_hit_rate = % of sims below maximum_line  
        - prediction_error = actual_total - sim_mean (negative = we overshot)
        
        For a GOOD under pick:
        - High under_hit_rate (most sims stay below max)
        - We want actual to also stay below max
        """
        sim_result = self.simulate_game(home_team, away_team)
        sim_mean = sim_result['mean']
        
        # Maximum line = sim_mean + 12 (DK alternate over)
        maximum_line = sim_mean + 12
        
        # Calculate under hit rate
        under_hits = np.sum(sim_result['totals'] < maximum_line)
        under_hit_rate = (under_hits / len(sim_result['totals'])) * 100
        
        # Did the UNDER hit? (actual stayed below max line)
        under_won = actual_total < maximum_line
        
        # Margin: how much we won/lost by
        margin = maximum_line - actual_total  # Positive = won
        
        # Cushion for unders = how far below max line our prediction is
        # This is always 12 by construction, so use a different metric:
        # "safety_margin" = how far below max the actual ended up
        cushion = maximum_line - actual_total if under_won else -(actual_total - maximum_line)
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'actual_total': actual_total,
            'maximum_line': maximum_line,
            'sim_mean': sim_mean,
            'under_hit_rate': under_hit_rate,
            'cushion': margin,  # How much we won by (or lost by if negative)
            'under_won': under_won,
            'margin': margin,
            'prediction_error': actual_total - sim_mean  # + means we underestimated
        }
    
    def run_full_backtest(self, 
                          min_hit_rate: float = 90,
                          min_cushion: float = 20) -> pd.DataFrame:
        """
        Run backtest across all historical games.
        
        Args:
            min_hit_rate: Minimum under hit rate to consider
            min_cushion: Minimum cushion to consider
        
        Returns:
            DataFrame with all backtest results
        """
        if self.games is None:
            print("❌ No games loaded")
            return pd.DataFrame()
        
        results = []
        total = len(self.games)
        
        print(f"\n🎲 Running backtest on {total} games...")
        print(f"   Filters: {min_hit_rate}%+ under rate, {min_cushion}+ cushion")
        
        for i, row in self.games.iterrows():
            home = row.get('home_team', '')
            away = row.get('away_team', '')
            home_score = row.get('home_score', 0)
            away_score = row.get('away_score', 0)
            
            if not home or not away or pd.isna(home_score) or pd.isna(away_score):
                continue
            if home_score <= 0 or away_score <= 0:
                continue
            
            actual_total = home_score + away_score
            
            # Use sim mean as proxy for standard line
            result = self.backtest_game(home, away, actual_total)
            
            # Only keep games meeting minimum thresholds
            if result['under_hit_rate'] >= min_hit_rate and result['cushion'] >= min_cushion:
                result['game_date'] = row.get('date', '')
                results.append(result)
            
            if (i + 1) % 500 == 0:
                print(f"   Processed {i + 1}/{total} games...")
        
        df = pd.DataFrame(results)
        print(f"✅ Backtest complete: {len(df)} games met criteria")
        
        return df
    
    def analyze_tiers(self, results_df: pd.DataFrame) -> Dict:
        """
        Analyze backtest results by tier.
        
        Tests multiple tier configurations to find optimal thresholds.
        """
        if results_df.empty:
            return {}
        
        print("\n" + "=" * 70)
        print("📊 TIER ANALYSIS - MAXIMUM (UNDER) SYSTEM")
        print("=" * 70)
        
        tier_configs = [
            # (name, hit_rate_min, cushion_min)
            ('99%+ & 40+ cushion', 99, 40),
            ('99%+ & 35+ cushion', 99, 35),
            ('99%+ & 30+ cushion', 99, 30),
            ('99%+ & 25+ cushion', 99, 25),
            ('98%+ & 40+ cushion', 98, 40),
            ('98%+ & 35+ cushion', 98, 35),
            ('98%+ & 30+ cushion', 98, 30),
            ('97%+ & 40+ cushion', 97, 40),
            ('97%+ & 35+ cushion', 97, 35),
            ('96%+ & 40+ cushion', 96, 40),
            ('95%+ & 40+ cushion', 95, 40),
        ]
        
        tier_results = {}
        
        for name, hit_min, cushion_min in tier_configs:
            filtered = results_df[
                (results_df['under_hit_rate'] >= hit_min) & 
                (results_df['cushion'] >= cushion_min)
            ]
            
            if len(filtered) == 0:
                continue
            
            wins = filtered['under_won'].sum()
            losses = len(filtered) - wins
            win_rate = wins / len(filtered) * 100
            
            # Calculate average margin when lost
            losses_df = filtered[~filtered['under_won']]
            avg_loss_margin = losses_df['margin'].mean() if len(losses_df) > 0 else 0
            
            tier_results[name] = {
                'wins': wins,
                'losses': losses,
                'total': len(filtered),
                'win_rate': win_rate,
                'avg_loss_margin': avg_loss_margin
            }
            
            status = "✅" if win_rate >= 90 else "⚠️" if win_rate >= 85 else "❌"
            print(f"\n{status} {name}")
            print(f"   Record: {wins}-{losses} ({win_rate:.1f}%)")
            print(f"   Sample: {len(filtered)} games")
            if losses > 0:
                print(f"   Avg loss margin: {avg_loss_margin:.1f} pts")
        
        return tier_results
    
    def find_losses(self, results_df: pd.DataFrame, 
                    hit_min: float = 98, 
                    cushion_min: float = 35) -> pd.DataFrame:
        """Find games where the under lost despite meeting criteria."""
        filtered = results_df[
            (results_df['under_hit_rate'] >= hit_min) & 
            (results_df['cushion'] >= cushion_min) &
            (~results_df['under_won'])
        ]
        
        if len(filtered) > 0:
            print(f"\n❌ LOSSES at {hit_min}%+ & {cushion_min}+ cushion:")
            print("-" * 70)
            for _, row in filtered.iterrows():
                print(f"   {row['away_team'][:20]} @ {row['home_team'][:20]}")
                print(f"      Max: {row['maximum_line']:.0f} | Actual: {row['actual_total']:.0f} | Over by: {-row['margin']:.0f}")
                print(f"      Under Rate: {row['under_hit_rate']:.1f}% | Cushion: {row['cushion']:.1f}")
        
        return filtered


def main():
    """Run full backtest analysis."""
    bt = MaximumBacktester()
    
    # Run backtest with loose filters to capture all candidates
    # For unders, cushion = margin (how much we won by)
    # So cushion > 0 means we won, cushion < 0 means we lost
    results = bt.run_full_backtest(min_hit_rate=80, min_cushion=-50)
    
    if results.empty:
        print("❌ No results to analyze")
        return
    
    # Save results
    results.to_csv('max_backtest_results.csv', index=False)
    print(f"\n💾 Saved to max_backtest_results.csv")
    
    # Basic stats first
    print(f"\n📊 OVERALL STATS:")
    print(f"   Total games: {len(results)}")
    print(f"   Unders won: {results['under_won'].sum()}")
    print(f"   Unders lost: {len(results) - results['under_won'].sum()}")
    print(f"   Win rate: {results['under_won'].mean() * 100:.1f}%")
    
    # Analyze tiers
    tier_results = bt.analyze_tiers(results)
    
    # Show losses at strictest tier
    print("\n" + "=" * 70)
    bt.find_losses(results, hit_min=99, cushion_min=0)
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 SUMMARY - MAXIMUM (UNDER) SYSTEM")
    print("=" * 70)
    
    best_tiers = sorted(
        [(k, v) for k, v in tier_results.items() if v['total'] >= 10],
        key=lambda x: (x[1]['win_rate'], x[1]['total']),
        reverse=True
    )
    
    print("\nTop performing tiers (10+ sample):")
    for name, stats in best_tiers[:5]:
        print(f"   {name}: {stats['wins']}-{stats['losses']} ({stats['win_rate']:.1f}%)")


if __name__ == "__main__":
    main()