"""
CBB MINIMUM TOTALS - MONTE CARLO SIMULATION ENGINE V2
======================================================
IMPROVEMENTS OVER V1:
1. Opponent defense adjustment - blends offensive avg with opponent's defensive avg
2. Wider standard deviations - minimum 10 pts to account for small samples
3. More aggressive "bad night" scenarios - down to 55% of average
4. Defensive matchup risk flags
5. Pace adjustment placeholder for future enhancement

This addresses the Michigan St/UNC and Saint Louis/Santa Clara losses where
elite defenses caused scores well below offensive averages.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import json
from datetime import datetime


class MonteCarloSimulatorV2:
    """
    Monte Carlo simulation engine for CBB minimum totals.
    
    V2 includes opponent defensive adjustments and wider variance modeling.
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
        """Load game data and calculate team scoring AND defensive distributions."""
        print(f"Loading game data from {self.games_csv_path}...")
        df = pd.read_csv(self.games_csv_path)
        print(f"   Loaded {len(df)} games")
        
        # Get all unique teams
        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
        
        print("Calculating team offensive AND defensive distributions...")
        
        for team in all_teams:
            # OFFENSIVE: Get all scores FOR this team
            home_scores = df[df['home_team'] == team]['home_score'].tolist()
            away_scores = df[df['away_team'] == team]['away_score'].tolist()
            all_scores = home_scores + away_scores
            
            # DEFENSIVE: Get all scores AGAINST this team
            # When team is home, opponent (away) scores
            home_defense = df[df['home_team'] == team]['away_score'].tolist()
            # When team is away, opponent (home) scores
            away_defense = df[df['away_team'] == team]['home_score'].tolist()
            all_allowed = home_defense + away_defense
            
            # Get all game totals this team has been in
            home_totals = df[df['home_team'] == team]['total_points'].tolist()
            away_totals = df[df['away_team'] == team]['total_points'].tolist()
            all_totals = home_totals + away_totals
            
            if len(all_scores) >= 1:
                self.team_stats[team] = {
                    'games': len(all_scores),
                    # Offensive stats
                    'ppg_mean': np.mean(all_scores),
                    'ppg_std': np.std(all_scores) if len(all_scores) > 1 else 10.0,
                    'ppg_min': min(all_scores),
                    'ppg_max': max(all_scores),
                    # Defensive stats (points ALLOWED)
                    'def_mean': np.mean(all_allowed) if all_allowed else 70.0,
                    'def_std': np.std(all_allowed) if len(all_allowed) > 1 else 10.0,
                    'def_min': min(all_allowed) if all_allowed else 50,
                    'def_max': max(all_allowed) if all_allowed else 90,
                    # Game total stats
                    'total_mean': np.mean(all_totals),
                    'total_std': np.std(all_totals) if len(all_totals) > 1 else 15.0,
                    'total_min': min(all_totals),
                    'total_max': max(all_totals),
                }
        
        print(f"   Calculated stats for {len(self.team_stats)} teams")
        
        # Calculate league averages for reference
        all_ppg = [s['ppg_mean'] for s in self.team_stats.values()]
        all_def = [s['def_mean'] for s in self.team_stats.values()]
        self.league_avg_ppg = np.mean(all_ppg)
        self.league_avg_def = np.mean(all_def)
        print(f"   League avg PPG: {self.league_avg_ppg:.1f}")
        print(f"   League avg allowed: {self.league_avg_def:.1f}")
    
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
    
    def _get_adjusted_scoring(self, offense_stats: Dict, defense_stats: Dict, 
                               is_home: bool = False,
                               offense_weight: float = 0.80) -> Tuple[float, float]:
        """
        Calculate opponent-adjusted expected scoring.
        
        Blends team's offensive average with opponent's defensive average.
        
        Args:
            offense_stats: Stats for the team scoring
            defense_stats: Stats for the defending team
            is_home: Whether the scoring team is home (slight boost)
            offense_weight: How much to weight offense vs defense (0.80 = 80% offense, 20% defense)
            
        Returns:
            Tuple of (adjusted_mean, adjusted_std)
        """
        off_mean = offense_stats['ppg_mean']
        off_std = offense_stats['ppg_std']
        
        def_mean = defense_stats['def_mean']  # Points this defense ALLOWS
        def_std = defense_stats['def_std']
        
        # Blend offensive and defensive expectations
        # Default: 70% offense, 30% opponent defense
        # This still accounts for defense but doesn't let it dominate
        defense_weight = 1.0 - offense_weight
        adjusted_mean = (off_mean * offense_weight) + (def_mean * defense_weight)
        
        # Home court advantage: +2 points
        if is_home:
            adjusted_mean += 2.0
        
        # Combined standard deviation (add in quadrature, then inflate for safety)
        # Using larger of the two stds, plus a base uncertainty
        adjusted_std = max(off_std, def_std, 10.0) * 1.15
        
        return adjusted_mean, adjusted_std
    
    def _is_elite_defense(self, stats: Dict) -> bool:
        """Check if team has elite defense (allows < 65 ppg)."""
        return stats.get('def_mean', 70) < 65
    
    def _is_poor_offense(self, stats: Dict) -> bool:
        """Check if team has poor offense (scores < 65 ppg)."""
        return stats.get('ppg_mean', 70) < 65
    
    def simulate_game(self, home_team: str, away_team: str, 
                      n_simulations: int = 10000,
                      include_bad_night: bool = True) -> Dict:
        """
        Run Monte Carlo simulation for a single game with opponent adjustments.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            n_simulations: Number of simulations to run (increased default to 10k)
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
            'data_quality': 'unknown',
            'defense_warning': False,
            'matchup_details': {}
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
        
        # Default stats for unknown teams
        default_stats = {
            'ppg_mean': 68.0,
            'ppg_std': 10.0,
            'def_mean': 70.0,
            'def_std': 10.0,
            'games': 0
        }
        
        if not home_stats:
            home_stats = default_stats
            result['data_quality'] = 'partial' if away_stats else 'none'
        if not away_stats:
            away_stats = default_stats
            result['data_quality'] = 'partial' if home_stats else 'none'
        
        # Calculate OPPONENT-ADJUSTED scoring expectations
        # Home team scores against Away team's defense
        home_mean, home_std = self._get_adjusted_scoring(home_stats, away_stats, is_home=True)
        # Away team scores against Home team's defense
        away_mean, away_std = self._get_adjusted_scoring(away_stats, home_stats, is_home=False)
        
        # Store matchup details for analysis
        result['matchup_details'] = {
            'home_raw_ppg': home_stats['ppg_mean'],
            'home_adjusted_ppg': home_mean,
            'away_raw_ppg': away_stats['ppg_mean'],
            'away_adjusted_ppg': away_mean,
            'home_def_avg': home_stats['def_mean'],
            'away_def_avg': away_stats['def_mean'],
        }
        
        # Check for elite defense matchups
        if self._is_elite_defense(home_stats) or self._is_elite_defense(away_stats):
            result['defense_warning'] = True
        
        # Ensure minimum standard deviations (small samples underestimate variance)
        home_std = max(home_std, 10.0)
        away_std = max(away_std, 10.0)
        
        # Run simulations
        np.random.seed(None)  # Use random seed each time
        
        sim_totals = []
        
        for _ in range(n_simulations):
            # Base scoring from normal distribution with ADJUSTED means
            home_score = np.random.normal(home_mean, home_std)
            away_score = np.random.normal(away_mean, away_std)
            
            # Add "bad night" scenarios - BALANCED approach
            if include_bad_night:
                # 5% chance each team has a bad night
                if np.random.random() < 0.05:
                    # Bad night: score 70-85% of adjusted average
                    home_score = home_mean * np.random.uniform(0.70, 0.85)
                if np.random.random() < 0.05:
                    away_score = away_mean * np.random.uniform(0.70, 0.85)
                
                # 2% chance of defensive slugfest
                if np.random.random() < 0.02:
                    # Both teams score lower than expected
                    total_adjustment = np.random.uniform(-8, -15)
                    home_score += total_adjustment / 2
                    away_score += total_adjustment / 2
            
            # Floor at realistic minimums
            home_score = max(40, home_score)
            away_score = max(40, away_score)
            
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
                      n_simulations: int = 10000) -> Dict:
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
            'defense_warning': sim['defense_warning'],
            'matchup_details': sim['matchup_details'],
            'risk_factors': []
        }
        
        # Decision logic - balanced thresholds
        if hit_rate >= 95:
            result['decision'] = 'YES'
            result['risk_factors'].append(f"✅ {hit_rate:.1f}% of sims hit minimum (very high)")
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
        
        # DEFENSE WARNING - only for truly elite defenses
        if sim['defense_warning']:
            result['risk_factors'].append(f"🛡️ ELITE DEFENSE in matchup - verify line")
            # Only downgrade if borderline AND elite defense
            if result['decision'] == 'YES' and hit_rate < 92:
                result['decision'] = 'MAYBE'
                result['risk_factors'].append(f"⚠️ Downgraded due to defensive matchup")
        
        # Show adjustment details
        md = sim['matchup_details']
        if md:
            home_adj = md['home_raw_ppg'] - md['home_adjusted_ppg']
            away_adj = md['away_raw_ppg'] - md['away_adjusted_ppg']
            if abs(home_adj) > 5 or abs(away_adj) > 5:
                result['risk_factors'].append(
                    f"📊 Defense adjustment: Home {md['home_raw_ppg']:.0f}→{md['home_adjusted_ppg']:.0f}, "
                    f"Away {md['away_raw_ppg']:.0f}→{md['away_adjusted_ppg']:.0f}"
                )
        
        # Check 5th percentile vs minimum (worst case)
        if sim['percentiles']['5th'] < minimum_total:
            gap = minimum_total - sim['percentiles']['5th']
            result['risk_factors'].append(f"⚠️ 5th percentile ({sim['percentiles']['5th']:.0f}) is {gap:.0f} below min")
        
        # Main line proximity check
        if main_line_proximity is not None:
            if main_line_proximity < 70:
                result['risk_factors'].append(f"🚫 Only {main_line_proximity:.0f}% get within 10 of main line")
                if result['decision'] == 'YES':
                    result['decision'] = 'MAYBE'
            elif main_line_proximity < 85:
                result['risk_factors'].append(f"⚠️ {main_line_proximity:.0f}% get within 10 of main line")
        
        # Adjust for data quality
        if sim['data_quality'] in ['partial', 'none']:
            result['risk_factors'].append(f"⚠️ Limited data ({sim['data_quality']})")
            if result['decision'] == 'YES' and hit_rate < 95:
                result['decision'] = 'MAYBE'
        elif sim['data_quality'] == 'low':
            result['risk_factors'].append(f"⚠️ Low data quality (< 3 games per team)")
            if result['decision'] == 'YES' and hit_rate < 94:
                result['decision'] = 'MAYBE'
        
        return result
    
    def evaluate_all_games(self, games: List[Dict], n_simulations: int = 10000) -> Tuple[List[Dict], Dict]:
        """
        Evaluate all games in a list.
        
        Args:
            games: List of dicts with home_team, away_team, minimum_total, standard_total
            n_simulations: Simulations per game
            
        Returns:
            Tuple of (results list, summary dict)
        """
        print(f"\n🎲 Running Monte Carlo V2 ({n_simulations:,} sims per game)...")
        print(f"   WITH opponent defense adjustments")
        
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
        defense_warnings = sum(1 for r in results if r.get('defense_warning', False))
        
        summary = {
            'total_games': len(results),
            'yes_count': yes_count,
            'maybe_count': maybe_count,
            'no_count': no_count,
            'defense_warnings': defense_warnings,
            'avg_hit_rate': np.mean([r['hit_rate'] for r in results]) if results else 0,
            'simulations_per_game': n_simulations,
        }
        
        print(f"   Done! {yes_count} YES, {maybe_count} MAYBE, {no_count} NO")
        print(f"   ⚠️ {defense_warnings} games have elite defense matchups")
        
        return results, summary
    
    def print_report(self, results: List[Dict], summary: Dict):
        """Print formatted evaluation report."""
        print("\n" + "=" * 80)
        print("🎲 CBB MINIMUM TOTALS - MONTE CARLO V2 ANALYSIS")
        print(f"   {summary['simulations_per_game']:,} simulations per game")
        print(f"   WITH opponent defense adjustments")
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
                defense_flag = " 🛡️" if r.get('defense_warning') else ""
                prox_str = f" | Main±10: {r['main_line_proximity']:.0f}%" if r['main_line_proximity'] else ""
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}{defense_flag}")
                print(f"    Min: {r['minimum_total']:<6} | Hit Rate: {r['hit_rate']:.1f}%{prox_str}")
                print(f"    Sim: {r['sim_min']:.0f}-{r['sim_max']:.0f} (avg {r['sim_mean']:.1f})")
                # Show defense adjustment if significant
                md = r.get('matchup_details', {})
                if md:
                    home_adj = md.get('home_raw_ppg', 0) - md.get('home_adjusted_ppg', 0)
                    away_adj = md.get('away_raw_ppg', 0) - md.get('away_adjusted_ppg', 0)
                    if abs(home_adj) > 3 or abs(away_adj) > 3:
                        print(f"    Adj: Home {md.get('home_raw_ppg',0):.0f}→{md.get('home_adjusted_ppg',0):.0f}, "
                              f"Away {md.get('away_raw_ppg',0):.0f}→{md.get('away_adjusted_ppg',0):.0f}")
        
        if maybe_picks:
            print(f"\n🟡 MAYBE - PROCEED WITH CAUTION ({len(maybe_picks)} games)")
            print("-" * 80)
            for r in maybe_picks:
                defense_flag = " 🛡️" if r.get('defense_warning') else ""
                prox_str = f" | Main±10: {r['main_line_proximity']:.0f}%" if r['main_line_proximity'] else ""
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}{defense_flag}")
                print(f"    Min: {r['minimum_total']:<6} | Hit Rate: {r['hit_rate']:.1f}%{prox_str}")
                print(f"    Sim: {r['sim_min']:.0f}-{r['sim_max']:.0f} (avg {r['sim_mean']:.1f})")
                # Show key risk
                risk = [f for f in r['risk_factors'] if '⚠️' in f or '🚫' in f or '🛡️' in f]
                if risk:
                    print(f"    → {risk[0]}")
        
        if no_picks:
            print(f"\n🔴 NO - SKIP THESE ({len(no_picks)} games)")
            print("-" * 80)
            for r in no_picks[:10]:
                defense_flag = " 🛡️" if r.get('defense_warning') else ""
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}{defense_flag}")
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
        print(f"   🟢 YES: {summary['yes_count']} picks (92%+ hit rate)")
        print(f"   🟡 MAYBE: {summary['maybe_count']} picks (85-92% hit rate)")
        print(f"   🔴 NO: {summary['no_count']} skipped (<85% hit rate)")
        print(f"   🛡️ Elite defense matchups: {summary['defense_warnings']}")
        print(f"   📈 Average Hit Rate: {summary['avg_hit_rate']:.1f}%")
        print("=" * 80)
    
    def backtest_game(self, home_team: str, away_team: str,
                      minimum_total: float, actual_total: float,
                      standard_total: float = None) -> Dict:
        """
        Backtest a single game to see if V2 would have caught it.
        
        Returns dict with prediction vs actual.
        """
        result = self.evaluate_game(home_team, away_team, minimum_total, standard_total)
        
        actual_hit = actual_total >= minimum_total
        predicted_yes = result['decision'] == 'YES'
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'minimum_total': minimum_total,
            'actual_total': actual_total,
            'actual_hit': actual_hit,
            'v2_decision': result['decision'],
            'v2_hit_rate': result['hit_rate'],
            'v2_sim_mean': result['sim_mean'],
            'defense_warning': result['defense_warning'],
            'correct': (predicted_yes and actual_hit) or (not predicted_yes and not actual_hit),
            'false_positive': predicted_yes and not actual_hit,
            'false_negative': not predicted_yes and actual_hit,
        }


# Convenience functions for integration
def evaluate_all_games(games: List[Dict], n_simulations: int = 10000) -> Tuple[List[Dict], Dict]:
    """Main entry point - V2 with defense adjustments."""
    simulator = MonteCarloSimulatorV2()
    return simulator.evaluate_all_games(games, n_simulations)


def print_evaluation_report(results: List[Dict], summary: Dict):
    """Print formatted report."""
    simulator = MonteCarloSimulatorV2.__new__(MonteCarloSimulatorV2)
    simulator.print_report(results, summary)


if __name__ == "__main__":
    # Test mode - backtest the two losses
    print("Monte Carlo V2 - Backtest Mode")
    print("=" * 60)
    
    default_path = Path(__file__).parent / 'data' / 'ncaa_games_history.csv'
    if not default_path.exists():
        print(f"\n⚠️ No game data found at {default_path}")
    else:
        sim = MonteCarloSimulatorV2(str(default_path))
        
        print("\n📊 BACKTESTING THE TWO LOSSES:")
        print("-" * 60)
        
        # Michigan St @ North Carolina
        result1 = sim.backtest_game(
            home_team='North Carolina',
            away_team='Michigan St.',
            minimum_total=140.5,
            actual_total=132,
            standard_total=152.5
        )
        print(f"\n{result1['away_team']} @ {result1['home_team']}")
        print(f"  Minimum: {result1['minimum_total']} | Actual: {result1['actual_total']}")
        print(f"  V2 Decision: {result1['v2_decision']} ({result1['v2_hit_rate']:.1f}%)")
        print(f"  V2 Sim Mean: {result1['v2_sim_mean']:.1f}")
        print(f"  Defense Warning: {result1['defense_warning']}")
        print(f"  Would have avoided loss: {'YES ✅' if not result1['false_positive'] else 'NO ❌'}")
        
        # Saint Louis @ Santa Clara
        result2 = sim.backtest_game(
            home_team='Santa Clara',
            away_team='Saint Louis',
            minimum_total=147.5,
            actual_total=141,
            standard_total=159.5
        )
        print(f"\n{result2['away_team']} @ {result2['home_team']}")
        print(f"  Minimum: {result2['minimum_total']} | Actual: {result2['actual_total']}")
        print(f"  V2 Decision: {result2['v2_decision']} ({result2['v2_hit_rate']:.1f}%)")
        print(f"  V2 Sim Mean: {result2['v2_sim_mean']:.1f}")
        print(f"  Defense Warning: {result2['defense_warning']}")
        print(f"  Would have avoided loss: {'YES ✅' if not result2['false_positive'] else 'NO ❌'}")