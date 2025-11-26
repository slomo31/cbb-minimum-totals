"""
Historical Backtester for CBB Minimum Totals
Tests the system against completed games from this season
"""

import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CURRENT_SEASON, DATA_DIR


class HistoricalBacktester:
    """
    Backtest minimum totals strategy against completed games
    
    Since we don't have historical alternate totals, we simulate them
    based on actual game totals and standard line relationships.
    """
    
    ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.completed_games = []
        self.backtest_results = []
    
    def fetch_completed_games(self, days_back=30):
        """Fetch completed games from ESPN"""
        print(f"Fetching completed games from last {days_back} days...")
        
        all_games = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y%m%d")
            
            try:
                url = f"{self.ESPN_BASE}/scoreboard?dates={date_str}"
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for event in data.get('events', []):
                        status = event.get('status', {}).get('type', {}).get('name', '')
                        
                        if status != 'STATUS_FINAL':
                            continue
                        
                        competition = event.get('competitions', [{}])[0]
                        competitors = competition.get('competitors', [])
                        
                        if len(competitors) != 2:
                            continue
                        
                        home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
                        away = next((c for c in competitors if c.get('homeAway') == 'away'), {})
                        
                        home_score = int(home.get('score', 0))
                        away_score = int(away.get('score', 0))
                        
                        if home_score == 0 or away_score == 0:
                            continue
                        
                        game = {
                            'game_id': event.get('id'),
                            'game_date': current.strftime('%Y-%m-%d'),
                            'home_team': home.get('team', {}).get('displayName', ''),
                            'away_team': away.get('team', {}).get('displayName', ''),
                            'home_score': home_score,
                            'away_score': away_score,
                            'actual_total': home_score + away_score
                        }
                        all_games.append(game)
                
            except Exception as e:
                print(f"Error fetching {date_str}: {e}")
            
            current += timedelta(days=1)
        
        self.completed_games = all_games
        print(f"Found {len(all_games)} completed games")
        return all_games
    
    def simulate_betting_lines(self, games):
        """
        Simulate what the betting lines would have been
        
        Based on our observations:
        - Standard total is usually close to actual (within ±5-10 points)
        - Minimum alternate is typically 10-12 points below standard
        """
        print("\nSimulating betting lines...")
        
        for game in games:
            actual = game['actual_total']
            
            # Simulate standard total (actual ± some variance)
            # Vegas is usually within 5-8 points of actual
            variance = np.random.normal(0, 4)  # Small random variance
            simulated_standard = round(actual + variance, 0) + 0.5
            
            # Minimum alternate is typically 10-12 points below standard
            # Based on real data: minimums are ~8-12% below standard
            min_offset = np.random.uniform(10, 14)  # 10-14 points below
            simulated_minimum = simulated_standard - min_offset
            
            game['simulated_standard'] = simulated_standard
            game['simulated_minimum'] = round(simulated_minimum, 1)
            game['buffer'] = round(simulated_standard - simulated_minimum, 1)
        
        return games
    
    def run_predictions(self, games):
        """Run our prediction logic on historical games"""
        print("\nRunning predictions on historical games...")
        
        results = []
        
        for game in games:
            minimum = game['simulated_minimum']
            actual = game['actual_total']
            standard = game['simulated_standard']
            
            # Calculate expected total (use standard as proxy)
            expected = standard + 2  # Home court adjustment
            
            # Calculate buffer
            buffer = expected - minimum
            
            # Calculate confidence (same logic as predictor)
            if buffer >= 20:
                confidence = 92
            elif buffer >= 15:
                confidence = 87
            elif buffer >= 12:
                confidence = 83
            elif buffer >= 10:
                confidence = 80
            elif buffer >= 8:
                confidence = 77
            elif buffer >= 5:
                confidence = 73
            elif buffer >= 3:
                confidence = 68
            else:
                confidence = 60 + buffer * 2
            
            confidence = max(50, min(95, confidence))
            
            # Make decision
            if confidence >= 80:
                decision = 'YES'
            elif confidence >= 75:
                decision = 'MAYBE'
            else:
                decision = 'NO'
            
            # Check result
            went_over = actual > minimum
            result = 'WIN' if went_over else 'LOSS'
            
            results.append({
                **game,
                'expected_total': expected,
                'buffer': buffer,
                'confidence': confidence,
                'decision': decision,
                'went_over': went_over,
                'result': result
            })
        
        self.backtest_results = results
        return results
    
    def analyze_results(self, results):
        """Analyze backtest results"""
        df = pd.DataFrame(results)
        
        print("\n" + "=" * 70)
        print("📊 BACKTEST RESULTS")
        print("=" * 70)
        
        print(f"\nTotal games analyzed: {len(df)}")
        
        # Overall hit rate on OVER
        overall_over = len(df[df['went_over'] == True])
        overall_rate = overall_over / len(df) * 100
        print(f"Games that went OVER minimum: {overall_over}/{len(df)} ({overall_rate:.1f}%)")
        
        # Results by decision
        print("\n📈 RESULTS BY DECISION:")
        print("-" * 50)
        
        for decision in ['YES', 'MAYBE', 'NO']:
            subset = df[df['decision'] == decision]
            if len(subset) == 0:
                continue
            
            wins = len(subset[subset['result'] == 'WIN'])
            losses = len(subset[subset['result'] == 'LOSS'])
            win_rate = wins / len(subset) * 100
            
            icon = '🟢' if decision == 'YES' else '🟡' if decision == 'MAYBE' else '🔴'
            status = '✅ PASS' if (decision == 'YES' and win_rate >= 85) or (decision == 'NO' and win_rate < 70) else '⚠️'
            
            print(f"\n{icon} {decision} PICKS:")
            print(f"   Record: {wins}-{losses} ({win_rate:.1f}%)")
            print(f"   Count: {len(subset)} games")
            print(f"   Avg Confidence: {subset['confidence'].mean():.1f}%")
            print(f"   Avg Buffer: {subset['buffer'].mean():.1f} points")
            print(f"   Status: {status}")
        
        # Results by confidence threshold
        print("\n📊 RESULTS BY CONFIDENCE THRESHOLD:")
        print("-" * 50)
        
        thresholds = [95, 90, 85, 80, 75, 70]
        for thresh in thresholds:
            subset = df[df['confidence'] >= thresh]
            if len(subset) == 0:
                continue
            wins = len(subset[subset['result'] == 'WIN'])
            win_rate = wins / len(subset) * 100
            print(f"   ≥{thresh}%: {wins}/{len(subset)} ({win_rate:.1f}%)")
        
        # Detailed breakdown
        print("\n📋 SAMPLE RESULTS (Last 15 games):")
        print("-" * 70)
        
        sample = df.tail(15)
        for _, game in sample.iterrows():
            icon = '✅' if game['result'] == 'WIN' else '❌'
            print(f"{icon} {game['away_team'][:20]} @ {game['home_team'][:20]}")
            print(f"   Min: {game['simulated_minimum']} | Actual: {game['actual_total']} | Conf: {game['confidence']:.0f}% | {game['decision']}")
        
        # Save results
        output_file = self.data_dir.parent / "output_archive" / "backtests" / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"\n✅ Saved detailed results to {output_file}")
        
        # Also save for ML training
        ml_file = self.data_dir / "backtest_for_ml.csv"
        df.to_csv(ml_file, index=False)
        print(f"✅ Saved ML training data to {ml_file}")
        
        return df
    
    def run_full_backtest(self, days_back=30):
        """Run complete backtest"""
        print("=" * 70)
        print("🏀 CBB MINIMUM TOTALS - HISTORICAL BACKTEST")
        print(f"   Testing last {days_back} days of games")
        print("=" * 70)
        
        # Fetch games
        games = self.fetch_completed_games(days_back)
        
        if not games:
            print("❌ No completed games found")
            return None
        
        # Simulate lines
        games = self.simulate_betting_lines(games)
        
        # Run predictions
        results = self.run_predictions(games)
        
        # Analyze
        df = self.analyze_results(results)
        
        return df


def main():
    backtester = HistoricalBacktester()
    
    # Run backtest on last 30 days
    results = backtester.run_full_backtest(days_back=30)
    
    if results is not None:
        print("\n" + "=" * 70)
        print("🎯 BACKTEST COMPLETE")
        print("=" * 70)
        
        # Summary stats
        yes_picks = results[results['decision'] == 'YES']
        if len(yes_picks) > 0:
            yes_wins = len(yes_picks[yes_picks['result'] == 'WIN'])
            yes_rate = yes_wins / len(yes_picks) * 100
            
            print(f"\n🎯 YES PICK ACCURACY: {yes_wins}/{len(yes_picks)} ({yes_rate:.1f}%)")
            
            if yes_rate >= 85:
                print("   ✅ TARGET MET (85%+)")
            elif yes_rate >= 80:
                print("   ⚠️ CLOSE TO TARGET (80-85%)")
            else:
                print("   ❌ BELOW TARGET (<80%) - Consider ML enhancement")


if __name__ == "__main__":
    main()
