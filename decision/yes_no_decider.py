"""
YES/NO Decision Maker
Makes final betting decisions based on predictions
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import CONFIDENCE_THRESHOLDS, BANKROLL_ALLOCATION, DATA_DIR


class YesNoDecider:
    """Makes final YES/MAYBE/NO decisions on predictions"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / DATA_DIR
        self.output_dir = Path(__file__).parent.parent / "output_archive" / "decisions"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def evaluate_predictions(self, predictions_df=None):
        """Evaluate predictions and make decisions"""
        if predictions_df is None:
            pred_file = self.data_dir / "predictions.csv"
            if pred_file.exists():
                predictions_df = pd.read_csv(pred_file)
            else:
                print("No predictions file found")
                return pd.DataFrame()
        
        if predictions_df.empty:
            return pd.DataFrame()
        
        # Group by decision
        yes_picks = predictions_df[predictions_df['decision'] == 'YES'].copy()
        maybe_picks = predictions_df[predictions_df['decision'] == 'MAYBE'].copy()
        no_picks = predictions_df[predictions_df['decision'] == 'NO'].copy()
        
        # Print report
        print("\n" + "=" * 70)
        print("🏀 CBB MINIMUM TOTALS - BETTING DECISIONS")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        
        # YES picks
        if not yes_picks.empty:
            print(f"\n🟢 YES PICKS ({len(yes_picks)}) - Bet 3% each")
            print("-" * 50)
            for _, pick in yes_picks.sort_values('confidence_pct', ascending=False).iterrows():
                away = pick.get('away_team', 'Unknown')
                home = pick.get('home_team', 'Unknown')
                minimum = pick.get('minimum_total', 0)
                expected = pick.get('expected_total', 0)
                conf = pick.get('confidence_pct', 0)
                print(f"\n  {away} @ {home}")
                print(f"  📊 OVER {minimum} | Expected: {expected} | Conf: {conf:.0f}%")
        
        # MAYBE picks
        if not maybe_picks.empty:
            print(f"\n🟡 MAYBE PICKS ({len(maybe_picks)}) - Consider 2%")
            print("-" * 50)
            for _, pick in maybe_picks.sort_values('confidence_pct', ascending=False).iterrows():
                away = pick.get('away_team', 'Unknown')
                home = pick.get('home_team', 'Unknown')
                minimum = pick.get('minimum_total', 0)
                conf = pick.get('confidence_pct', 0)
                print(f"  {away} @ {home} - OVER {minimum} ({conf:.0f}%)")
        
        # NO picks
        if not no_picks.empty:
            print(f"\n🔴 NO PICKS ({len(no_picks)}) - Skip")
            print("-" * 50)
            for _, pick in no_picks.iterrows():
                away = pick.get('away_team', 'Unknown')
                home = pick.get('home_team', 'Unknown')
                minimum = pick.get('minimum_total', 0)
                conf = pick.get('confidence_pct', 0)
                print(f"  {away} @ {home} - OVER {minimum} ({conf:.0f}%)")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print(f"   YES: {len(yes_picks)} picks (bet 3% each)")
        print(f"   MAYBE: {len(maybe_picks)} picks (consider 2% each)")
        print(f"   NO: {len(no_picks)} picks (skip)")
        print("=" * 70)
        
        # Save decisions
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_file = self.output_dir / f"decisions_{date_str}.csv"
        predictions_df.to_csv(output_file, index=False)
        print(f"\n✅ Saved to {output_file}")
        
        return predictions_df


def main():
    decider = YesNoDecider()
    decider.evaluate_predictions()


if __name__ == "__main__":
    main()
