#!/usr/bin/env python3
"""
Standard Line Over/Under Backtest
Uses existing Monte Carlo V3 infrastructure
"""
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path
import csv
import numpy as np

# Import existing Monte Carlo engine
from monte_carlo_cbb_v3 import MonteCarloSimulatorV3

ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"


def fetch_historical_odds(date_str: str) -> list:
    """Fetch historical odds from The Odds API."""
    iso_date = f"{date_str}T12:00:00Z"
    
    url = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'totals',
        'date': iso_date,
        'bookmakers': 'draftkings'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 422:
            return []
        response.raise_for_status()
        data = response.json()
        
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        print(f"   API remaining: {remaining}")
        
        return data.get('data', [])
    except Exception as e:
        print(f"   Odds API error: {e}")
        return []


def fetch_actual_scores(date_str: str) -> dict:
    """Fetch actual scores from NCAA API."""
    ncaa_date = date_str.replace('-', '/')
    url = f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{ncaa_date}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        scores = {}
        for game_wrapper in data.get('games', []):
            game = game_wrapper.get('game', game_wrapper)
            
            if game.get('gameState') != 'final' and game.get('finalMessage') != 'FINAL':
                continue
            
            home = game.get('home', {})
            away = game.get('away', {})
            
            home_name = home.get('names', {}).get('short', '')
            away_name = away.get('names', {}).get('short', '')
            
            try:
                total = int(home.get('score', 0)) + int(away.get('score', 0))
                scores[(home_name, away_name)] = {
                    'total': total,
                    'home_score': int(home.get('score', 0)),
                    'away_score': int(away.get('score', 0)),
                    'home_team': home_name,
                    'away_team': away_name,
                }
            except:
                continue
        
        return scores
    except Exception as e:
        print(f"   Score fetch error: {e}")
        return {}


def evaluate_standard_line(sim: MonteCarloSimulatorV3, home_team: str, away_team: str, 
                           standard_total: float, n_sims: int = 10000) -> dict:
    """Evaluate a game against the standard line using Monte Carlo."""
    
    # Use the existing simulation method
    result = sim.evaluate_game(
        home_team=home_team,
        away_team=away_team,
        minimum_total=standard_total,  # Use standard line as the threshold
        standard_total=standard_total,
        n_simulations=n_sims
    )
    
    # The hit_rate tells us % of sims that went OVER the line
    over_pct = result['hit_rate']
    under_pct = 100 - over_pct
    
    # Determine best side
    if over_pct > under_pct:
        best_side = 'OVER'
        confidence = over_pct
    else:
        best_side = 'UNDER'
        confidence = under_pct
    
    return {
        'best_side': best_side,
        'confidence': confidence,
        'over_pct': over_pct,
        'under_pct': under_pct,
        'sim_mean': result.get('sim_mean', 0),
    }


def run_backtest(season: str):
    """Run standard line backtest."""
    print("=" * 70)
    print(f"🏀 STANDARD LINE O/U BACKTEST - {season} SEASON")
    print("=" * 70)
    
    # Initialize simulator
    sim = MonteCarloSimulatorV3()
    
    # Date range
    if season == "2024-25":
        start_date = datetime(2024, 11, 4)
        end_date = datetime(2025, 4, 7)
    else:  # 2025-26
        start_date = datetime(2025, 11, 4)
        end_date = datetime.now() - timedelta(days=1)
    
    # Results
    all_results = []
    yes_picks = {'wins': 0, 'losses': 0, 'over_w': 0, 'over_l': 0, 'under_w': 0, 'under_l': 0}
    maybe_picks = {'wins': 0, 'losses': 0}
    
    current_date = start_date
    day_count = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n📅 {date_str}")
        
        # Fetch odds
        odds_data = fetch_historical_odds(date_str)
        if not odds_data:
            current_date += timedelta(days=1)
            continue
        
        # Parse games with standard totals
        games = []
        for game in odds_data:
            game_info = {
                'home_team': game.get('home_team', ''),
                'away_team': game.get('away_team', ''),
            }
            
            for bm in game.get('bookmakers', []):
                for market in bm.get('markets', []):
                    if market.get('key') == 'totals':
                        for outcome in market.get('outcomes', []):
                            if outcome.get('name') == 'Over':
                                game_info['standard_total'] = outcome.get('point')
                                game_info['over_odds'] = outcome.get('price')
                            elif outcome.get('name') == 'Under':
                                game_info['under_odds'] = outcome.get('price')
            
            if game_info.get('standard_total'):
                games.append(game_info)
        
        # Fetch scores
        scores = fetch_actual_scores(date_str)
        
        print(f"   {len(games)} games with odds, {len(scores)} with scores")
        
        # Evaluate each game
        for game in games:
            eval_result = evaluate_standard_line(
                sim,
                game['home_team'],
                game['away_team'],
                float(game['standard_total'])
            )
            
            # Find actual score - try to match team names
            actual = None
            odds_home = game['home_team'].lower()
            odds_away = game['away_team'].lower()
            
            for (score_home, score_away), score_data in scores.items():
                # Check if team names match (partial matching)
                home_match = (odds_home in score_home.lower() or 
                             score_home.lower() in odds_home or
                             odds_home.split()[-1] in score_home.lower())
                away_match = (odds_away in score_away.lower() or 
                             score_away.lower() in odds_away or
                             odds_away.split()[-1] in score_away.lower())
                
                if home_match and away_match:
                    actual = score_data
                    break
            
            if actual:
                actual_total = actual['total']
                standard = float(game['standard_total'])
                
                # Did the bet win?
                if eval_result['best_side'] == 'OVER':
                    hit = actual_total > standard
                else:
                    hit = actual_total < standard
                
                # Determine decision based on confidence
                if eval_result['confidence'] >= 95:
                    decision = 'YES'
                elif eval_result['confidence'] >= 85:
                    decision = 'MAYBE'
                else:
                    decision = 'NO'
                
                result_row = {
                    'date': date_str,
                    'away': game['away_team'],
                    'home': game['home_team'],
                    'standard_total': standard,
                    'actual_total': actual_total,
                    'best_side': eval_result['best_side'],
                    'confidence': eval_result['confidence'],
                    'decision': decision,
                    'hit': hit,
                    'margin': actual_total - standard,
                }
                all_results.append(result_row)
                
                # Track results
                if decision == 'YES':
                    if hit:
                        yes_picks['wins'] += 1
                        if eval_result['best_side'] == 'OVER':
                            yes_picks['over_w'] += 1
                        else:
                            yes_picks['under_w'] += 1
                    else:
                        yes_picks['losses'] += 1
                        if eval_result['best_side'] == 'OVER':
                            yes_picks['over_l'] += 1
                        else:
                            yes_picks['under_l'] += 1
                elif decision == 'MAYBE':
                    if hit:
                        maybe_picks['wins'] += 1
                    else:
                        maybe_picks['losses'] += 1
        
        day_count += 1
        
        # Progress
        if day_count % 10 == 0:
            total_yes = yes_picks['wins'] + yes_picks['losses']
            pct = yes_picks['wins'] / total_yes * 100 if total_yes > 0 else 0
            print(f"   📊 Progress: {day_count} days, {total_yes} YES, {yes_picks['wins']}-{yes_picks['losses']} ({pct:.1f}%)")
        
        current_date += timedelta(days=1)
    
    # Final results
    print("\n" + "=" * 70)
    print("📊 FINAL RESULTS")
    print("=" * 70)
    
    total_yes = yes_picks['wins'] + yes_picks['losses']
    total_maybe = maybe_picks['wins'] + maybe_picks['losses']
    
    print(f"\nDates tested: {day_count}")
    print(f"Total games analyzed: {len(all_results)}")
    
    if total_yes > 0:
        pct = yes_picks['wins'] / total_yes * 100
        print(f"\n🟢 YES PICKS (95%+ confidence): {total_yes}")
        print(f"   Record: {yes_picks['wins']}-{yes_picks['losses']} ({pct:.1f}%)")
        print(f"   OVER:  {yes_picks['over_w']}-{yes_picks['over_l']}")
        print(f"   UNDER: {yes_picks['under_w']}-{yes_picks['under_l']}")
        
        # Profitability at -110
        profit = (yes_picks['wins'] * 100) - (yes_picks['losses'] * 110)
        roi = profit / (total_yes * 110) * 100
        print(f"\n💰 At -110 odds:")
        print(f"   Net: {profit/100:+.1f} units")
        print(f"   ROI: {roi:+.1f}%")
    
    if total_maybe > 0:
        pct = maybe_picks['wins'] / total_maybe * 100
        print(f"\n🟡 MAYBE PICKS (90-95%): {total_maybe}")
        print(f"   Record: {maybe_picks['wins']}-{maybe_picks['losses']} ({pct:.1f}%)")
    
    # Show losses
    yes_results = [r for r in all_results if r['decision'] == 'YES']
    losses = [r for r in yes_results if not r['hit']]
    if losses:
        print(f"\n❌ YES PICK LOSSES ({len(losses)}):")
        print("-" * 70)
        for r in losses[:15]:
            print(f"   {r['date']}: {r['away'][:18]} @ {r['home'][:18]}")
            print(f"      {r['best_side']} {r['standard_total']} | Actual: {r['actual_total']} | Conf: {r['confidence']:.1f}%")
    
    # Save
    output_file = f"standard_backtest_{season.replace('-', '_')}.csv"
    with open(output_file, 'w', newline='') as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    season = sys.argv[1] if len(sys.argv) > 1 else "2025-26"
    run_backtest(season)