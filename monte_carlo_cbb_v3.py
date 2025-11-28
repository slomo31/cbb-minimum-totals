"""
CBB MINIMUM TOTALS - MONTE CARLO SIMULATION ENGINE V3
======================================================
COMBINES:
1. Barttorvik efficiency + tempo data (expected scoring)
2. Game history data (variance/standard deviation)

KEY IMPROVEMENTS OVER V2:
- Uses adjusted efficiency (accounts for strength of schedule)
- Tempo-based scoring (possessions × efficiency)
- Matchup-specific calculations (both teams' offense vs defense)
- Real variance from game history
- Dual data source validation

This should be the most accurate version yet.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import json
from datetime import datetime
import requests


class MonteCarloSimulatorV3:
    """
    Monte Carlo simulation engine combining Barttorvik + game history.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize simulator with both data sources.
        
        Args:
            data_dir: Path to data directory
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / 'data'
        else:
            data_dir = Path(data_dir)
        
        self.data_dir = data_dir
        self.barttorvik_df = None
        self.game_history_df = None
        self.team_variance = {}  # From game history
        self.name_cache = {}
        
        # Load data sources
        self._load_barttorvik()
        self._load_game_history()
        
        # League averages for fallbacks
        self.league_avg_tempo = 67.5
        self.league_avg_efficiency = 100.0
    
    def _load_barttorvik(self):
        """Load Barttorvik stats."""
        bt_file = self.data_dir / 'barttorvik_stats.csv'
        
        if bt_file.exists():
            self.barttorvik_df = pd.read_csv(bt_file)
            print(f"✅ Loaded Barttorvik data: {len(self.barttorvik_df)} teams")
        else:
            print(f"⚠️ Barttorvik file not found at {bt_file}")
            print("   Run: python fetch_barttorvik.py")
            self.barttorvik_df = pd.DataFrame()
    
    def _load_game_history(self):
        """Load game history and calculate variance per team."""
        gh_file = self.data_dir / 'ncaa_games_history.csv'
        
        if gh_file.exists():
            self.game_history_df = pd.read_csv(gh_file)
            print(f"✅ Loaded game history: {len(self.game_history_df)} games")
            self._calculate_team_variance()
        else:
            print(f"⚠️ Game history not found at {gh_file}")
            self.game_history_df = pd.DataFrame()
    
    def _calculate_team_variance(self):
        """Calculate scoring variance for each team from game history."""
        if self.game_history_df.empty:
            return
        
        df = self.game_history_df
        
        # Get all teams
        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
        
        for team in all_teams:
            # Get all scores for this team
            home_scores = df[df['home_team'] == team]['home_score'].tolist()
            away_scores = df[df['away_team'] == team]['away_score'].tolist()
            all_scores = home_scores + away_scores
            
            # Get game totals
            home_totals = df[df['home_team'] == team]['total_points'].tolist()
            away_totals = df[df['away_team'] == team]['total_points'].tolist()
            all_totals = home_totals + away_totals
            
            if len(all_scores) >= 1:
                self.team_variance[team] = {
                    'games': len(all_scores),
                    'scores': all_scores,
                    'ppg_mean': np.mean(all_scores),
                    'ppg_std': np.std(all_scores) if len(all_scores) > 1 else 10.0,
                    'ppg_min': min(all_scores),
                    'ppg_max': max(all_scores),
                    'total_std': np.std(all_totals) if len(all_totals) > 1 else 15.0,
                }
        
        print(f"   Calculated variance for {len(self.team_variance)} teams")
    
    def _find_barttorvik_team(self, name: str) -> Optional[pd.Series]:
        """Find team in Barttorvik data with fuzzy matching."""
        if self.barttorvik_df.empty:
            return None
        
        cache_key = f"bt_{name}"
        if cache_key in self.name_cache:
            cached = self.name_cache[cache_key]
            if cached is None:
                return None
            return self.barttorvik_df[self.barttorvik_df['team'] == cached].iloc[0]
        
        name_lower = name.lower().strip()
        
        # Remove common suffixes for matching
        suffixes_to_remove = [
            'wildcats', 'bulldogs', 'tigers', 'bears', 'eagles', 'hawks',
            'cardinals', 'blue devils', 'tar heels', 'spartans', 'wolverines',
            'hoyas', 'friars', 'billikens', 'broncos', 'gaels', 'flyers',
            'cougars', 'huskies', 'cavaliers', 'fighting illini', 'boilermakers',
            'mountaineers', 'razorbacks', 'crimson tide', 'volunteers', 'gators',
            'seminoles', 'hurricanes', 'yellow jackets', 'demon deacons',
            'red raiders', 'longhorns', 'sooners', 'jayhawks', 'cyclones',
            'golden eagles', 'musketeers', 'bluejays', 'red storm', 'pirates',
            'hoosiers', 'buckeyes', 'nittany lions', 'terrapins', 'badgers',
            'hawkeyes', 'golden gophers', 'cornhuskers', 'scarlet knights'
        ]
        
        clean_name = name_lower
        for suffix in suffixes_to_remove:
            clean_name = clean_name.replace(suffix, '').strip()
        
        # Also handle abbreviations
        abbrev_map = {
            'uconn': 'connecticut',
            'unc': 'north carolina',
            'lsu': 'lsu',
            'tcu': 'tcu',
            'smu': 'smu',
            'byu': 'byu',
            'vcu': 'vcu',
            'ucf': 'ucf',
            'usc': 'southern california',
            'ucla': 'ucla',
            'unlv': 'unlv',
        }
        
        if clean_name in abbrev_map:
            clean_name = abbrev_map[clean_name]
        
        # Try to find match
        for idx, row in self.barttorvik_df.iterrows():
            team_lower = row['team'].lower()
            
            # Direct match
            if team_lower == name_lower or team_lower == clean_name:
                self.name_cache[cache_key] = row['team']
                return row
            
            # Partial match
            if clean_name in team_lower or team_lower in clean_name:
                self.name_cache[cache_key] = row['team']
                return row
            
            # Word overlap
            name_words = set(clean_name.split())
            team_words = set(team_lower.split())
            # Remove common words
            common = {'st', 'st.', 'state', 'university', 'of', 'the'}
            name_words -= common
            team_words -= common
            
            if name_words and team_words and name_words & team_words:
                # At least one meaningful word matches
                overlap = name_words & team_words
                if len(overlap) >= 1 and any(len(w) > 3 for w in overlap):
                    self.name_cache[cache_key] = row['team']
                    return row
        
        # Fuzzy match as last resort
        best_match = None
        best_score = 0.0
        
        for idx, row in self.barttorvik_df.iterrows():
            score = SequenceMatcher(None, clean_name, row['team'].lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = row
        
        if best_score >= 0.6:
            self.name_cache[cache_key] = best_match['team']
            return best_match
        
        self.name_cache[cache_key] = None
        return None
    
    def _find_variance_team(self, name: str) -> Optional[Dict]:
        """Find team in game history variance data."""
        cache_key = f"var_{name}"
        if cache_key in self.name_cache:
            return self.team_variance.get(self.name_cache[cache_key])
        
        name_lower = name.lower()
        
        # Direct match
        if name in self.team_variance:
            self.name_cache[cache_key] = name
            return self.team_variance[name]
        
        # Fuzzy match
        for team_name in self.team_variance.keys():
            if name_lower in team_name.lower() or team_name.lower() in name_lower:
                self.name_cache[cache_key] = team_name
                return self.team_variance[team_name]
        
        # Word match
        name_words = set(name_lower.replace('.', '').split())
        for team_name in self.team_variance.keys():
            team_words = set(team_name.lower().replace('.', '').split())
            if name_words & team_words:
                self.name_cache[cache_key] = team_name
                return self.team_variance[team_name]
        
        return None
    
    def _calculate_matchup_expected(self, home_bt: pd.Series, away_bt: pd.Series) -> Dict:
        """
        Calculate expected scoring using Barttorvik efficiency + tempo.
        
        The formula:
        - Game tempo = average of both teams' tempos (adjusted toward league avg)
        - Team score = (team_off_eff × opp_def_eff / 100) × game_tempo / 100
        
        This accounts for:
        - How good the offense is (adj_o)
        - How good the opposing defense is (adj_d)
        - How fast both teams play (tempo)
        """
        home_adj_o = home_bt['adj_o']
        home_adj_d = home_bt['adj_d']
        home_tempo = home_bt['adj_tempo']
        
        away_adj_o = away_bt['adj_o']
        away_adj_d = away_bt['adj_d']
        away_tempo = away_bt['adj_tempo']
        
        # Game tempo: weighted average (both teams influence pace)
        # Slight weight toward league average to regress extremes
        game_tempo = (home_tempo * 0.4) + (away_tempo * 0.4) + (self.league_avg_tempo * 0.2)
        
        # Expected points calculation
        # Home team: their offense vs away defense
        # Formula: (off_eff * def_eff / league_avg_eff) * tempo / 100
        # Simplified: we use geometric-style blend
        
        # Home scoring: blend of home offense and away defense
        home_off_factor = home_adj_o / 100  # Convert to multiplier
        away_def_factor = away_adj_d / 100  # Higher = worse defense = more points
        home_expected = (home_off_factor * away_def_factor) * game_tempo
        
        # Away scoring: blend of away offense and home defense
        away_off_factor = away_adj_o / 100
        home_def_factor = home_adj_d / 100
        away_expected = (away_off_factor * home_def_factor) * game_tempo
        
        # Home court advantage: ~3-4 points total, split between offense boost and defense boost
        home_advantage = 3.5
        home_expected += home_advantage * 0.6  # 60% of advantage is offensive
        away_expected -= home_advantage * 0.4  # 40% is defensive
        
        return {
            'home_expected': home_expected,
            'away_expected': away_expected,
            'total_expected': home_expected + away_expected,
            'game_tempo': game_tempo,
            'home_adj_o': home_adj_o,
            'home_adj_d': home_adj_d,
            'away_adj_o': away_adj_o,
            'away_adj_d': away_adj_d,
        }
    
    def _get_team_std(self, bt_team: pd.Series, var_team: Dict) -> float:
        """
        Get standard deviation for team scoring.
        
        Uses game history if available, otherwise estimates from efficiency.
        """
        if var_team and var_team['games'] >= 3:
            # Use actual variance from games, but set minimum
            return max(var_team['ppg_std'], 8.0)
        
        # Estimate std from efficiency (higher efficiency teams tend to be more consistent)
        # Base std of 10, adjusted slightly by efficiency
        if bt_team is not None:
            adj_o = bt_team['adj_o']
            # Elite offenses (120+) slightly more consistent, weak offenses more variable
            if adj_o >= 115:
                return 9.0
            elif adj_o >= 105:
                return 10.0
            else:
                return 11.0
        
        return 10.0  # Default
    
    def _is_elite_defense(self, adj_d: float) -> bool:
        """Check if team has elite defense (adj_d < 95 is very good)."""
        return adj_d < 95
    
    def _is_slow_tempo(self, tempo: float) -> bool:
        """Check if team plays slow (< 65 possessions)."""
        return tempo < 65
    
    def simulate_game(self, home_team: str, away_team: str,
                      n_simulations: int = 10000) -> Dict:
        """
        Run Monte Carlo simulation combining Barttorvik + game history.
        """
        # Find teams in both data sources
        home_bt = self._find_barttorvik_team(home_team)
        away_bt = self._find_barttorvik_team(away_team)
        home_var = self._find_variance_team(home_team)
        away_var = self._find_variance_team(away_team)
        
        result = {
            'home_team': home_team,
            'away_team': away_team,
            'home_bt_found': home_bt is not None,
            'away_bt_found': away_bt is not None,
            'home_var_found': home_var is not None,
            'away_var_found': away_var is not None,
            'simulations': n_simulations,
            'data_quality': 'unknown',
            'defense_warning': False,
            'tempo_warning': False,
            'matchup_details': {}
        }
        
        # Determine data quality
        if home_bt is not None and away_bt is not None:
            if home_var and away_var and home_var['games'] >= 3 and away_var['games'] >= 3:
                result['data_quality'] = 'high'
            else:
                result['data_quality'] = 'medium'  # Have efficiency but limited variance data
        elif home_bt is not None or away_bt is not None:
            result['data_quality'] = 'partial'
        else:
            result['data_quality'] = 'low'
        
        # Calculate expected scoring from Barttorvik
        if home_bt is not None and away_bt is not None:
            matchup = self._calculate_matchup_expected(home_bt, away_bt)
            home_mean = matchup['home_expected']
            away_mean = matchup['away_expected']
            
            result['matchup_details'] = {
                'home_adj_o': matchup['home_adj_o'],
                'home_adj_d': matchup['home_adj_d'],
                'away_adj_o': matchup['away_adj_o'],
                'away_adj_d': matchup['away_adj_d'],
                'game_tempo': matchup['game_tempo'],
                'home_expected': home_mean,
                'away_expected': away_mean,
                'total_expected': matchup['total_expected'],
            }
            
            # Check for elite defense / slow tempo warnings
            if self._is_elite_defense(home_bt['adj_d']) or self._is_elite_defense(away_bt['adj_d']):
                result['defense_warning'] = True
            if self._is_slow_tempo(home_bt['adj_tempo']) or self._is_slow_tempo(away_bt['adj_tempo']):
                result['tempo_warning'] = True
        else:
            # Fallback to game history or defaults
            if home_var:
                home_mean = home_var['ppg_mean'] + 2  # Home advantage
            else:
                home_mean = 72.0  # League average + home
            
            if away_var:
                away_mean = away_var['ppg_mean']
            else:
                away_mean = 68.0  # League average away
            
            result['matchup_details'] = {
                'home_expected': home_mean,
                'away_expected': away_mean,
                'total_expected': home_mean + away_mean,
                'note': 'Using fallback (missing Barttorvik data)'
            }
        
        # Get standard deviations from game history
        home_std = self._get_team_std(home_bt, home_var)
        away_std = self._get_team_std(away_bt, away_var)
        
        # Run simulations
        np.random.seed(None)
        sim_totals = []
        
        for _ in range(n_simulations):
            # Base scoring from normal distribution
            home_score = np.random.normal(home_mean, home_std)
            away_score = np.random.normal(away_mean, away_std)
            
            # Bad night scenarios (5% chance each)
            if np.random.random() < 0.05:
                home_score = home_mean * np.random.uniform(0.70, 0.85)
            if np.random.random() < 0.05:
                away_score = away_mean * np.random.uniform(0.70, 0.85)
            
            # Rare defensive slugfest (2%)
            if np.random.random() < 0.02:
                adjustment = np.random.uniform(-8, -15)
                home_score += adjustment / 2
                away_score += adjustment / 2
            
            # Floor at realistic minimums
            home_score = max(40, home_score)
            away_score = max(40, away_score)
            
            sim_totals.append(home_score + away_score)
        
        result['sim_totals'] = sim_totals
        result['mean_total'] = np.mean(sim_totals)
        result['std_total'] = np.std(sim_totals)
        result['min_total'] = np.min(sim_totals)
        result['max_total'] = np.max(sim_totals)
        
        result['percentiles'] = {
            '1st': np.percentile(sim_totals, 1),
            '5th': np.percentile(sim_totals, 5),
            '10th': np.percentile(sim_totals, 10),
            '25th': np.percentile(sim_totals, 25),
            '50th': np.percentile(sim_totals, 50),
        }
        
        return result
    
    def evaluate_game(self, home_team: str, away_team: str,
                      minimum_total: float, standard_total: float = None,
                      n_simulations: int = 10000) -> Dict:
        """
        Evaluate if a game will hit its minimum total.
        """
        sim = self.simulate_game(home_team, away_team, n_simulations)
        
        # Calculate hit rate
        hits = sum(1 for t in sim['sim_totals'] if t >= minimum_total)
        hit_rate = hits / len(sim['sim_totals']) * 100
        
        # Main line proximity
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
            'data_quality': sim['data_quality'],
            'defense_warning': sim['defense_warning'],
            'tempo_warning': sim['tempo_warning'],
            'matchup_details': sim['matchup_details'],
            'risk_factors': []
        }
        
        # Decision logic
        if hit_rate >= 95:
            result['decision'] = 'YES'
            result['risk_factors'].append(f"✅ {hit_rate:.1f}% hit rate (very high)")
        elif hit_rate >= 88:
            result['decision'] = 'YES'
            result['risk_factors'].append(f"✅ {hit_rate:.1f}% hit rate")
        elif hit_rate >= 80:
            result['decision'] = 'MAYBE'
            result['risk_factors'].append(f"⚠️ {hit_rate:.1f}% hit rate (borderline)")
        else:
            result['decision'] = 'NO'
            result['risk_factors'].append(f"🚫 {hit_rate:.1f}% hit rate")
        
        # Warnings
        if sim['defense_warning']:
            result['risk_factors'].append("🛡️ Elite defense in matchup")
            if result['decision'] == 'YES' and hit_rate < 92:
                result['decision'] = 'MAYBE'
                result['risk_factors'].append("⚠️ Downgraded for elite defense")
        
        if sim['tempo_warning']:
            result['risk_factors'].append("🐢 Slow tempo team in matchup")
        
        # Data quality warnings
        if sim['data_quality'] in ['partial', 'low']:
            result['risk_factors'].append(f"⚠️ Limited data ({sim['data_quality']})")
            if result['decision'] == 'YES' and hit_rate < 92:
                result['decision'] = 'MAYBE'
        
        # Simulation details
        result['risk_factors'].append(f"Sim: {sim['min_total']:.0f}-{sim['max_total']:.0f} (avg {sim['mean_total']:.1f})")
        
        # 5th percentile check
        if sim['percentiles']['5th'] < minimum_total:
            gap = minimum_total - sim['percentiles']['5th']
            result['risk_factors'].append(f"⚠️ 5th pct ({sim['percentiles']['5th']:.0f}) is {gap:.0f} below min")
        
        return result
    
    def evaluate_all_games(self, games: List[Dict], n_simulations: int = 10000) -> Tuple[List[Dict], Dict]:
        """Evaluate all games."""
        print(f"\n🎲 Running Monte Carlo V3 ({n_simulations:,} sims per game)...")
        print(f"   Using Barttorvik efficiency + game history variance")
        
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
        
        return results, summary
    
    def print_report(self, results: List[Dict], summary: Dict):
        """Print formatted report."""
        print("\n" + "=" * 80)
        print("🎲 CBB MINIMUM TOTALS - MONTE CARLO V3")
        print(f"   {summary['simulations_per_game']:,} simulations per game")
        print(f"   Barttorvik efficiency + game history variance")
        print("=" * 80)
        
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
                flags = ""
                if r.get('defense_warning'): flags += " 🛡️"
                if r.get('tempo_warning'): flags += " 🐢"
                
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}{flags}")
                print(f"    Min: {r['minimum_total']:<6.1f} | Hit Rate: {r['hit_rate']:.1f}%")
                
                md = r.get('matchup_details', {})
                if 'total_expected' in md:
                    print(f"    Expected: {md['total_expected']:.1f} | Tempo: {md.get('game_tempo', 0):.1f}")
                print(f"    Sim: {r['sim_min']:.0f}-{r['sim_max']:.0f} (avg {r['sim_mean']:.1f})")
        
        if maybe_picks:
            print(f"\n🟡 MAYBE - PROCEED WITH CAUTION ({len(maybe_picks)} games)")
            print("-" * 80)
            for r in maybe_picks[:10]:
                flags = ""
                if r.get('defense_warning'): flags += " 🛡️"
                if r.get('tempo_warning'): flags += " 🐢"
                
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}{flags}")
                print(f"    Min: {r['minimum_total']:<6.1f} | Hit Rate: {r['hit_rate']:.1f}%")
            
            if len(maybe_picks) > 10:
                print(f"  ... and {len(maybe_picks) - 10} more")
        
        if no_picks:
            print(f"\n🔴 NO - SKIP ({len(no_picks)} games)")
            print("-" * 80)
            for r in no_picks[:5]:
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}")
                print(f"    Min: {r['minimum_total']:<6.1f} | Hit Rate: {r['hit_rate']:.1f}%")
            if len(no_picks) > 5:
                print(f"  ... and {len(no_picks) - 5} more")
        
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print(f"   🟢 YES: {summary['yes_count']} (88%+ hit rate)")
        print(f"   🟡 MAYBE: {summary['maybe_count']} (80-88%)")
        print(f"   🔴 NO: {summary['no_count']} (<80%)")
        print(f"   🛡️ Elite defense matchups: {summary['defense_warnings']}")
        print("=" * 80)


# Convenience function for backward compatibility
def evaluate_all_games(games: List[Dict], n_simulations: int = 10000) -> Tuple[List[Dict], Dict]:
    """Main entry point."""
    simulator = MonteCarloSimulatorV3()
    return simulator.evaluate_all_games(games, n_simulations)


if __name__ == "__main__":
    print("Monte Carlo V3 - Test Mode")
    print("=" * 60)
    
    sim = MonteCarloSimulatorV3()
    
    # Test with a sample matchup
    print("\nSample matchup: Duke @ North Carolina")
    result = sim.evaluate_game(
        home_team='North Carolina',
        away_team='Duke',
        minimum_total=140.0,
        standard_total=155.0
    )
    
    print(f"  Decision: {result['decision']}")
    print(f"  Hit Rate: {result['hit_rate']:.1f}%")
    print(f"  Sim Mean: {result['sim_mean']:.1f}")
    print(f"  Data Quality: {result['data_quality']}")
    print(f"  Risk Factors: {result['risk_factors']}")
