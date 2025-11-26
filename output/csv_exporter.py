#!/usr/bin/env python3
"""
CSV Exporter
Export predictions and results to various CSV formats
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.season_config import DATA_DIR, OUTPUT_ARCHIVE_DIR


class CSVExporter:
    """Export data to CSV files"""
    
    def __init__(self):
        self.data_dir = PROJECT_ROOT / DATA_DIR
        self.output_dir = PROJECT_ROOT / 'output'
        self.archive_dir = PROJECT_ROOT / OUTPUT_ARCHIVE_DIR
        
        self.output_dir.mkdir(exist_ok=True)
    
    def export_predictions(self, predictions_df, filename=None):
        """Export predictions to CSV"""
        if filename is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f'predictions_{date_str}.csv'
        
        output_path = self.output_dir / filename
        predictions_df.to_csv(output_path, index=False)
        print(f"Exported predictions to {output_path}")
        return output_path
    
    def export_yes_picks(self, predictions_df, filename=None):
        """Export only YES picks"""
        yes_picks = predictions_df[predictions_df['decision'] == 'YES']
        
        if filename is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f'yes_picks_{date_str}.csv'
        
        output_path = self.output_dir / filename
        
        # Select key columns
        columns = [
            'home_team', 'away_team', 'game_date', 'game_time',
            'minimum_total', 'expected_total', 'buffer', 'confidence_pct'
        ]
        
        export_df = yes_picks[[c for c in columns if c in yes_picks.columns]]
        export_df.to_csv(output_path, index=False)
        print(f"Exported {len(yes_picks)} YES picks to {output_path}")
        return output_path
    
    def export_tracking_summary(self, tracking_df, filename=None):
        """Export tracking summary"""
        if filename is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f'tracking_summary_{date_str}.csv'
        
        # Calculate summary stats
        summary = []
        
        for decision in ['YES', 'MAYBE']:
            subset = tracking_df[tracking_df['decision'] == decision]
            wins = len(subset[subset['result'] == 'WIN'])
            losses = len(subset[subset['result'] == 'LOSS'])
            pending = len(subset[subset['result'] == 'PENDING'])
            
            summary.append({
                'decision_type': decision,
                'total': len(subset),
                'wins': wins,
                'losses': losses,
                'pending': pending,
                'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
                'record': f"{wins}-{losses}"
            })
        
        summary_df = pd.DataFrame(summary)
        output_path = self.output_dir / filename
        summary_df.to_csv(output_path, index=False)
        print(f"Exported tracking summary to {output_path}")
        return output_path
    
    def export_for_betting(self, predictions_df, include_maybe=False):
        """Export formatted for actual betting"""
        picks = predictions_df[predictions_df['decision'] == 'YES'].copy()
        
        if include_maybe:
            maybe = predictions_df[predictions_df['decision'] == 'MAYBE']
            picks = pd.concat([picks, maybe])
        
        betting_df = pd.DataFrame({
            'Matchup': picks['away_team'] + ' @ ' + picks['home_team'],
            'Bet Type': 'OVER',
            'Line': picks['minimum_total'],
            'Expected Total': picks['expected_total'],
            'Buffer': picks['buffer'],
            'Confidence': picks['confidence_pct'].apply(lambda x: f"{x:.1f}%"),
            'Decision': picks['decision'],
            'Bet Size': picks['decision'].apply(lambda x: '3%' if x == 'YES' else '2%')
        })
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f'betting_sheet_{date_str}.csv'
        output_path = self.output_dir / filename
        betting_df.to_csv(output_path, index=False)
        print(f"Exported betting sheet to {output_path}")
        return output_path
    
    def export_daily_report(self, predictions_df, tracking_df=None):
        """Export comprehensive daily report"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Export all formats
        self.export_predictions(predictions_df)
        self.export_yes_picks(predictions_df)
        self.export_for_betting(predictions_df)
        
        if tracking_df is not None:
            self.export_tracking_summary(tracking_df)
        
        print(f"\nDaily report exported for {date_str}")


def main():
    """Test the CSV exporter"""
    exporter = CSVExporter()
    
    # Try to load existing predictions
    pred_file = exporter.data_dir / 'predictions.csv'
    
    if pred_file.exists():
        predictions = pd.read_csv(pred_file)
        print(f"Loaded {len(predictions)} predictions")
        
        # Export all formats
        exporter.export_daily_report(predictions)
    else:
        print("No predictions file found")
        print("Run master_workflow.py first")


if __name__ == "__main__":
    main()
