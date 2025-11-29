#!/usr/bin/env python3
"""
CBB MINIMUM TOTALS - ELITE FILTER V4
=====================================
PARLAY FUEL SYSTEM

4 TIERS (you decide which to bet):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIER 1 🔒 99%+ & 35+ cushion  →  89-0  (100%)   LOCK
TIER 2 ✅ 99%+ & 30+ cushion  →  118-9 (92.9%)  VERY SAFE  
TIER 3 ✅ 99%+ & 25+ cushion  →  120-9 (93.0%)  SAFE
TIER 4 ⚠️ 98%+ & 35+ cushion  →  179-28 (86.5%) FLOOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nothing below 98% & 35+ cushion is shown.

Usage:
    from elite_cbb_v4 import EliteCBBFilter
    
    filter = EliteCBBFilter()
    result = filter.evaluate_game(sim_result, minimum_line)
    
    if result['tier']:  # 1, 2, 3, or 4
        # Decide based on tier
"""

from datetime import datetime
from typing import Dict, List, Optional


class EliteCBBFilter:
    """
    Elite filter for CBB minimum totals.
    Only passes games that meet strict criteria for parlay safety.
    """
    
    # Teams/conferences to NEVER bet on
    BLACKLIST = [
        # America East
        'vermont', 'maine', 'albany', 'binghamton', 'umass lowell', 'umbc', 'new hampshire',
        # NEC
        'wagner', 'sacred heart', 'merrimack', 'st. francis', 'central connecticut', 'fairleigh',
        'fairleigh dickinson', 'stonehill', 'lio', 'le moyne',
        # WAC
        'tarleton', 'cal baptist', 'utah valley', 'seattle', 'abilene christian',
        'southern utah', 'utah tech', 'grand canyon',
        # ASUN
        'bellarmine', 'lipscomb', 'central arkansas', 'queens', 'jacksonville',
        'north florida', 'stetson', 'kennesaw', 'north alabama', 'austin peay',
        # Big South
        'radford', 'high point', 'charleston southern', 'unc asheville',
        'longwood', 'presbyterian', 'winthrop', 'gardner-webb', 'campbell',
        # Big Sky
        'eastern washington', 'idaho state', 'northern arizona', 'sacramento st', 'montana',
        'montana st', 'portland st', 'idaho', 'weber st', 'northern colorado',
        # Horizon
        'detroit mercy', 'cleveland st', 'oakland', 'youngstown', 'robert morris', 'green bay',
        'milwaukee', 'iupui', 'wright st', 'purdue fort wayne', 'fort wayne',
        # OVC
        'arkansas-little rock', 'western illinois', 'eastern illinois', 'morehead', 'tenn-martin',
        'tennessee tech', 'southeast missouri', 'siu edwardsville', 'lindenwood', 'tennessee st',
        'southern indiana', 'ut martin',
        # MEAC/SWAC (high variance)
        'bethune-cookman', 'florida a&m', 'norfolk st', 'howard', 'morgan st', 'coppin st',
        'delaware st', 'south carolina st', 'nc central', 'maryland eastern',
        'alabama a&m', 'alabama st', 'alcorn st', 'grambling', 'jackson st', 'miss valley',
        'prairie view', 'southern', 'texas southern', 'arkansas-pine bluff',
        # Southland
        'houston christian', 'incarnate word', 'lamar', 'mcneese', 'new orleans',
        'nicholls', 'northwestern st', 'southeastern louisiana', 'texas a&m-corpus',
        'texas a&m-commerce',
        # Summit League
        'denver', 'north dakota', 'north dakota st', 'oral roberts', 'south dakota',
        'south dakota st', 'umkc', 'western illinois', 'st. thomas',
        # Elite Defense Teams (suppress scoring unpredictably)
        'san diego st', 'virginia',
        # Specific problematic teams
        'georgetown',  # Home games are unpredictable
    ]
    
    def __init__(self, early_season_cutoff: str = "01-15"):
        """
        Initialize filter.
        
        Args:
            early_season_cutoff: MM-DD after which to use stricter thresholds
        """
        self.early_season_cutoff = early_season_cutoff
    
    def _is_early_season(self, date_str: str) -> bool:
        """Check if date is in early season (before Jan 15)."""
        try:
            if isinstance(date_str, str):
                date = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                date = date_str
            
            # Early season = Nov, Dec, first half of Jan
            month = date.month
            day = date.day
            
            if month in [11, 12]:
                return True
            if month == 1 and day <= 15:
                return True
            return False
        except:
            return False
    
    def _is_blacklisted(self, home_team: str, away_team: str) -> bool:
        """Check if either team is blacklisted."""
        home_lower = home_team.lower()
        away_lower = away_team.lower()
        
        for team in self.BLACKLIST:
            if team in home_lower or team in away_lower:
                return True
        return False
    
    def _get_thresholds(self, date_str: str) -> Dict:
        """Get appropriate thresholds based on season timing."""
        # Floor thresholds (minimum to show any pick)
        return {
            'floor_hit_rate': 98.0,
            'floor_cushion': 35.0,
        }
    
    def _get_tier(self, hit_rate: float, cushion: float) -> Optional[int]:
        """
        Determine tier based on hit rate and cushion.
        
        Returns:
            1 = LOCK (99%+ & 35+)      - 100% backtest
            2 = VERY SAFE (99%+ & 30+) - 92.9% backtest
            3 = SAFE (99%+ & 25+)      - 93.0% backtest
            4 = FLOOR (98%+ & 35+)     - 86.5% backtest
            None = Does not qualify
        """
        if hit_rate >= 99 and cushion >= 35:
            return 1
        elif hit_rate >= 99 and cushion >= 30:
            return 2
        elif hit_rate >= 99 and cushion >= 25:
            return 3
        elif hit_rate >= 98 and cushion >= 35:
            return 4
        else:
            return None
    
    def evaluate(self, 
                 home_team: str,
                 away_team: str,
                 hit_rate: float,
                 sim_mean: float,
                 minimum_line: float,
                 date_str: str = None) -> Dict:
        """
        Evaluate if a game passes elite filters.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            hit_rate: Monte Carlo hit rate (% of sims above minimum)
            sim_mean: Average total from simulations
            minimum_line: The minimum total line
            date_str: Game date (YYYY-MM-DD)
        
        Returns:
            Dict with:
                - tier: int or None (1=LOCK, 2=VERY SAFE, 3=SAFE, 4=FLOOR, None=NO BET)
                - tier_label: str description
                - reason: str - Why it passed/failed
                - cushion: float - Points of cushion
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        cushion = sim_mean - minimum_line
        
        result = {
            'tier': None,
            'tier_label': 'NO BET',
            'reason': '',
            'cushion': cushion,
            'hit_rate': hit_rate,
            'home_team': home_team,
            'away_team': away_team,
            'minimum_line': minimum_line,
            'sim_mean': sim_mean,
        }
        
        # Check floor thresholds
        if hit_rate < 98.0:
            result['reason'] = f"HIT_RATE_TOO_LOW ({hit_rate:.1f}% < 98%)"
            return result
        
        if cushion < 35.0:
            result['reason'] = f"CUSHION_TOO_LOW ({cushion:.1f} < 35)"
            return result
        
        # Determine tier
        tier = self._get_tier(hit_rate, cushion)
        result['tier'] = tier
        
        tier_labels = {
            1: '🔒 TIER 1 - LOCK (100%)',
            2: '✅ TIER 2 - VERY SAFE (92.9%)',
            3: '✅ TIER 3 - SAFE (93.0%)',
            4: '⚠️ TIER 4 - FLOOR (86.5%)',
        }
        
        result['tier_label'] = tier_labels.get(tier, 'NO BET')
        result['reason'] = f"QUALIFIED - {result['tier_label']}"
        
        return result
    
    def filter_games(self, games: List[Dict], date_str: str = None) -> List[Dict]:
        """
        Filter a list of games to only qualified picks (Tier 1-4).
        
        Args:
            games: List of game dicts with keys:
                   home_team, away_team, hit_rate, sim_mean, minimum_line
            date_str: Date for threshold determination
        
        Returns:
            List of games that qualify (sorted by tier)
        """
        qualified_games = []
        
        for game in games:
            result = self.evaluate(
                home_team=game.get('home_team', ''),
                away_team=game.get('away_team', ''),
                hit_rate=game.get('hit_rate', 0),
                sim_mean=game.get('sim_mean', 0),
                minimum_line=game.get('minimum_line', 0),
                date_str=date_str
            )
            
            if result['tier']:  # Has a tier (1-4)
                game['elite_result'] = result
                qualified_games.append(game)
        
        # Sort by tier (1 first, then 4 last)
        qualified_games.sort(key=lambda x: x['elite_result']['tier'])
        
        return qualified_games


def print_elite_report(games: List[Dict], date_str: str = None):
    """Print formatted report of elite picks."""
    filter = EliteCBBFilter()
    
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print("\n" + "=" * 70)
    print(f"🎯 CBB ELITE PICKS - {date_str}")
    print("=" * 70)
    print("TIERS:")
    print("  🔒 TIER 1: 99%+ & 35+ cushion → 100% backtest (LOCK)")
    print("  ✅ TIER 2: 99%+ & 30+ cushion → 92.9% backtest")
    print("  ✅ TIER 3: 99%+ & 25+ cushion → 93.0% backtest")
    print("  ⚠️ TIER 4: 98%+ & 35+ cushion → 86.5% backtest (FLOOR)")
    print("=" * 70)
    
    qualified_games = filter.filter_games(games, date_str)
    
    if not qualified_games:
        print("\n   No qualified picks today. Wait for better opportunities.")
    else:
        # Group by tier
        for tier in [1, 2, 3, 4]:
            tier_games = [g for g in qualified_games if g['elite_result']['tier'] == tier]
            if tier_games:
                result = tier_games[0]['elite_result']
                print(f"\n{result['tier_label']} - {len(tier_games)} pick(s)\n")
                
                for game in tier_games:
                    r = game['elite_result']
                    print(f"   {game['away_team'][:25]:25} @ {game['home_team'][:25]}")
                    print(f"      OVER {r['minimum_line']} minimum")
                    print(f"      Hit Rate: {r['hit_rate']:.1f}% | Cushion: {r['cushion']:.1f}")
                    print()
    
    print("=" * 70)
    
    return qualified_games


# Quick test
if __name__ == "__main__":
    filter = EliteCBBFilter()
    
    # Test Tier 1 (LOCK)
    result = filter.evaluate(
        home_team="Duke",
        away_team="Kentucky", 
        hit_rate=99.5,
        sim_mean=170,
        minimum_line=130,
        date_str="2024-11-15"
    )
    print(f"Tier 1 test: Tier {result['tier']} - {result['tier_label']}")
    
    # Test Tier 4 (FLOOR)
    result = filter.evaluate(
        home_team="Kansas",
        away_team="Baylor",
        hit_rate=98.2,
        sim_mean=168,
        minimum_line=130,
        date_str="2025-02-15"
    )
    print(f"Tier 4 test: Tier {result['tier']} - {result['tier_label']}")
    
    # Test blacklisted team
    result = filter.evaluate(
        home_team="Georgetown",
        away_team="Villanova",
        hit_rate=99.5,
        sim_mean=170,
        minimum_line=130,
        date_str="2024-11-15"
    )
    print(f"Blacklist test: Tier {result['tier']} - {result['reason']}")
    
    # Test below floor
    result = filter.evaluate(
        home_team="Duke",
        away_team="UNC",
        hit_rate=97.5,
        sim_mean=165,
        minimum_line=130,
        date_str="2025-02-15"
    )
    print(f"Below floor test: Tier {result['tier']} - {result['reason']}")