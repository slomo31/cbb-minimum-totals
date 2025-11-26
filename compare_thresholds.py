#!/usr/bin/env python3
"""
Compare Thresholds
Analyze predictions at different confidence thresholds (75%, 80%, 85%)
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.season_config import DATA_DIR


def load_predictions():
    """Load predictions from CSV"""
    pred_file = PROJECT_ROOT / DATA_DIR / 'predictions.csv'
    
    if not pred_file.exists():
        print(f"Predictions file not found: {pred_file}")
        print("Run master_workflow.py first")
        return None
    
    return pd.read_csv(pred_file)


def analyze_at_threshold(predictions, threshold):
    """Analyze predictions at a specific threshold"""
    above = predictions[predictions['confidence_pct'] >= threshold]
    
    count = len(above)
    avg_confidence = above['confidence_pct'].mean() if count > 0 else 0
    avg_buffer = above['buffer'].mean() if count > 0 else 0
    
    return {
        'threshold': threshold,
        'count': count,
        'avg_confidence': round(avg_confidence, 1),
        'avg_buffer': round(avg_buffer, 1),
        'picks': above
    }


def compare_thresholds(predictions):
    """Compare predictions across multiple thresholds"""
    thresholds = [75, 80, 85, 90]
    
    print("=" * 70)
    print("THRESHOLD COMPARISON ANALYSIS")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    print(f"\nTotal games analyzed: {len(predictions)}")
    
    print("\n" + "-" * 50)
    print(f"{'Threshold':<12} {'Count':<8} {'Avg Conf':<12} {'Avg Buffer':<12}")
    print("-" * 50)
    
    results = []
    for threshold in thresholds:
        analysis = analyze_at_threshold(predictions, threshold)
        results.append(analysis)
        
        print(f"{threshold}%{'':<9} {analysis['count']:<8} {analysis['avg_confidence']}%{'':<7} {analysis['avg_buffer']:+.1f} pts")
    
    # Detailed breakdown
    print("\n" + "=" * 70)
    print("DETAILED BREAKDOWN BY THRESHOLD")
    print("=" * 70)
    
    for analysis in results:
        threshold = analysis['threshold']
        picks = analysis['picks']
        
        if picks.empty:
            continue
        
        print(f"\n{'='*50}")
        print(f"{threshold}%+ CONFIDENCE PICKS ({analysis['count']} games)")
        print("=" * 50)
        
        for _, pick in picks.iterrows():
            print(f"\n{pick['away_team']} @ {pick['home_team']}")
            print(f"   Min: {pick['minimum_total']} | Expected: {pick['expected_total']} | Buffer: {pick['buffer']:+.1f}")
            print(f"   Confidence: {pick['confidence_pct']:.1f}%")
    
    # Recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    
    # Find the best threshold based on count and quality
    for analysis in results:
        if analysis['threshold'] == 80:
            count_80 = analysis['count']
        if analysis['threshold'] == 85:
            count_85 = analysis['count']
    
    if count_85 >= 3:
        print("\n✅ RECOMMENDED: Use 85% threshold")
        print(f"   You have {count_85} high-confidence picks")
    elif count_80 >= 3:
        print("\n✅ RECOMMENDED: Use 80% threshold")
        print(f"   You have {count_80} picks at this level")
    else:
        print("\n⚠️ WARNING: Limited high-confidence picks today")
        print("   Consider waiting for better opportunities")
    
    return results


def main():
    """Main entry point"""
    predictions = load_predictions()
    
    if predictions is None:
        return
    
    compare_thresholds(predictions)


if __name__ == "__main__":
    main()
