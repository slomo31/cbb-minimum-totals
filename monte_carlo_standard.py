#!/usr/bin/env python3
"""
Monte Carlo Standard Line Over/Under System

Instead of minimum totals, this predicts which side of the standard line
the game will land on. Only bets when confidence is 95%+.

At -110 odds, 95% confidence = massive edge
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import os

# Import the team name matcher
from team_name_matcher import normalize_team_name


def find_best_match(name: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
    """Simple fuzzy matching for team names."""
    name_lower = name.lower()
    name_words = set(name_lower.split())
    
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        cand_lower = candidate.lower()
        cand_words = set(cand_lower.split())
        
        # Word overlap score
        if name_words and cand_words:
            overlap = len(name_words & cand_words)
            total = len(name_words | cand_words)
            score = overlap / total
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
    
    return best_match


class StandardLineSimulator:
    """Monte Carlo simulator for standard over/under lines."""
    
    def __init__(self):
        """Initialize with Barttorvik data and game history."""
        self.barttorvik_df = None
        self.team_variance = {}
        self._load_data()
    
    def _load_data(self):
        """Load Barttorvik and variance data."""
        # Try multiple paths
        bt_paths = [
            os.path.expanduser("~/cbb_minimum_system/barttorvik_data.csv"),
            "/mnt/user-data/uploads/barttorvik_data.csv",
            "barttorvik_data.csv",
        ]
        
        for bt_path in bt_paths:
            if os.path.exists(bt_path):
                self.barttorvik_df = pd.read_csv(bt_path)
                print(f"✅ Loaded Barttorvik data: {len(self.barttorvik_df)} teams")
                break
        else:
            print("❌ Barttorvik data not found")
            return
        
        # Load game history for variance
        gh_paths = [
            os.path.expanduser("~/cbb_minimum_system/game_history.json"),
            "/mnt/user-data/uploads/game_history.json",
            "game_history.json",
        ]
        
        for gh_path in gh_paths:
            if os.path.exists(gh_path):
                with open(gh_path, 'r') as f:
                    games = json.load(f)
                print(f"✅ Loaded game history: {len(games)} games")
                self._calculate_variance(games)
                break
    
    def _calculate_variance(self, games: List[Dict]):
        """Calculate scoring variance per team."""
        team_scores = {}
        
        for game in games:
            for team_key, score_key in [('home_team', 'home_score'), ('away_team', 'away_score')]:
                team = game.get(team_key, '')
                score = game.get(score_key)
                if team and score:
                    if team not in team_scores:
                        team_scores[team] = []
                    team_scores[team].append(float(score))
        
        for team, scores in team_scores.items():
            if len(scores) >= 3:
                self.team_variance[team] = {
                    'mean': np.mean(scores),
                    'std': np.std(scores),
                    'games': len(scores),
                    'min': min(scores),
                    'max': max(scores)
                }
        
        print(f"   Calculated variance for {len(self.team_variance)} teams")
    
    def _find_barttorvik_team(self, team_name: str) -> Optional[pd.Series]:
        """Find team in Barttorvik data."""
        if self.barttorvik_df is None:
            return None
        
        canonical = normalize_team_name(team_name)
        bt_teams = self.barttorvik_df['team'].tolist()
        
        # Direct match
        for idx, bt_team in enumerate(bt_teams):
            if normalize_team_name(bt_team) == canonical:
                return self.barttorvik_df.iloc[idx]
        
        # Fuzzy match
        best_match = find_best_match(team_name, bt_teams)
        if best_match:
            return self.barttorvik_df[self.barttorvik_df['team'] == best_match].iloc[0]
        
        return None
    
    def _find_variance_team(self, team_name: str) -> Optional[Dict]:
        """Find team variance data."""
        canonical = normalize_team_name(team_name)
        
        # Direct match
        for team, data in self.team_variance.items():
            if normalize_team_name(team) == canonical:
                return data
        
        # Fuzzy match
        best_match = find_best_match(team_name, list(self.team_variance.keys()))
        if best_match:
            return self.team_variance[best_match]
        
        return None
    
    def simulate_game(self, home_team: str, away_team: str, n_simulations: int = 10000) -> Dict:
        """Run Monte Carlo simulation for a game."""
        home_bt = self._find_barttorvik_team(home_team)
        away_bt = self._find_barttorvik_team(away_team)
        home_var = self._find_variance_team(home_team)
        away_var = self._find_variance_team(away_team)
        
        # Get efficiency ratings
        if home_bt is not None and away_bt is not None:
            home_adj_o = home_bt['adj_o']
            home_adj_d = home_bt['adj_d']
            away_adj_o = away_bt['adj_o']
            away_adj_d = away_bt['adj_d']
            home_tempo = home_bt['adj_tempo']
            away_tempo = away_bt['adj_tempo']
            
            # Expected pace
            avg_tempo = 67.5
            game_tempo = (home_tempo + away_tempo) / 2
            pace_factor = game_tempo / avg_tempo
            
            # Expected points (adjusted for matchup)
            avg_efficiency = 107.5
            home_expected = ((home_adj_o / avg_efficiency) * (away_adj_d / avg_efficiency) * avg_efficiency) * pace_factor * 0.72
            away_expected = ((away_adj_o / avg_efficiency) * (home_adj_d / avg_efficiency) * avg_efficiency) * pace_factor * 0.72
            
            # Home court advantage
            home_expected += 2
            away_expected -= 1
            
            data_quality = 'good'
        else:
            # Fallback to variance data
            home_expected = home_var['mean'] if home_var else 70
            away_expected = away_var['mean'] if away_var else 70
            data_quality = 'partial' if (home_var or away_var) else 'low'
        
        # Determine standard deviation
        home_std = home_var['std'] if home_var else 12
        away_std = away_var['std'] if away_var else 12
        
        # Cap extreme values
        home_std = max(6, min(18, home_std))
        away_std = max(6, min(18, away_std))
        
        # Run simulations
        home_scores = np.random.normal(home_expected, home_std, n_simulations)
        away_scores = np.random.normal(away_expected, away_std, n_simulations)
        
        # Floor at realistic minimums
        home_scores = np.maximum(home_scores, 35)
        away_scores = np.maximum(away_scores, 35)
        
        totals = home_scores + away_scores
        
        return {
            'totals': totals,
            'mean_total': np.mean(totals),
            'std_total': np.std(totals),
            'min_total': np.min(totals),
            'max_total': np.max(totals),
            'home_expected': home_expected,
            'away_expected': away_expected,
            'percentiles': {
                '5th': np.percentile(totals, 5),
                '10th': np.percentile(totals, 10),
                '25th': np.percentile(totals, 25),
                '50th': np.percentile(totals, 50),
                '75th': np.percentile(totals, 75),
                '90th': np.percentile(totals, 90),
                '95th': np.percentile(totals, 95),
            },
            'data_quality': data_quality,
            'game_tempo': game_tempo if home_bt is not None else 67.5,
        }
    
    def evaluate_game(self, home_team: str, away_team: str, 
                      standard_total: float, n_simulations: int = 10000) -> Dict:
        """Evaluate a game against the standard line."""
        
        sim = self.simulate_game(home_team, away_team, n_simulations)
        
        # Calculate over/under probabilities
        over_count = np.sum(sim['totals'] > standard_total)
        under_count = np.sum(sim['totals'] < standard_total)
        push_count = n_simulations - over_count - under_count
        
        over_pct = (over_count / n_simulations) * 100
        under_pct = (under_count / n_simulations) * 100
        
        # Determine best side and confidence
        if over_pct > under_pct:
            best_side = 'OVER'
            confidence = over_pct
        else:
            best_side = 'UNDER'
            confidence = under_pct
        
        # Decision logic
        # 95%+ = strong bet
        # 90-95% = lean
        # <90% = no bet
        if confidence >= 95:
            decision = 'YES'
        elif confidence >= 90:
            decision = 'MAYBE'
        else:
            decision = 'NO'
        
        # Edge calculation (vs -110 odds which need 52.4% to break even)
        edge = confidence - 52.4
        
        result = {
            'home_team': home_team,
            'away_team': away_team,
            'standard_total': standard_total,
            'sim_mean': sim['mean_total'],
            'sim_std': sim['std_total'],
            'over_pct': over_pct,
            'under_pct': under_pct,
            'best_side': best_side,
            'confidence': confidence,
            'decision': decision,
            'edge': edge,
            'data_quality': sim['data_quality'],
            'risk_factors': [],
        }
        
        # Add context
        diff = sim['mean_total'] - standard_total
        result['risk_factors'].append(f"Line: {standard_total} | Sim Avg: {sim['mean_total']:.1f} ({diff:+.1f})")
        result['risk_factors'].append(f"Range: {sim['percentiles']['5th']:.0f} - {sim['percentiles']['95th']:.0f}")
        
        if sim['data_quality'] != 'good':
            result['risk_factors'].append(f"⚠️ Data quality: {sim['data_quality']}")
        
        return result
    
    def evaluate_all_games(self, games: List[Dict], n_simulations: int = 10000) -> Tuple[List[Dict], Dict]:
        """Evaluate all games."""
        print(f"\n🎲 Running Standard Line Simulator ({n_simulations:,} sims per game)...")
        
        results = []
        for i, game in enumerate(games):
            if game.get('standard_total'):
                result = self.evaluate_game(
                    home_team=game.get('home_team', ''),
                    away_team=game.get('away_team', ''),
                    standard_total=float(game['standard_total']),
                    n_simulations=n_simulations
                )
                result['game_id'] = game.get('game_id', '')
                results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"   Processed {i + 1}/{len(games)} games...")
        
        # Summary
        yes_count = sum(1 for r in results if r['decision'] == 'YES')
        maybe_count = sum(1 for r in results if r['decision'] == 'MAYBE')
        over_picks = sum(1 for r in results if r['decision'] == 'YES' and r['best_side'] == 'OVER')
        under_picks = sum(1 for r in results if r['decision'] == 'YES' and r['best_side'] == 'UNDER')
        
        summary = {
            'total_games': len(results),
            'yes_count': yes_count,
            'maybe_count': maybe_count,
            'over_picks': over_picks,
            'under_picks': under_picks,
            'avg_confidence': np.mean([r['confidence'] for r in results]) if results else 0,
        }
        
        print(f"   Done! {yes_count} YES picks ({over_picks} OVER, {under_picks} UNDER)")
        
        return results, summary
    
    def print_report(self, results: List[Dict], summary: Dict):
        """Print formatted report."""
        print("\n" + "=" * 80)
        print("🎲 CBB STANDARD LINE OVER/UNDER PICKS")
        print("=" * 80)
        
        yes_picks = sorted([r for r in results if r['decision'] == 'YES'],
                          key=lambda x: x['confidence'], reverse=True)
        maybe_picks = sorted([r for r in results if r['decision'] == 'MAYBE'],
                            key=lambda x: x['confidence'], reverse=True)
        
        if yes_picks:
            print(f"\n🟢 YES - BET THESE ({len(yes_picks)} games)")
            print("-" * 80)
            for r in yes_picks:
                side_emoji = "⬆️" if r['best_side'] == 'OVER' else "⬇️"
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}")
                print(f"    {side_emoji} {r['best_side']} {r['standard_total']} | {r['confidence']:.1f}% confidence | Edge: +{r['edge']:.1f}%")
                print(f"    Sim: {r['sim_mean']:.1f} avg | {r['risk_factors'][1]}")
        
        if maybe_picks:
            print(f"\n🟡 MAYBE - MONITOR ({len(maybe_picks)} games)")
            print("-" * 80)
            for r in maybe_picks[:10]:  # Top 10 only
                side_emoji = "⬆️" if r['best_side'] == 'OVER' else "⬇️"
                print(f"  {r['away_team'][:22]:22} @ {r['home_team'][:22]:22}")
                print(f"    {side_emoji} {r['best_side']} {r['standard_total']} | {r['confidence']:.1f}%")
        
        print("\n" + "=" * 80)
        print(f"📊 SUMMARY: {summary['yes_count']} strong picks, {summary['maybe_count']} leans")
        if summary['yes_count'] > 0:
            print(f"   OVER picks: {summary['over_picks']} | UNDER picks: {summary['under_picks']}")
        print("=" * 80)


if __name__ == "__main__":
    sim = StandardLineSimulator()
    
    # Test with a sample game
    result = sim.evaluate_game("Duke", "North Carolina", 155.5)
    print(f"\nTest: Duke vs UNC, Line: 155.5")
    print(f"  Best side: {result['best_side']} ({result['confidence']:.1f}%)")
    print(f"  Decision: {result['decision']}")
    print(f"  Sim mean: {result['sim_mean']:.1f}")
