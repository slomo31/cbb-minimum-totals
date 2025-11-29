#!/usr/bin/env python3
"""
CBB UNIFIED DAILY PICKER
=========================
Single picker that evaluates ALL games against BOTH criteria:
- Elite Filter (99%+ & 35+ cushion) → Tiers 1-4
- Monte Carlo Filter (88%+ hit rate) → YES/MAYBE/NO

This ensures Elite picks ALWAYS appear in Monte Carlo view.

Usage:
    python unified_picker.py
    python unified_picker.py --date 2025-01-15
"""

import sys
import argparse
from datetime import datetime
import requests
import pandas as pd
import numpy as np
from pathlib import Path

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"
DATA_DIR = Path(__file__).parent / "data"


# ============================================================
# EMBEDDED MONTE CARLO SIMULATOR
# ============================================================
class MonteCarloSimulator:
    """Monte Carlo simulator for CBB totals."""
    
    def __init__(self):
        self.team_stats = {}
        self.game_history = pd.DataFrame()
        self.team_variances = {}
        self._load_data()
    
    def _load_data(self):
        """Load Barttorvik stats and game history."""
        # Load Barttorvik
        bart_file = DATA_DIR / "barttorvik_stats.csv"
        if bart_file.exists():
            df = pd.read_csv(bart_file)
            for _, row in df.iterrows():
                name = row.get('team', '').lower().strip()
                self.team_stats[name] = {
                    'adj_o': row.get('adj_o', 100),
                    'adj_d': row.get('adj_d', 100),
                    'adj_t': row.get('adj_tempo', 68),
                    'name': row.get('team', '')
                }
            print(f"✅ Loaded Barttorvik data: {len(self.team_stats)} teams")
        
        # Load game history for variance calculation
        games_file = DATA_DIR / "ncaa_games_history.csv"
        if games_file.exists():
            self.game_history = pd.read_csv(games_file)
            self._calculate_variances()
            print(f"✅ Loaded game history: {len(self.game_history)} games")
    
    def _calculate_variances(self):
        """Calculate team scoring variances from game history."""
        if self.game_history.empty:
            return
        
        # Home team variances
        if 'home_team' in self.game_history.columns and 'home_score' in self.game_history.columns:
            home_vars = self.game_history.groupby('home_team')['home_score'].std()
            for team, std in home_vars.items():
                name = team.lower().strip()
                self.team_variances[name] = std if pd.notna(std) else 12.0
        
        # Away team variances
        if 'away_team' in self.game_history.columns and 'away_score' in self.game_history.columns:
            away_vars = self.game_history.groupby('away_team')['away_score'].std()
            for team, std in away_vars.items():
                name = team.lower().strip()
                if name not in self.team_variances:
                    self.team_variances[name] = std if pd.notna(std) else 12.0
    
    def _find_team(self, name: str) -> dict:
        """Find team stats with fuzzy matching."""
        name_lower = name.lower().strip()
        
        # Direct match
        if name_lower in self.team_stats:
            return self.team_stats[name_lower]
        
        # Partial match
        for key, stats in self.team_stats.items():
            if name_lower in key or key in name_lower:
                return stats
        
        # Default stats
        return {'adj_o': 100, 'adj_d': 100, 'adj_t': 68, 'name': name}
    
    def _get_team_std(self, name: str) -> float:
        """Get team's scoring standard deviation."""
        name_lower = name.lower().strip()
        
        if name_lower in self.team_variances:
            return self.team_variances[name_lower]
        
        for key, std in self.team_variances.items():
            if name_lower in key or key in name_lower:
                return std
        
        return 12.0  # Default
    
    def simulate_game(self, home_team: str, away_team: str, n_simulations: int = 10000) -> dict:
        """Run Monte Carlo simulation for a game."""
        home_stats = self._find_team(home_team)
        away_stats = self._find_team(away_team)
        
        home_std = self._get_team_std(home_team)
        away_std = self._get_team_std(away_team)
        
        # Calculate expected scores using Barttorvik efficiency
        avg_tempo = (home_stats['adj_t'] + away_stats['adj_t']) / 2
        
        # Home team: their offense vs away defense
        home_off = (home_stats['adj_o'] * away_stats['adj_d']) / 100
        home_expected = (home_off / 100) * avg_tempo + 2  # Home court
        
        # Away team: their offense vs home defense
        away_off = (away_stats['adj_o'] * home_stats['adj_d']) / 100
        away_expected = (away_off / 100) * avg_tempo - 2  # Road penalty
        
        # Run simulations
        home_scores = np.random.normal(home_expected, home_std, n_simulations)
        away_scores = np.random.normal(away_expected, away_std, n_simulations)
        
        # Floor/ceiling
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
            'away_expected': away_expected
        }


# ============================================================
# EMBEDDED ELITE FILTER
# ============================================================
class EliteCBBFilter:
    """Elite filter for CBB minimum totals."""
    
    def evaluate(self, home_team: str, away_team: str, hit_rate: float, cushion: float, date_str: str = None) -> dict:
        """Evaluate if a game qualifies for Elite tiers."""
        result = {
            'tier': None,
            'tier_label': 'NO BET',
            'reason': ''
        }
        
        # Tier 1: 99%+ & 35+ cushion (100% backtest)
        if hit_rate >= 99 and cushion >= 35:
            result['tier'] = 1
            result['tier_label'] = '🔒 TIER 1 - LOCK (100%)'
            result['reason'] = 'QUALIFIED'
        # Tier 2: 99%+ & 30+ cushion (92.9% backtest)
        elif hit_rate >= 99 and cushion >= 30:
            result['tier'] = 2
            result['tier_label'] = '✅ TIER 2 - VERY SAFE (92.9%)'
            result['reason'] = 'QUALIFIED'
        # Tier 3: 99%+ & 25+ cushion (93.0% backtest)
        elif hit_rate >= 99 and cushion >= 25:
            result['tier'] = 3
            result['tier_label'] = '✅ TIER 3 - SAFE (93.0%)'
            result['reason'] = 'QUALIFIED'
        # Tier 4: 98%+ & 35+ cushion (86.5% backtest)
        elif hit_rate >= 98 and cushion >= 35:
            result['tier'] = 4
            result['tier_label'] = '⚠️ TIER 4 - FLOOR (86.5%)'
            result['reason'] = 'QUALIFIED'
        else:
            if hit_rate < 98:
                result['reason'] = f'HIT_RATE_TOO_LOW ({hit_rate:.1f}% < 98%)'
            else:
                result['reason'] = f'CUSHION_TOO_LOW ({cushion:.1f} < 25)'
        
        return result


# ============================================================
# ODDS FETCHING
# ============================================================
def fetch_todays_odds(date_str: str = None) -> list:
    """Fetch today's CBB odds from The Odds API."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if date_str == today:
        url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',
            'markets': 'totals',
            'bookmakers': 'draftkings'
        }
    else:
        url = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',
            'markets': 'totals',
            'date': f"{date_str}T12:00:00Z",
            'bookmakers': 'draftkings'
        }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"📡 API calls remaining: {response.headers.get('x-requests-remaining', 'N/A')}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []


def parse_games_with_lines(odds_data: list) -> list:
    """Parse odds data to extract games with totals."""
    games = []
    
    for game in odds_data:
        home_team = game.get('home_team', '')
        away_team = game.get('away_team', '')
        commence_time = game.get('commence_time', '')
        
        for bookmaker in game.get('bookmakers', []):
            if bookmaker.get('key') == 'draftkings':
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'totals':
                        for outcome in market.get('outcomes', []):
                            if outcome.get('name') == 'Over':
                                standard_total = outcome.get('point', 0)
                                if standard_total > 0:
                                    games.append({
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'standard_total': standard_total,
                                        'minimum_total': standard_total - 12,
                                        'maximum_total': standard_total + 12,
                                        'commence_time': commence_time
                                    })
                                break
    
    return games


# ============================================================
# MAIN PICKER
# ============================================================
def run_unified_picker(date_str: str = None):
    """Run unified picker evaluating both Elite and MC criteria."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print("\n" + "=" * 70)
    print(f"🏀 CBB UNIFIED PICKER - {date_str}")
    print("=" * 70)
    print("Evaluating ALL games against:")
    print("  • Elite Filter: 99%+ & 35+ cushion → Tiers 1-4")
    print("  • Monte Carlo: 88%+ → YES, 80-88% → MAYBE")
    print("=" * 70)
    
    # Initialize
    sim = MonteCarloSimulator()
    elite_filter = EliteCBBFilter()
    
    # Fetch odds
    print(f"\n📡 Fetching odds...")
    odds_data = fetch_todays_odds(date_str)
    
    if not odds_data:
        print("❌ No odds data available")
        return []
    
    games = parse_games_with_lines(odds_data)
    print(f"   Found {len(games)} games with lines")
    
    if not games:
        print("❌ No games with totals found")
        return []
    
    # Evaluate each game
    print(f"\n🎲 Running Monte Carlo simulations (10,000 per game)...")
    
    all_results = []
    
    for i, game in enumerate(games):
        # Run simulation
        sim_result = sim.simulate_game(
            home_team=game['home_team'],
            away_team=game['away_team'],
            n_simulations=10000
        )
        
        minimum_line = game['minimum_total']
        
        # Calculate hit rate for OVER minimum
        over_hits = np.sum(sim_result['totals'] > minimum_line)
        hit_rate = (over_hits / len(sim_result['totals'])) * 100
        
        # Cushion = sim_mean - minimum_line
        cushion = sim_result['mean'] - minimum_line
        
        # === ELITE FILTER ===
        elite_result = elite_filter.evaluate(
            home_team=game['home_team'],
            away_team=game['away_team'],
            hit_rate=hit_rate,
            cushion=cushion,
            date_str=date_str
        )
        
        elite_tier = elite_result.get('tier')
        elite_label = elite_result.get('tier_label', 'NO BET')
        
        # === MONTE CARLO FILTER ===
        if hit_rate >= 88:
            mc_category = 'YES'
            mc_bet_size = '3%'
        elif hit_rate >= 80:
            mc_category = 'MAYBE'
            mc_bet_size = '1-2%'
        else:
            mc_category = 'NO'
            mc_bet_size = '0%'
        
        game_result = {
            'date': date_str,
            'commence_time': game['commence_time'],
            'away_team': game['away_team'],
            'home_team': game['home_team'],
            'standard_total': game['standard_total'],
            'minimum_total': minimum_line,
            'maximum_total': game['maximum_total'],
            'hit_rate': round(hit_rate, 1),
            'sim_mean': round(sim_result['mean'], 1),
            'cushion': round(cushion, 1),
            'elite_tier': elite_tier or 0,
            'elite_label': elite_label,
            'elite_qualified': elite_tier is not None and elite_tier > 0,
            'mc_category': mc_category,
            'mc_bet_size': mc_bet_size,
            'mc_qualified': mc_category in ['YES', 'MAYBE'],
        }
        
        all_results.append(game_result)
        
        if (i + 1) % 20 == 0:
            print(f"   Processed {i + 1}/{len(games)} games...")
    
    # === PRINT RESULTS ===
    print("\n" + "=" * 70)
    print("📊 ELITE MINIMUM (OVER) PICKS")
    print("=" * 70)
    
    elite_picks = [r for r in all_results if r['elite_qualified']]
    
    if not elite_picks:
        print("\n   No Elite picks today. Check Monte Carlo for lower-confidence options.")
    else:
        for tier in [1, 2, 3, 4]:
            tier_picks = [r for r in elite_picks if r['elite_tier'] == tier]
            if tier_picks:
                tier_labels = {
                    1: '🔒 TIER 1 - LOCK (100%)',
                    2: '✅ TIER 2 - VERY SAFE (92.9%)',
                    3: '✅ TIER 3 - SAFE (93.0%)',
                    4: '⚠️ TIER 4 - FLOOR (86.5%)',
                }
                print(f"\n{tier_labels[tier]} - {len(tier_picks)} pick(s)\n")
                
                for pick in sorted(tier_picks, key=lambda x: x['hit_rate'], reverse=True):
                    print(f"   {pick['away_team'][:25]:25} @ {pick['home_team'][:25]}")
                    print(f"      OVER {pick['minimum_total']} | {pick['hit_rate']:.1f}% | Cushion: +{pick['cushion']:.1f}")
    
    print("\n" + "=" * 70)
    print("🎲 MONTE CARLO PICKS")
    print("=" * 70)
    
    mc_yes = [r for r in all_results if r['mc_category'] == 'YES']
    mc_maybe = [r for r in all_results if r['mc_category'] == 'MAYBE']
    
    if mc_yes:
        print(f"\n🟢 YES - Bet These ({len(mc_yes)})\n")
        for pick in sorted(mc_yes, key=lambda x: x['hit_rate'], reverse=True):
            elite_badge = f" [ELITE T{pick['elite_tier']}]" if pick['elite_qualified'] else ""
            print(f"   {pick['away_team'][:25]:25} @ {pick['home_team'][:25]}")
            print(f"      OVER {pick['minimum_total']} | {pick['hit_rate']:.1f}% | Sim: {pick['sim_mean']:.0f}{elite_badge}")
    
    if mc_maybe:
        print(f"\n🟡 MAYBE - Caution ({len(mc_maybe)})\n")
        for pick in sorted(mc_maybe, key=lambda x: x['hit_rate'], reverse=True)[:10]:
            elite_badge = f" [ELITE T{pick['elite_tier']}]" if pick['elite_qualified'] else ""
            print(f"   {pick['away_team'][:25]:25} @ {pick['home_team'][:25]}")
            print(f"      OVER {pick['minimum_total']} | {pick['hit_rate']:.1f}% | Sim: {pick['sim_mean']:.0f}{elite_badge}")
        if len(mc_maybe) > 10:
            print(f"   ... and {len(mc_maybe) - 10} more")
    
    if not mc_yes and not mc_maybe:
        print("\n   No Monte Carlo picks today.")
    
    # === SAVE TO CSV FILES ===
    save_unified_results(all_results, date_str)
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"   Total games analyzed: {len(all_results)}")
    print(f"   Elite qualified: {len(elite_picks)} (Tiers 1-4)")
    print(f"   MC YES: {len(mc_yes)} | MC MAYBE: {len(mc_maybe)}")
    print("=" * 70)
    
    return all_results


def save_unified_results(all_results: list, date_str: str):
    """Save results to BOTH elite_picks.csv and monte_carlo_picks.csv."""
    DATA_DIR.mkdir(exist_ok=True)
    
    # === SAVE ELITE PICKS ===
    elite_rows = []
    for r in all_results:
        elite_rows.append({
            'date': r['date'],
            'game_time': r['commence_time'],
            'away_team': r['away_team'],
            'home_team': r['home_team'],
            'standard_total': r['standard_total'],
            'minimum_total': r['minimum_total'],
            'hit_rate': r['hit_rate'],
            'sim_mean': r['sim_mean'],
            'cushion': r['cushion'],
            'tier': r['elite_tier'],
            'tier_label': r['elite_label'],
            'reason': 'QUALIFIED' if r['elite_qualified'] else 'NOT_QUALIFIED',
        })
    
    elite_df = pd.DataFrame(elite_rows)
    elite_df['sort_key'] = elite_df['tier'].apply(lambda x: x if x > 0 else 99)
    elite_df = elite_df.sort_values(['sort_key', 'hit_rate'], ascending=[True, False])
    elite_df = elite_df.drop('sort_key', axis=1)
    
    elite_path = DATA_DIR / "elite_picks.csv"
    elite_df.to_csv(elite_path, index=False)
    print(f"\n💾 Saved {len(elite_df)} games to {elite_path}")
    print(f"   Elite qualified: {len(elite_df[elite_df['tier'] > 0])}")
    
    # === SAVE MONTE CARLO PICKS ===
    mc_rows = []
    for r in all_results:
        mc_rows.append({
            'date': r['date'],
            'game_time': r['commence_time'],
            'away_team': r['away_team'],
            'home_team': r['home_team'],
            'standard_total': r['standard_total'],
            'minimum_total': r['minimum_total'],
            'hit_rate': r['hit_rate'],
            'sim_mean': r['sim_mean'],
            'cushion': r['cushion'],
            'mc_category': r['mc_category'],
            'mc_bet_size': r['mc_bet_size'],
            'elite_tier': r['elite_tier'],
            'elite_qualified': r['elite_qualified'],
        })
    
    mc_df = pd.DataFrame(mc_rows)
    
    category_order = {'YES': 1, 'MAYBE': 2, 'NO': 3}
    mc_df['sort_key'] = mc_df['mc_category'].map(category_order)
    mc_df = mc_df.sort_values(['sort_key', 'hit_rate'], ascending=[True, False])
    mc_df = mc_df.drop('sort_key', axis=1)
    
    mc_path = DATA_DIR / "monte_carlo_picks.csv"
    mc_df.to_csv(mc_path, index=False)
    print(f"💾 Saved {len(mc_df)} games to {mc_path}")
    print(f"   MC YES: {len(mc_df[mc_df['mc_category'] == 'YES'])}")
    print(f"   MC MAYBE: {len(mc_df[mc_df['mc_category'] == 'MAYBE'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CBB Unified Daily Picker')
    parser.add_argument('--date', type=str, help='Date to check (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    
    run_unified_picker(args.date)