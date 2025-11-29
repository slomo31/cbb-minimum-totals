#!/usr/bin/env python3
"""
CBB UNIFIED DAILY PICKER V2
============================
Updated with backtested tiers from 65-game live tracking data.

NEW TIERS (based on real DraftKings lines):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIER 1 🔒 98%+ hit rate  →  3-0   (100%)    LOCK - Heavy bet
TIER 2 ✅ 94%+ hit rate  →  8-1   (88.9%)   SAFE - Normal bet
TIER 3 �� 88%+ hit rate  →  11-2  (84.6%)   YES  - Light bet
MAYBE 🟡 80-88% hit rate →  Caution - Track only
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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


class MonteCarloSimulator:
    """Monte Carlo simulator for CBB totals with historical variance."""
    
    def __init__(self):
        self.team_stats = {}
        self.game_history = pd.DataFrame()
        self.team_variances = {}
        self._load_data()
    
    def _load_data(self):
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
        
        games_file = DATA_DIR / "ncaa_games_history.csv"
        if games_file.exists():
            self.game_history = pd.read_csv(games_file)
            self._calculate_variances()
            print(f"✅ Loaded game history: {len(self.game_history)} games")
    
    def _calculate_variances(self):
        if self.game_history.empty:
            return
        if 'home_team' in self.game_history.columns and 'home_score' in self.game_history.columns:
            home_vars = self.game_history.groupby('home_team')['home_score'].std()
            for team, std in home_vars.items():
                name = team.lower().strip()
                self.team_variances[name] = std if pd.notna(std) else 12.0
        if 'away_team' in self.game_history.columns and 'away_score' in self.game_history.columns:
            away_vars = self.game_history.groupby('away_team')['away_score'].std()
            for team, std in away_vars.items():
                name = team.lower().strip()
                if name not in self.team_variances:
                    self.team_variances[name] = std if pd.notna(std) else 12.0
    
    def _find_team(self, name: str) -> dict:
        name_lower = name.lower().strip()
        if name_lower in self.team_stats:
            return self.team_stats[name_lower]
        for key, stats in self.team_stats.items():
            if name_lower in key or key in name_lower:
                return stats
        return {'adj_o': 100, 'adj_d': 100, 'adj_t': 68, 'name': name}
    
    def _get_team_std(self, name: str) -> float:
        name_lower = name.lower().strip()
        if name_lower in self.team_variances:
            return self.team_variances[name_lower]
        for key, std in self.team_variances.items():
            if name_lower in key or key in name_lower:
                return std
        return 12.0
    
    def simulate_game(self, home_team: str, away_team: str, n_simulations: int = 10000) -> dict:
        home_stats = self._find_team(home_team)
        away_stats = self._find_team(away_team)
        home_std = self._get_team_std(home_team)
        away_std = self._get_team_std(away_team)
        
        avg_tempo = (home_stats['adj_t'] + away_stats['adj_t']) / 2
        home_off = (home_stats['adj_o'] * away_stats['adj_d']) / 100
        home_expected = (home_off / 100) * avg_tempo + 2
        away_off = (away_stats['adj_o'] * home_stats['adj_d']) / 100
        away_expected = (away_off / 100) * avg_tempo - 2
        
        home_scores = np.clip(np.random.normal(home_expected, home_std, n_simulations), 35, 130)
        away_scores = np.clip(np.random.normal(away_expected, away_std, n_simulations), 35, 130)
        total_scores = home_scores + away_scores
        
        return {
            'totals': total_scores,
            'mean': np.mean(total_scores),
            'std': np.std(total_scores),
        }


def fetch_todays_odds(date_str: str = None) -> list:
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    
    if date_str == today:
        url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
        params = {'apiKey': ODDS_API_KEY, 'regions': 'us', 'markets': 'totals', 'bookmakers': 'draftkings'}
    else:
        url = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
        params = {'apiKey': ODDS_API_KEY, 'regions': 'us', 'markets': 'totals', 'date': f"{date_str}T12:00:00Z", 'bookmakers': 'draftkings'}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"📡 API calls remaining: {response.headers.get('x-requests-remaining', 'N/A')}")
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []


def parse_games_with_lines(odds_data: list) -> list:
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
                                        'home_team': home_team, 'away_team': away_team,
                                        'standard_total': standard_total,
                                        'minimum_total': standard_total - 12,
                                        'maximum_total': standard_total + 12,
                                        'commence_time': commence_time
                                    })
                                break
    return games


def classify_pick(hit_rate: float) -> dict:
    """Classify based on 65-game backtest: 98%→100%, 94%→88.9%, 88%→84.6%"""
    if hit_rate >= 98:
        return {'tier': 1, 'tier_label': '🔒 TIER 1 - LOCK (100%)', 'category': 'LOCK', 'bet_size': 'Heavy (5%)', 'qualified': True}
    elif hit_rate >= 94:
        return {'tier': 2, 'tier_label': '✅ TIER 2 - SAFE (88.9%)', 'category': 'SAFE', 'bet_size': 'Normal (3%)', 'qualified': True}
    elif hit_rate >= 88:
        return {'tier': 3, 'tier_label': '🟢 TIER 3 - YES (84.6%)', 'category': 'YES', 'bet_size': 'Light (2%)', 'qualified': True}
    elif hit_rate >= 80:
        return {'tier': 4, 'tier_label': '🟡 MAYBE - Caution', 'category': 'MAYBE', 'bet_size': 'Track only (1%)', 'qualified': False}
    else:
        return {'tier': 0, 'tier_label': 'NO BET', 'category': 'NO', 'bet_size': '0%', 'qualified': False}


def run_unified_picker(date_str: str = None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print("\n" + "=" * 70)
    print(f"🏀 CBB UNIFIED PICKER V2 - {date_str}")
    print("=" * 70)
    print("TIERS (backtested on 65 games with real DK lines):")
    print("  🔒 TIER 1: 98%+ hit rate → 100% win rate  - Heavy bet (5%)")
    print("  ✅ TIER 2: 94%+ hit rate → 88.9% win rate - Normal bet (3%)")
    print("  🟢 TIER 3: 88%+ hit rate → 84.6% win rate - Light bet (2%)")
    print("  🟡 MAYBE:  80-88%        → Track only")
    print("=" * 70)
    
    sim = MonteCarloSimulator()
    
    print(f"\n📡 Fetching odds...")
    odds_data = fetch_todays_odds(date_str)
    if not odds_data:
        print("❌ No odds data available")
        return []
    
    games = parse_games_with_lines(odds_data)
    print(f"   Found {len(games)} games with lines")
    if not games:
        return []
    
    print(f"\n🎲 Running Monte Carlo simulations (10,000 per game)...")
    
    all_results = []
    for i, game in enumerate(games):
        sim_result = sim.simulate_game(game['home_team'], game['away_team'], 10000)
        minimum_line = game['minimum_total']
        hit_rate = (np.sum(sim_result['totals'] > minimum_line) / len(sim_result['totals'])) * 100
        cushion = sim_result['mean'] - minimum_line
        classification = classify_pick(hit_rate)
        
        all_results.append({
            'date': date_str, 'commence_time': game['commence_time'],
            'away_team': game['away_team'], 'home_team': game['home_team'],
            'standard_total': game['standard_total'], 'minimum_total': minimum_line,
            'maximum_total': game['maximum_total'], 'hit_rate': round(hit_rate, 1),
            'sim_mean': round(sim_result['mean'], 1), 'cushion': round(cushion, 1),
            'tier': classification['tier'], 'tier_label': classification['tier_label'],
            'category': classification['category'], 'bet_size': classification['bet_size'],
            'qualified': classification['qualified'],
        })
        if (i + 1) % 20 == 0:
            print(f"   Processed {i + 1}/{len(games)} games...")
    
    # Print results
    print("\n" + "=" * 70)
    print("📊 PICKS BY TIER")
    print("=" * 70)
    
    for tier_num, tier_name, emoji in [(1, "LOCK", "🔒"), (2, "SAFE", "✅"), (3, "YES", "🟢")]:
        tier_picks = [r for r in all_results if r['tier'] == tier_num]
        if tier_picks:
            print(f"\n{emoji} TIER {tier_num} - {tier_name} ({len(tier_picks)} picks)\n")
            for pick in sorted(tier_picks, key=lambda x: x['hit_rate'], reverse=True):
                print(f"   {pick['away_team'][:28]:<28} @ {pick['home_team'][:28]}")
                print(f"      OVER {pick['minimum_total']} | {pick['hit_rate']:.1f}% | Sim: {pick['sim_mean']:.0f}")
    
    maybe = [r for r in all_results if r['tier'] == 4]
    if maybe:
        print(f"\n🟡 MAYBE ({len(maybe)} picks) - Track only\n")
        for pick in sorted(maybe, key=lambda x: x['hit_rate'], reverse=True)[:8]:
            print(f"   {pick['away_team'][:28]:<28} @ {pick['home_team'][:28]}")
            print(f"      OVER {pick['minimum_total']} | {pick['hit_rate']:.1f}% | Sim: {pick['sim_mean']:.0f}")
        if len(maybe) > 8:
            print(f"   ... and {len(maybe) - 8} more")
    
    tier1 = [r for r in all_results if r['tier'] == 1]
    tier2 = [r for r in all_results if r['tier'] == 2]
    tier3 = [r for r in all_results if r['tier'] == 3]
    
    if not tier1 and not tier2 and not tier3:
        print("\n   ⚠️ No qualified picks today (nothing at 88%+)")
    
    # Save
    save_results(all_results, date_str)
    
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"   Total games: {len(all_results)}")
    print(f"   🔒 TIER 1: {len(tier1)}  |  ✅ TIER 2: {len(tier2)}  |  🟢 TIER 3: {len(tier3)}")
    print(f"   Total qualified: {len(tier1) + len(tier2) + len(tier3)}")
    print("=" * 70)
    
    return all_results


def save_results(all_results: list, date_str: str):
    DATA_DIR.mkdir(exist_ok=True)
    
    df = pd.DataFrame(all_results)
    df = df.sort_values(['tier', 'hit_rate'], ascending=[True, False])
    df.to_csv(DATA_DIR / "elite_picks.csv", index=False)
    
    # MC format for backward compatibility
    mc_df = df.copy()
    mc_df['mc_category'] = mc_df['tier'].apply(lambda x: 'YES' if x in [1,2,3] else ('MAYBE' if x == 4 else 'NO'))
    mc_df.to_csv(DATA_DIR / "monte_carlo_picks.csv", index=False)
    
    qualified = len(df[df['tier'].isin([1,2,3])])
    print(f"\n💾 Saved {len(df)} games | Qualified: {qualified}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CBB Unified Picker V2')
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    run_unified_picker(args.date)
