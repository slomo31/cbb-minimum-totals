#!/usr/bin/env python3
"""
Generate Dashboard
Creates an HTML dashboard for tracking CBB minimum totals performance
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.season_config import DATA_DIR, OUTPUT_ARCHIVE_DIR


def get_tracking_stats():
    """Get tracking statistics"""
    tracking_file = PROJECT_ROOT / OUTPUT_ARCHIVE_DIR / 'decisions' / 'tracking_results.csv'
    
    if not tracking_file.exists():
        return None, None
    
    df = pd.read_csv(tracking_file)
    
    # Calculate stats
    yes_df = df[df['decision'] == 'YES']
    maybe_df = df[df['decision'] == 'MAYBE']
    
    yes_wins = len(yes_df[yes_df['result'] == 'WIN'])
    yes_losses = len(yes_df[yes_df['result'] == 'LOSS'])
    yes_pending = len(yes_df[yes_df['result'] == 'PENDING'])
    
    maybe_wins = len(maybe_df[maybe_df['result'] == 'WIN'])
    maybe_losses = len(maybe_df[maybe_df['result'] == 'LOSS'])
    maybe_pending = len(maybe_df[maybe_df['result'] == 'PENDING'])
    
    total_wins = yes_wins + maybe_wins
    total_losses = yes_losses + maybe_losses
    
    stats = {
        'yes_record': f"{yes_wins}-{yes_losses}",
        'yes_pending': yes_pending,
        'yes_win_rate': (yes_wins / (yes_wins + yes_losses) * 100) if (yes_wins + yes_losses) > 0 else 0,
        'maybe_record': f"{maybe_wins}-{maybe_losses}",
        'maybe_pending': maybe_pending,
        'maybe_win_rate': (maybe_wins / (maybe_wins + maybe_losses) * 100) if (maybe_wins + maybe_losses) > 0 else 0,
        'total_record': f"{total_wins}-{total_losses}",
        'total_pending': yes_pending + maybe_pending,
        'total_win_rate': (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
    }
    
    return stats, df


def get_todays_picks():
    """Get today's predictions"""
    pred_file = PROJECT_ROOT / DATA_DIR / 'predictions.csv'
    
    if not pred_file.exists():
        return None
    
    df = pd.read_csv(pred_file)
    return df


def generate_html():
    """Generate HTML dashboard"""
    stats, tracking_df = get_tracking_stats()
    predictions = get_todays_picks()
    
    # Build HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CBB Minimum Totals Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            padding: 30px 0;
        }
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00ff88, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .timestamp {
            color: #888;
            font-size: 0.9em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stat-card h3 {
            color: #888;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
        }
        .stat-value {
            font-size: 3em;
            font-weight: bold;
        }
        .stat-value.green { color: #00ff88; }
        .stat-value.yellow { color: #ffd700; }
        .stat-value.blue { color: #00d4ff; }
        .win-rate {
            font-size: 1.2em;
            color: #888;
            margin-top: 10px;
        }
        .pending {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        .section {
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 25px;
            margin: 30px 0;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .section h2 {
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .picks-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .pick-card {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid;
        }
        .pick-card.yes { border-color: #00ff88; }
        .pick-card.maybe { border-color: #ffd700; }
        .pick-card.win { border-color: #00ff88; background: rgba(0,255,136,0.1); }
        .pick-card.loss { border-color: #ff4444; background: rgba(255,68,68,0.1); }
        .pick-card .matchup {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .pick-card .details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            font-size: 0.9em;
            color: #aaa;
        }
        .pick-card .confidence {
            font-weight: bold;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge.yes { background: #00ff88; color: #000; }
        .badge.maybe { background: #ffd700; color: #000; }
        .badge.win { background: #00ff88; color: #000; }
        .badge.loss { background: #ff4444; color: #fff; }
        .badge.pending { background: #666; color: #fff; }
        footer {
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 0.9em;
        }
        @media (max-width: 600px) {
            header h1 { font-size: 1.8em; }
            .stat-value { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏀 CBB Minimum Totals</h1>
            <p class="timestamp">Last Updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        </header>
"""
    
    # Stats cards
    if stats:
        html += """
        <div class="stats-grid">
            <div class="stat-card">
                <h3>🟢 YES Picks (80%+)</h3>
                <div class="stat-value green">""" + stats['yes_record'] + """</div>
                <div class="win-rate">""" + f"{stats['yes_win_rate']:.1f}% Win Rate" + """</div>
                <div class="pending">""" + f"{stats['yes_pending']} pending" + """</div>
            </div>
            <div class="stat-card">
                <h3>🟡 MAYBE Picks (75-79%)</h3>
                <div class="stat-value yellow">""" + stats['maybe_record'] + """</div>
                <div class="win-rate">""" + f"{stats['maybe_win_rate']:.1f}% Win Rate" + """</div>
                <div class="pending">""" + f"{stats['maybe_pending']} pending" + """</div>
            </div>
            <div class="stat-card">
                <h3>📊 Combined Total</h3>
                <div class="stat-value blue">""" + stats['total_record'] + """</div>
                <div class="win-rate">""" + f"{stats['total_win_rate']:.1f}% Win Rate" + """</div>
                <div class="pending">""" + f"{stats['total_pending']} total pending" + """</div>
            </div>
        </div>
"""
    
    # Today's picks
    if predictions is not None and not predictions.empty:
        yes_picks = predictions[predictions['decision'] == 'YES']
        maybe_picks = predictions[predictions['decision'] == 'MAYBE']
        
        if not yes_picks.empty:
            html += """
        <div class="section">
            <h2>🟢 Today's YES Picks</h2>
            <div class="picks-list">
"""
            for _, pick in yes_picks.iterrows():
                html += f"""
                <div class="pick-card yes">
                    <div class="matchup">{pick['away_team']} @ {pick['home_team']}</div>
                    <div class="details">
                        <div>Min Total: <strong>{pick['minimum_total']}</strong></div>
                        <div>Expected: <strong>{pick['expected_total']}</strong></div>
                        <div>Buffer: <strong>{pick['buffer']:+.1f}</strong></div>
                        <div class="confidence">Confidence: <span class="badge yes">{pick['confidence_pct']:.1f}%</span></div>
                    </div>
                </div>
"""
            html += """
            </div>
        </div>
"""
        
        if not maybe_picks.empty:
            html += """
        <div class="section">
            <h2>🟡 Today's MAYBE Picks</h2>
            <div class="picks-list">
"""
            for _, pick in maybe_picks.iterrows():
                html += f"""
                <div class="pick-card maybe">
                    <div class="matchup">{pick['away_team']} @ {pick['home_team']}</div>
                    <div class="details">
                        <div>Min Total: <strong>{pick['minimum_total']}</strong></div>
                        <div>Expected: <strong>{pick['expected_total']}</strong></div>
                        <div>Buffer: <strong>{pick['buffer']:+.1f}</strong></div>
                        <div class="confidence">Confidence: <span class="badge maybe">{pick['confidence_pct']:.1f}%</span></div>
                    </div>
                </div>
"""
            html += """
            </div>
        </div>
"""
    
    # Recent results
    if tracking_df is not None:
        recent = tracking_df[tracking_df['result'] != 'PENDING'].tail(10)
        if not recent.empty:
            html += """
        <div class="section">
            <h2>📋 Recent Results</h2>
            <div class="picks-list">
"""
            for _, game in recent.iterrows():
                result_class = 'win' if game['result'] == 'WIN' else 'loss'
                html += f"""
                <div class="pick-card {result_class}">
                    <div class="matchup">{game['matchup']} <span class="badge {result_class}">{game['result']}</span></div>
                    <div class="details">
                        <div>Min Total: {game['minimum_total']}</div>
                        <div>Actual: <strong>{game['actual_total']}</strong></div>
                        <div>Confidence: {game['confidence_pct']:.1f}%</div>
                        <div>Decision: {game['decision']}</div>
                    </div>
                </div>
"""
            html += """
            </div>
        </div>
"""
    
    html += """
        <footer>
            <p>CBB Minimum Totals Prediction System</p>
            <p>🎲 Bet responsibly. Past performance does not guarantee future results.</p>
        </footer>
    </div>
</body>
</html>
"""
    
    return html


def main():
    """Generate and save dashboard"""
    html = generate_html()
    
    output_file = PROJECT_ROOT / 'output' / 'dashboard.html'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Dashboard generated: {output_file}")
    
    # Also save to docs for GitHub Pages
    docs_dir = PROJECT_ROOT / 'docs'
    docs_dir.mkdir(exist_ok=True)
    
    with open(docs_dir / 'index.html', 'w') as f:
        f.write(html)
    
    print(f"Also saved to docs/index.html for GitHub Pages")


if __name__ == "__main__":
    main()
