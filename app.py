"""
CBB Minimum Totals Dashboard
Flask app for Render deployment
"""

from flask import Flask, render_template_string, jsonify
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)

# Data directory
DATA_DIR = Path(__file__).parent / "data"

def load_predictions():
    """Load current predictions"""
    pred_file = DATA_DIR / "predictions.csv"
    if pred_file.exists():
        return pd.read_csv(pred_file)
    return pd.DataFrame()

def load_tracking():
    """Load tracking results"""
    track_file = DATA_DIR / "tracking_results.csv"
    if track_file.exists():
        return pd.read_csv(track_file)
    return pd.DataFrame()

def get_stats():
    """Calculate dashboard stats"""
    tracking = load_tracking()
    predictions = load_predictions()
    
    if tracking.empty:
        # Use predictions for pending
        pending = len(predictions[predictions['decision'] == 'YES']) if not predictions.empty else 0
        return {
            'record': '0-0',
            'win_rate': '0%',
            'pending': pending,
            'avg_confidence': f"{predictions['confidence_pct'].mean():.1f}%" if not predictions.empty else '0%'
        }
    
    complete = tracking[tracking['status'] == 'COMPLETE']
    pending = tracking[tracking['status'] == 'PENDING']
    
    if complete.empty:
        wins, losses = 0, 0
        win_rate = 0
    else:
        wins = len(complete[complete['result'] == 'WIN'])
        losses = len(complete[complete['result'] == 'LOSS'])
        win_rate = wins / len(complete) * 100 if len(complete) > 0 else 0
    
    avg_conf = tracking['confidence_pct'].mean() if 'confidence_pct' in tracking.columns else 0
    
    return {
        'record': f'{wins}-{losses}',
        'win_rate': f'{win_rate:.1f}%',
        'pending': len(pending),
        'avg_confidence': f'{avg_conf:.1f}%'
    }

def get_games_by_date():
    """Group predictions by game date"""
    predictions = load_predictions()
    
    if predictions.empty:
        return []
    
    # Filter to YES picks only
    yes_picks = predictions[predictions['decision'] == 'YES'].copy()
    
    if yes_picks.empty:
        return []
    
    # Add danger zone info
    from analyzers.danger_zone_filter import check_danger_zone
    
    games = []
    for _, row in yes_picks.iterrows():
        danger = check_danger_zone(
            row.get('home_team', ''),
            row.get('away_team', ''),
            row.get('minimum_total', 150)
        )
        
        games.append({
            'home_team': row.get('home_team', ''),
            'away_team': row.get('away_team', ''),
            'minimum_total': row.get('minimum_total', 0),
            'expected_total': row.get('expected_total', 0),
            'confidence': row.get('confidence_pct', 0),
            'buffer': row.get('buffer', 0),
            'game_date': row.get('game_date', ''),
            'game_time': row.get('game_time', ''),
            'is_danger': danger['is_danger'],
            'danger_level': danger['recommendation']
        })
    
    return games

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏀 CBB Minimum Totals</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1100px;
            margin: 0 auto;
        }
        
        .header {
            text-align: left;
            margin-bottom: 10px;
        }
        
        .header h1 {
            color: white;
            font-size: 28px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .subtitle {
            color: rgba(255,255,255,0.8);
            font-size: 14px;
            margin-top: 5px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        .stat-card {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .stat-label {
            color: rgba(255,255,255,0.7);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .stat-value {
            color: white;
            font-size: 32px;
            font-weight: 700;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin: 15px 0;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(17, 153, 142, 0.4);
        }
        
        .games-list {
            margin-top: 20px;
        }
        
        .game-card {
            background: rgba(255,255,255,0.12);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            margin-bottom: 12px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
        }
        
        .game-card:hover {
            transform: translateX(5px);
        }
        
        .game-card.danger {
            border-left: 4px solid #ff6b6b;
        }
        
        .game-card.caution {
            border-left: 4px solid #ffd93d;
        }
        
        .game-card.safe {
            border-left: 4px solid #6bcb77;
        }
        
        .game-header {
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }
        
        .game-teams {
            color: white;
            font-size: 16px;
            font-weight: 600;
        }
        
        .game-meta {
            color: rgba(255,255,255,0.6);
            font-size: 12px;
            margin-top: 4px;
        }
        
        .game-stats {
            text-align: right;
        }
        
        .game-pick-count {
            color: white;
            font-size: 14px;
            font-weight: 600;
        }
        
        .game-confidence {
            color: rgba(255,255,255,0.7);
            font-size: 12px;
        }
        
        .game-details {
            background: rgba(0,0,0,0.2);
            padding: 15px 20px;
            display: none;
        }
        
        .game-details.show {
            display: block;
        }
        
        .pick-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            color: white;
        }
        
        .pick-row:last-child {
            border-bottom: none;
        }
        
        .pick-label {
            color: rgba(255,255,255,0.7);
            font-size: 13px;
        }
        
        .pick-value {
            font-weight: 600;
            font-size: 14px;
        }
        
        .pick-value.green {
            color: #6bcb77;
        }
        
        .pick-value.yellow {
            color: #ffd93d;
        }
        
        .pick-value.red {
            color: #ff6b6b;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .badge.safe {
            background: rgba(107, 203, 119, 0.3);
            color: #6bcb77;
        }
        
        .badge.caution {
            background: rgba(255, 217, 61, 0.3);
            color: #ffd93d;
        }
        
        .badge.skip {
            background: rgba(255, 107, 107, 0.3);
            color: #ff6b6b;
        }
        
        .no-data {
            text-align: center;
            color: rgba(255,255,255,0.7);
            padding: 40px;
            font-size: 16px;
        }
        
        .section-title {
            color: white;
            font-size: 18px;
            font-weight: 600;
            margin: 25px 0 15px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .legend {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
            color: rgba(255,255,255,0.8);
            font-size: 12px;
        }
        
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }
        
        .legend-dot.safe { background: #6bcb77; }
        .legend-dot.caution { background: #ffd93d; }
        .legend-dot.skip { background: #ff6b6b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏀 CBB Minimum Totals</h1>
            <p class="subtitle">High-Confidence Alternate Totals (85%+ Win Rate Target)</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Record</div>
                <div class="stat-value">{{ stats.record }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value">{{ stats.win_rate }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pending Picks</div>
                <div class="stat-value">{{ stats.pending }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Confidence</div>
                <div class="stat-value">{{ stats.avg_confidence }}</div>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">
            🔄 Refresh Data
        </button>
        
        <div class="section-title">📋 Today's Picks</div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-dot safe"></div>
                <span>Safe - Bet 3%</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot caution"></div>
                <span>Caution - Bet 1-2%</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot skip"></div>
                <span>Skip - Don't Bet</span>
            </div>
        </div>
        
        <div class="games-list">
            {% if games %}
                {% for game in games %}
                <div class="game-card {{ 'skip' if game.danger_level == 'SKIP' else 'caution' if game.is_danger else 'safe' }}">
                    <div class="game-header" onclick="toggleDetails(this)">
                        <div>
                            <div class="game-teams">{{ game.away_team }} @ {{ game.home_team }}</div>
                            <div class="game-meta">OVER {{ game.minimum_total }} • Buffer: +{{ "%.1f"|format(game.buffer) }}</div>
                        </div>
                        <div class="game-stats">
                            <div class="game-pick-count">{{ "%.0f"|format(game.confidence) }}%</div>
                            <div class="game-confidence">
                                <span class="badge {{ 'skip' if game.danger_level == 'SKIP' else 'caution' if game.is_danger else 'safe' }}">
                                    {{ game.danger_level }}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="game-details">
                        <div class="pick-row">
                            <span class="pick-label">Minimum Total</span>
                            <span class="pick-value">{{ game.minimum_total }}</span>
                        </div>
                        <div class="pick-row">
                            <span class="pick-label">Expected Total</span>
                            <span class="pick-value green">{{ "%.1f"|format(game.expected_total) }}</span>
                        </div>
                        <div class="pick-row">
                            <span class="pick-label">Buffer</span>
                            <span class="pick-value green">+{{ "%.1f"|format(game.buffer) }} points</span>
                        </div>
                        <div class="pick-row">
                            <span class="pick-label">Confidence</span>
                            <span class="pick-value">{{ "%.1f"|format(game.confidence) }}%</span>
                        </div>
                        <div class="pick-row">
                            <span class="pick-label">Recommendation</span>
                            <span class="pick-value {{ 'red' if game.danger_level == 'SKIP' else 'yellow' if game.is_danger else 'green' }}">
                                {{ 'SKIP' if game.danger_level == 'SKIP' else 'CAUTION' if game.is_danger else 'BET 3%' }}
                            </span>
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data">
                    No picks available. Run the workflow to generate predictions.
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        function toggleDetails(header) {
            const details = header.nextElementSibling;
            details.classList.toggle('show');
        }
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    stats = get_stats()
    games = get_games_by_date()
    return render_template_string(DASHBOARD_HTML, stats=stats, games=games)

@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

@app.route('/api/picks')
def api_picks():
    return jsonify(get_games_by_date())

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
