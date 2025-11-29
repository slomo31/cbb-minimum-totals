#!/usr/bin/env python3
"""
CBB MAXIMUM TOTALS - ELITE FILTER V1
=====================================
PARLAY FUEL SYSTEM - UNDERS EDITION

Looking for games where teams are EXTREMELY UNLIKELY to exceed
alternate maximum lines (standard + 12).

BACKTEST RESULTS (1,390 games):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TIER 1 🔒 Sim ≥ 155 & HR 80-85%  →  106-10 (91.4%)  BEST
TIER 2 ✅ Sim ≥ 160 & HR 80-88%  →  56-9  (86.2%)   SAFE
TIER 3 ⚠️ Max line ≥ 165        →  150-18 (89.3%)  VOLUME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Key insight: Higher hit rates actually perform WORSE for unders.
The sweet spot is 80-85% hit rate with higher expected totals.

Losses typically come from blowouts (weak team vs strong team).

Usage:
    from elite_cbb_max_v1 import EliteCBBMaxFilter
    
    filter = EliteCBBMaxFilter()
    result = filter.evaluate(sim_result, maximum_line)
"""

from datetime import datetime
from typing import Dict, List, Optional


class EliteCBBMaxFilter:
    """
    Elite filter for CBB maximum totals (unders).
    Only passes games that meet strict criteria for parlay safety.
    
    Key finding from backtest: Lower hit rates (80-85%) with higher
    sim_mean actually perform BETTER than high hit rates.
    """
    
    # Teams/matchups that tend to blow up unders (blowout risk)
    BLOWOUT_RISK_TEAMS = [
        # SWAC/MEAC (get blown out by P5)
        'alabama a&m', 'alabama st', 'alcorn', 'ark.-pine bluff', 
        'bethune-cookman', 'coppin st', 'delaware st', 'famu',
        'grambling', 'jackson st', 'mississippi valley', 'norfolk st',
        'prairie view', 'southern', 'texas southern',
        # Other high-variance small schools
        'central st', 'bethel', 'chaminade',
    ]
    
    def __init__(self):
        """Initialize filter with backtested thresholds."""
        pass
    
    def _is_blowout_risk(self, home_team: str, away_team: str) -> bool:
        """Check if matchup has high blowout risk."""
        home_lower = home_team.lower()
        away_lower = away_team.lower()
        
        for team in self.BLOWOUT_RISK_TEAMS:
            if team in away_lower:  # Weak away team = blowout risk
                return True
        return False
    
    def _get_tier(self, under_hit_rate: float, sim_mean: float, maximum_line: float) -> Optional[int]:
        """
        Determine tier based on backtested criteria.
        
        Key insight: For unders, we want MODERATE hit rates (80-85%)
        with HIGHER sim_mean. This indicates a game expected to be
        high-scoring but with natural variance keeping it under max.
        
        Returns:
            1 = BEST (91.4% backtest) - Sim ≥ 155 & HR 80-85%
            2 = SAFE (86.2% backtest) - Sim ≥ 160 & HR 80-88%
            3 = VOLUME (89.3% backtest) - Max line ≥ 165
            None = Does not qualify
        """
        # Tier 1: Best performing filter
        if sim_mean >= 155 and 80 <= under_hit_rate <= 85:
            return 1
        
        # Tier 2: Safe filter
        if sim_mean >= 160 and 80 <= under_hit_rate <= 88:
            return 2
        
        # Tier 3: Volume filter
        if maximum_line >= 165 and under_hit_rate >= 80:
            return 3
        
        return None
    
    def evaluate(self, 
                 home_team: str,
                 away_team: str,
                 under_hit_rate: float,
                 sim_mean: float,
                 maximum_line: float,
                 date_str: str = None) -> Dict:
        """
        Evaluate if a game passes elite filters for UNDER bet.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            under_hit_rate: Monte Carlo hit rate (% of sims UNDER maximum)
            sim_mean: Average total from simulations
            maximum_line: The maximum total line (standard + 12)
            date_str: Game date (YYYY-MM-DD)
        
        Returns:
            Dict with tier, reason, cushion, etc.
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # For unders, cushion = max_line - sim_mean
        cushion = maximum_line - sim_mean
        
        result = {
            'tier': None,
            'tier_label': 'NO BET',
            'reason': '',
            'cushion': cushion,
            'hit_rate': under_hit_rate,
            'home_team': home_team,
            'away_team': away_team,
            'maximum_line': maximum_line,
            'sim_mean': sim_mean,
        }
        
        # Check blowout risk
        if self._is_blowout_risk(home_team, away_team):
            result['reason'] = 'BLOWOUT_RISK'
            return result
        
        # Check floor thresholds
        if under_hit_rate < 80:
            result['reason'] = f"HIT_RATE_TOO_LOW ({under_hit_rate:.1f}% < 80%)"
            return result
        
        if under_hit_rate > 90:
            result['reason'] = f"HIT_RATE_TOO_HIGH ({under_hit_rate:.1f}% > 90% - paradoxically worse)"
            return result
        
        # Determine tier
        tier = self._get_tier(under_hit_rate, sim_mean, maximum_line)
        
        if tier is None:
            if sim_mean < 155:
                result['reason'] = f"SIM_MEAN_TOO_LOW ({sim_mean:.1f} < 155)"
            else:
                result['reason'] = f"NO_TIER_MATCH"
            return result
        
        result['tier'] = tier
        
        tier_labels = {
            1: '🔒 TIER 1 - BEST (91.4%)',
            2: '✅ TIER 2 - SAFE (86.2%)',
            3: '⚠️ TIER 3 - VOLUME (89.3%)',
        }
        
        result['tier_label'] = tier_labels.get(tier, 'NO BET')
        result['reason'] = f"QUALIFIED - {result['tier_label']}"
        
        return result
    
    def filter_games(self, games: List[Dict], date_str: str = None) -> List[Dict]:
        """
        Filter a list of games to only qualified picks.
        """
        qualified_games = []
        
        for game in games:
            result = self.evaluate(
                home_team=game.get('home_team', ''),
                away_team=game.get('away_team', ''),
                under_hit_rate=game.get('under_hit_rate', 0),
                sim_mean=game.get('sim_mean', 0),
                maximum_line=game.get('maximum_line', 0),
                date_str=date_str
            )
            
            if result['tier']:
                game['elite_result'] = result
                qualified_games.append(game)
        
        # Sort by tier
        qualified_games.sort(key=lambda x: x['elite_result']['tier'])
        
        return qualified_games


# Quick test
if __name__ == "__main__":
    filter = EliteCBBMaxFilter()
    
    # Test Tier 1 scenario
    result = filter.evaluate(
        home_team="Kansas",
        away_team="Duke",
        under_hit_rate=83.0,
        sim_mean=158,
        maximum_line=170,
        date_str="2024-11-15"
    )
    print(f"Tier 1 test: Tier {result['tier']} - {result['tier_label']}")
    
    # Test blowout risk
    result = filter.evaluate(
        home_team="Kentucky",
        away_team="Jackson St",
        under_hit_rate=82.0,
        sim_mean=160,
        maximum_line=172,
        date_str="2024-11-15"
    )
    print(f"Blowout risk test: Tier {result['tier']} - {result['reason']}")
    
    # Test hit rate too high (paradoxically bad)
    result = filter.evaluate(
        home_team="Duke",
        away_team="UNC",
        under_hit_rate=95.0,
        sim_mean=165,
        maximum_line=177,
        date_str="2024-11-15"
    )
    print(f"High HR test: Tier {result['tier']} - {result['reason']}")