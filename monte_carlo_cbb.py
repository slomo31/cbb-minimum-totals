"""
CBB MINIMUM TOTALS - MONTE CARLO SIMULATION ENGINE
===================================================
Simulates games thousands of times to get true probability of hitting minimum.

Logic:
1. Load team stats (avg PPG, std deviation) from NCAA game history
2. For each matchup, simulate 5,000+ games
3. Each simulation: random draw from normal distribution for each team
4. Count how many simulations hit the minimum
5. Decision based on hit rate, not static math

This replaces the broken subtractive risk scoring approach.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import json
from datetime import datetime


class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for CBB minimum totals.
    
    Runs thousands of game simulations using team scoring distributions
    to calculate the TRUE probability of hitting the minimum.
    """
    
    def __init__(self, games_csv_path: str = None):
        """
        Initialize simulator with historical game data.
        
        Args:
            games_csv_path: Path to ncaa_games_history.csv
        """
        self.team_stats = {}
        self.name_cache = {}
        
        # Default path
        if games_csv_path is None:
            games_csv_path = Path(__file__).parent / 'data' / 'ncaa_games_history.csv'
        
        self.games_csv_path = Path(games_csv_path)
        
        if self.games_csv_path.exists():
            self._load_and_calculate_stats()
        else:
            print(f"⚠️ Game history not found at {self.games_csv_path}")
            print("   Run: python data_collection/ncaa_stats_fetcher.py first")
    
    def _load_and_calculate_stats(self):
        """Load game data and calculate team scoring distributions."""
        print(f"Loading game data from {self.games_csv_path}...")
        df = pd.read_csv(self.games_csv_path)
        print(f"   Loaded {len(df)} games")
        
        # Get all unique teams
        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
        
        print("Calculating team scoring distributions...")
        
        for team in all_teams:
            # Get all scores for this team
            home_scores = df[df['home_team'] == team]['home_score'].tolist()
            away_scores = df[df['away_team'] == team]['away_score'].tolist()
            all_scores = home_scores + away_scores
            
            # Get all game totals this team has been in
            home_totals = df[df['home_team'] == team]['total_points'].tolist()
            away_totals = df[df['away_team'] == team]['total_points'].tolist()
            all_totals = home_totals + away_totals
            
            if len(all_scores) >= 1:
                self.team_stats[team] = {
                    'games': len(all_scores),
                    'ppg_mean': np.mean(all_scores),
                    'ppg_std': np.std(all_scores) if len(all_scores) > 1 else 8.0,  # Default std if only 1 game
                    'ppg_min': min(all_scores),
                    'ppg_max': max(all_scores),
                    'total_mean': np.mean(all_totals),
                    'total_std': np.std(all_totals) if len(all_totals) > 1 else 12.0,
                    'total_min': min(all_totals),
                    'total_max': max(all_totals),
                }
        
        print(f"   Calculated stats for {len(self.team_stats)} teams")
    
    def _match_team(self, name: str) -> Optional[str]:
        """Fuzzy match team name to our database."""
        if name in self.name_cache:
            return self.name_cache[name]
        
        # Direct match
        if name in self.team_stats:
            self.name_cache[name] = name
            return name
        
        # Case-insensitive
        name_lower = name.lower()
        for db_team in self.team_stats:
            if db_team.lower() == name_lower:
                self.name_cache[name] = db_team
                return db_team
        
        # Fuzzy match
        best_match = None
        best_score = 0.0
        
        for db_team in self.team_stats:
            score = SequenceMatcher(None, name_lower, db_team.lower()).ratio()
            
            # Boost if key words match
            name_words = set(name_lower.split())
            db_words = set(db_team.lower().split())
            if name_words & db_words:
                score = max(score, 0.65 + 0.1 * len(name_words & db_words))
            
            if score > best_score:
                best_score = score
                best_match = db_team
        
        if best_score >= 0.55:
            self.name_cache[name] = best_match
            return best_match
        
        self.name_cache[name] = None
        return None
    
    def simulate_game(self, home_team: str, away_team: str, 
                      n_simulations: int = 5000,
                      include_bad_night: bool = True) -> Dict:
        """
        Run Monte Carlo simulation for a single game.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            n_simulations: Number of simulations to run
            include_bad_night: Include "bad night" variance scenarios
            
        Returns:
            Dict with simulation results
        """
        home_match = self._match_team(home_team)
        away_match = self._match_team(away_team)
        
        result = {
            'home_team': home_team,
            'away_team': away_team,
            'home_matched': home_match,
            'away_matched': away_match,
            'simulations': n_simulations,
            'sim_totals': [],
            'mean_total': None,
            'std_total': None,
            'min_total': None,
            'max_total': None,
            'percentiles': {},
            'data_quality': 'unknown'
        }
        
        # Get team stats
        home_stats = self.team_stats.get(home_match) if home_match else None
        away_stats = self.team_stats.get(away_match) if away_match else None
        
        # Determine data quality
        home_games = home_stats['games'] if home_stats else 0
        away_games = away_stats['games'] if away_stats else 0
        
        if home_games >= 5 and away_games >= 5:
            result['data_quality'] = 'high'
        elif home_games >= 3 and away_games >= 3:
            result['data_quality'] = 'medium'
        elif home_games >= 1 and away_games >= 1:
            result['data_quality'] = 'low'
        
        # Set up simulation parameters
        if home_stats and away_stats:
            home_mean = home_stats['ppg_mean']
            home_std = max(home_stats['ppg_std'], 5.0)  # Minimum 5 pt std
            away_mean = away_stats['ppg_mean']
            away_std = max(away_stats['ppg_std'], 5.0)
        elif home_stats:
            home_mean = home_stats['ppg_mean']
            home_std = max(home_stats['ppg_std'], 5.0)
            away_mean = 68.0  # D1 average
            away_std = 10.0
            result['data_quality'] = 'partial'
        elif away_stats:
            home_mean = 70.0  # Slight home advantage
            home_std = 10.0
            away_mean = away_stats['ppg_mean']
            away_std = max(away_stats['ppg_std'], 5.0)
            result['data_quality'] = 'partial'
        else:
            # No data - use D1 averages
            home_mean = 70.0
            home_std = 10.0
            away_mean = 68.0
            away_std = 10.0
            result['data_quality'] = 'none'
        
        # Run simulations
        np.random.seed(None)  # Use random seed each time
        
        sim_totals = []
        
        for _ in range(n_simulations):
            # Base scoring from normal distribution
            home_score = np.random.normal(home_mean, home_std)
            away_score = np.random.normal(away_mean, away_std)
            
            # Add "bad night" scenarios (10% chance for each team)
            if include_bad_night:
                if np.random.random() < 0.10:
                    # Home team has bad night - score 15-25% below average
                    home_score = home_mean * np.random.uniform(0.75, 0.85)
                if np.random.random() < 0.10:
                    # Away team has bad night
                    away_score = away_mean * np.random.uniform(0.75, 0.85)
                
                # 5% chance of blowout (one team dominates, other gets garbage time = less total scoring)
                if np.random.random() < 0.05:
                    # Blowout scenario - total tends to be lower due to garbage time
                    total_adjustment = np.random.uniform(-8, -15)
                    home_score += total_adjustment / 2
                    away_score += total_adjustment / 2
            
            # Floor at realistic minimums (no team scores negative or below 35)
            home_score = max(35, home_score)
            away_score = max(35, away_score)
            
            total = home_score + away_score
            sim_totals.append(total)
        
        result['sim_totals'] = sim_totals
        result['mean_total'] = np.mean(sim_totals)
        result['std_total'] = np.std(sim_totals)
        result['min_total'] = np.min(sim_totals)
        result['max_total'] = np.max(sim_totals)
        
        # Calculate percentiles
        result['percentiles'] = {
            '1st': np.percentile(sim_totals, 1),
            '5th': np.percentile(sim_totals, 5),
            '10th': np.percentile(sim_totals, 10),
            '25th': np.percentile(sim_totals, 25),
            '50th': np.percentile(sim_totals, 50),
            '75th': np.percentile(sim_totals, 75),
            '90th': np.percentile(sim_totals, 90),
        }
        
        return result
    
    def evaluate_game(self, home_team: str, away_team: str,
                      minimum_total: float, standard_total: float = None,
                      n_simulations: int = 5000) -> Dict:
        """
        Evaluate if a game will hit its minimum total.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            minimum_total: The alternate minimum line
            standard_total: Optional main line
            n_simulations: Number of simulations
            
        Returns:
            Dict with recommendation, confidence, and analysis
        """
        # Run simulation
        sim = self.simulate_game(home_team, away_team, n_simulations)
        
        # Calculate hit rate
        hits = sum(1 for t in sim['sim_totals'] if t >= minimum_total)
        hit_rate = hits / len(sim['sim_totals']) * 100
        
        # Calculate how often we get within 5-10 points of main line
        main_line_proximity = None
        if standard_total:
            within_10 = sum(1 for t in sim['sim_totals'] if t >= standard_total - 10)
            main_line_proximity = within_10 / len(sim['sim_totals']) * 100
        
        result = {
            'home_team': home_team,
            'away_team': away_team,
            'minimum_total': minimum_total,
            'standard_total': standard_total,
            'decision': 'NO',
            'confidence': hit_rate,
            'hit_rate': hit_rate,
            'main_line_proximity': main_line_proximity,
            'sim_mean': sim['mean_total'],
            'sim_std': sim['std_total'],
            'sim_min': sim['min_total'],
            'sim_max': sim['max_total'],
            'percentile_5th': sim['percentiles']['5th'],
            'percentile_10th': sim['percentiles']['10th'],
            'data_quality': sim['data_quality'],
            'risk_factors': []
        }
        
        # Decision logic based on hit rate
        if hit_rate >= 95:
            result['decision'] = 'YES'
            result['risk_factors'].append(f"✅ {hit_rate:.1f}% of sims hit minimum")
        elif hit_rate >= 88:
            result['decision'] = 'YES'
            result['risk_factors'].append(f"✅ {hit_rate:.1f}% of sims hit minimum")
        elif hit_rate >= 80:
            result['decision'] = 'MAYBE'
            result['risk_factors'].append(f"⚠️ {hit_rate:.1f}% of sims hit minimum (borderline)")
        else:
            result['decision'] = 'NO'
            result['risk_factors'].append(f"🚫 Only {hit_rate:.1f}% of sims hit minimum")
        
        # Add context about simulation range
        result['risk_factors'].append(f"Sim range: {sim['min_total']:.0f} - {sim['max_total']:.0f}")
        result['risk_factors'].append(f"Sim mean: {sim['mean_total']:.1f} (std: {sim['std_total']:.1f})")
        
        # Check 5th percentile vs minimum (worst case)
        if sim['percentiles']['5th'] < minimum_total:
            gap = minimum_total - sim['percentiles']['5th']
            result['risk_factors'].append(f"⚠️ 5th percentile ({sim['percentiles']['5th']:.0f}) is {gap:.0f} below min")
        
        # Main line proximity check (your insight!)
        if main_line_proximity is not None:
            if main_line_proximity < 70:
                result['risk_factors'].append(f"🚫 Only {main_line_proximity:.0f}% get within 10 of main line")
                # Downgrade if we can't get close to main line
                if result['decision'] == 'YES':
                    result['decision'] = 'MAYBE'
            elif main_line_proximity < 85:
                result['risk_factors'].append(f"⚠️ {main_line_proximity:.0f}% get within 10 of main line")
        
        # Adjust for data quality
        if sim['data_quality'] in ['partial', 'none']:
            result['risk_factors'].append(f"⚠️ Limited data ({sim['data_quality']})")
            if result['decision'] == 'YES' and hit_rate < 92:
                result['decision'] = 'MAYBE'
        
        return result
    
    def evaluate_all_games(self, games: List[Dict], n_simulations: int = 5000) -> Tuple[List[Dict], Dict]:
        """
        Evaluate all games in a list.
        
        Args:
            games: List of dicts with home_team, away_team, minimum_total, standard_total
            n_simulations: Simulations per game
            
        Returns:
            Tuple of (results list, summary dict)
        """
        print(f"\nRunning Monte Carlo simulation ({n_simulations:,} sims per game)...")
        
        results = []
        for i, game in enumerate(games):
            result = self.evaluate_game(
                home_team=game.get('home_team', ''),
                away_team=game.get('away_team', ''),
                minimum_total=float(game.get('minimum_total', 0)),
                standard_total=game.get('standard_total'),
                n_simulations=n_simulations
            )
            results.append(result)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"   Processed {i + 1}/{len(games)} games...")
        
        # Summary
        yes_count = sum(1 for r in results if r['decision'] == 'YES')
        maybe_count = sum(1 for r in results if r['decision'] == 'MAYBE')
        no_count = sum(1 for r in results if r['decision'] == 'NO')
        
        summary = {
            'total_games': len(results),
            'yes_count': yes_count,
            'maybe_count': maybe_count,
            'no_count': no_count,
            'avg_hit_rate': np.mean([r['hit_rate'] for r in results]) if results else 0,
            'simulations_per_game': n_simulations,
        }
        
        print(f"   Done! {yes_count} YES, {maybe_count} MAYBE, {no_count} NO")
        
        return results, summary
    
    def print_report(self, results: List[Dict], summary: Dict):
        """Print formatted evaluation report."""
        print("\n" + "=" * 80)
        print("🎲 CBB MINIMUM TOTALS - MONTE CARLO ANALYSIS")
        print(f"   {summary['simulations_per_game']:,} simulations per game")
        print("=" * 80)
        
        # Sort by decision then hit rate
        yes_picks = sorted([r for r in results if r['decision'] == 'YES'],
                           key=lambda x: x['hit_rate'], reverse=True)
        maybe_picks = sorted([r for r in results if r['decision'] == 'MAYBE'],
                             key=lambda x: x['hit_rate'], reverse=True)
        no_picks = sorted([r for r in results if r['decision'] == 'NO'],
                          key=lambda x: x['hit_rate'], reverse=True)
        
        if yes_picks:
            print(f"\n🟢 YES - BET THESE ({len(yes_picks)} games)")
            print("-" * 80)
            for r in yes_picks:
                prox_str = f" | Main±10: {r['main_line_proximity']:.0f}%" if r['main_line_proximity'] else ""
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}")
                print(f"    Min: {r['minimum_total']:<6} | Hit Rate: {r['hit_rate']:.1f}%{prox_str}")
                print(f"    Sim: {r['sim_min']:.0f}-{r['sim_max']:.0f} (avg {r['sim_mean']:.1f})")
        
        if maybe_picks:
            print(f"\n🟡 MAYBE - PROCEED WITH CAUTION ({len(maybe_picks)} games)")
            print("-" * 80)
            for r in maybe_picks:
                prox_str = f" | Main±10: {r['main_line_proximity']:.0f}%" if r['main_line_proximity'] else ""
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}")
                print(f"    Min: {r['minimum_total']:<6} | Hit Rate: {r['hit_rate']:.1f}%{prox_str}")
                print(f"    Sim: {r['sim_min']:.0f}-{r['sim_max']:.0f} (avg {r['sim_mean']:.1f})")
                # Show key risk
                risk = [f for f in r['risk_factors'] if '⚠️' in f or '🚫' in f]
                if risk:
                    print(f"    → {risk[0]}")
        
        if no_picks:
            print(f"\n🔴 NO - SKIP THESE ({len(no_picks)} games)")
            print("-" * 80)
            for r in no_picks[:10]:
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}")
                print(f"    Min: {r['minimum_total']:<6} | Hit Rate: {r['hit_rate']:.1f}%")
                # Show why
                risk = [f for f in r['risk_factors'] if '🚫' in f]
                if risk:
                    print(f"    → {risk[0]}")
            if len(no_picks) > 10:
                print(f"  ... and {len(no_picks) - 10} more skipped")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print(f"   🟢 YES: {summary['yes_count']} picks (88%+ hit rate)")
        print(f"   🟡 MAYBE: {summary['maybe_count']} picks (80-88% hit rate)")
        print(f"   🔴 NO: {summary['no_count']} skipped (<80% hit rate)")
        print(f"   📈 Average Hit Rate: {summary['avg_hit_rate']:.1f}%")
        print("=" * 80)


# Convenience functions for integration with existing system
def evaluate_all_games(games: List[Dict], n_simulations: int = 5000) -> Tuple[List[Dict], Dict]:
    """Main entry point - drop-in replacement for old evaluator."""
    simulator = MonteCarloSimulator()
    return simulator.evaluate_all_games(games, n_simulations)


def print_evaluation_report(results: List[Dict], summary: Dict):
    """Print formatted report."""
    simulator = MonteCarloSimulator.__new__(MonteCarloSimulator)
    simulator.print_report(results, summary)


if __name__ == "__main__":
    # Test mode
    print("Monte Carlo Simulator - Test Mode")
    print("=" * 50)
    
    # Check for data
    default_path = Path(__file__).parent / 'data' / 'ncaa_games_history.csv'
    if not default_path.exists():
        print(f"\n⚠️ No game data found at {default_path}")
        print("Run this from your cbb_minimum_system folder:")
        print("  python data_collection/ncaa_stats_fetcher.py")
    else:
        # Run test
        sim = MonteCarloSimulator(str(default_path))
        
        test_games = [
            {'home_team': 'Duke Blue Devils', 'away_team': 'Kansas Jayhawks', 
             'minimum_total': 130, 'standard_total': 145},
            {'home_team': 'Houston Cougars', 'away_team': 'Alabama Crimson Tide',
             'minimum_total': 125, 'standard_total': 140},
        ]
        
        results, summary = sim.evaluate_all_games(test_games, n_simulations=5000)
        sim.print_report(results, summary)
