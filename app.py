"""
CBB Minimum Totals Dashboard - DUAL SYSTEM
Flask app with Monte Carlo + Legacy views
"""

from flask import Flask, render_template_string, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)

# Data directory
DATA_DIR = Path(__file__).parent / "data"


# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

def load_monte_carlo_picks():
    """Load Monte Carlo simulation results"""
    mc_file = DATA_DIR / "monte_carlo_picks.csv"
    if mc_file.exists():
        return pd.read_csv(mc_file)
    return pd.DataFrame()


def load_legacy_predictions():
    """Load legacy system predictions"""
    pred_file = DATA_DIR / "predictions.csv"
    if pred_file.exists():
        return pd.read_csv(pred_file)
    return pd.DataFrame()


def load_mc_tracking():
    """Load Monte Carlo tracking results"""
    track_file = DATA_DIR / "mc_tracking_results.csv"
    if track_file.exists():
        return pd.read_csv(track_file)
    return pd.DataFrame()


def load_legacy_tracking():
    """Load legacy tracking results"""
    track_file = DATA_DIR / "tracking_results.csv"
    if track_file.exists():
        return pd.read_csv(track_file)
    return pd.DataFrame()


# ============================================================
# STATS FUNCTIONS
# ============================================================

def get_mc_stats():
    """Get Monte Carlo system stats"""
    tracking = load_mc_tracking()
    predictions = load_monte_carlo_picks()
    
    # Filter to YES picks
    yes_picks = predictions[predictions['decision'] == 'YES'] if not predictions.empty else pd.DataFrame()
    
    if tracking.empty:
        pending = len(yes_picks) if not yes_picks.empty else 0
        avg_hit_rate = yes_picks['hit_rate'].mean() if not yes_picks.empty and 'hit_rate' in yes_picks.columns else 0
        return {
            'record': '0-0',
            'win_rate': '0.0%',
            'pending': pending,
            'avg_confidence': f"{avg_hit_rate:.1f}%"
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
    
    avg_hit = tracking['hit_rate'].mean() if 'hit_rate' in tracking.columns else 0
    
    return {
        'record': f'{wins}-{losses}',
        'win_rate': f'{win_rate:.1f}%',
        'pending': len(pending),
        'avg_confidence': f'{avg_hit:.1f}%'
    }


def get_legacy_stats():
    """Get legacy system stats"""
    tracking = load_legacy_tracking()
    predictions = load_legacy_predictions()
    
    yes_picks = predictions[predictions['decision'] == 'YES'] if not predictions.empty else pd.DataFrame()
    
    if tracking.empty:
        pending = len(yes_picks) if not yes_picks.empty else 0
        avg_conf = predictions['confidence_pct'].mean() if not predictions.empty and 'confidence_pct' in predictions.columns else 0
        return {
            'record': '0-0',
            'win_rate': '0.0%',
            'pending': pending,
            'avg_confidence': f"{avg_conf:.1f}%"
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


# ============================================================
# GAMES FUNCTIONS
# ============================================================

def get_mc_games():
    """Get Monte Carlo picks for display"""
    predictions = load_monte_carlo_picks()
    
    if predictions.empty:
        return {'yes': [], 'maybe': [], 'no': []}
    
    yes_picks = predictions[predictions['decision'] == 'YES'].copy()
    maybe_picks = predictions[predictions['decision'] == 'MAYBE'].copy()
    no_picks = predictions[predictions['decision'] == 'NO'].copy()
    
    def to_game_list(df):
        games = []
        for _, row in df.iterrows():
            games.append({
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'minimum_total': row.get('minimum_total', 0),
                'standard_total': row.get('standard_total', 0),
                'hit_rate': row.get('hit_rate', 0),
                'sim_mean': row.get('sim_mean', 0),
                'sim_range': row.get('sim_range', ''),
                'data_quality': row.get('data_quality', ''),
                'game_time': row.get('game_time', ''),
            })
        return games
    
    return {
        'yes': to_game_list(yes_picks),
        'maybe': to_game_list(maybe_picks),
        'no': to_game_list(no_picks)
    }


def get_legacy_games():
    """Get legacy picks for display"""
    predictions = load_legacy_predictions()
    
    if predictions.empty:
        return []
    
    yes_picks = predictions[predictions['decision'] == 'YES'].copy()
    
    if yes_picks.empty:
        return []
    
    games = []
    for _, row in yes_picks.iterrows():
        conf = row.get('confidence_pct', 0)
        
        # Determine danger level based on confidence
        if conf >= 85:
            danger_level = 'SAFE'
            is_danger = False
        elif conf >= 75:
            danger_level = 'CAUTION'
            is_danger = True
        else:
            danger_level = 'SKIP'
            is_danger = True
        
        games.append({
            'home_team': row.get('home_team', ''),
            'away_team': row.get('away_team', ''),
            'minimum_total': row.get('minimum_total', 0),
            'expected_total': row.get('expected_total', 0),
            'confidence': conf,
            'buffer': row.get('buffer', 0),
            'game_time': row.get('game_time', ''),
            'is_danger': is_danger,
            'danger_level': danger_level
        })
    
    return games


# ============================================================
# HTML TEMPLATE - DUAL SYSTEM
# ============================================================

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
            max-width: 1200px;
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
        
        .updated-time {
            color: rgba(255,255,255,0.6);
            font-size: 12px;
            margin-top: 5px;
        }
        
        /* System Toggle */
        .system-toggle {
            display: flex;
            gap: 10px;
            margin: 20px 0;
        }
        
        .toggle-btn {
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            border: 2px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.1);
            color: white;
            transition: all 0.3s;
        }
        
        .toggle-btn:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .toggle-btn.active {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            border-color: transparent;
        }
        
        .toggle-btn .badge-count {
            background: rgba(255,255,255,0.3);
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
            font-size: 12px;
        }
        
        .toggle-btn.active .badge-count {
            background: rgba(0,0,0,0.2);
        }
        
        /* Stats Grid */
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
        
        /* Game Cards */
        .games-section {
            margin-top: 20px;
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
        
        .game-card.yes { border-left: 4px solid #6bcb77; }
        .game-card.maybe { border-left: 4px solid #ffd93d; }
        .game-card.no { border-left: 4px solid #ff6b6b; }
        .game-card.safe { border-left: 4px solid #6bcb77; }
        .game-card.caution { border-left: 4px solid #ffd93d; }
        .game-card.skip { border-left: 4px solid #ff6b6b; }
        
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
        
        .hit-rate {
            color: white;
            font-size: 20px;
            font-weight: 700;
        }
        
        .hit-rate.high { color: #6bcb77; }
        .hit-rate.medium { color: #ffd93d; }
        .hit-rate.low { color: #ff6b6b; }
        
        .game-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-top: 4px;
        }
        
        .game-badge.yes { background: rgba(107, 203, 119, 0.3); color: #6bcb77; }
        .game-badge.maybe { background: rgba(255, 217, 61, 0.3); color: #ffd93d; }
        .game-badge.no { background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }
        .game-badge.safe { background: rgba(107, 203, 119, 0.3); color: #6bcb77; }
        .game-badge.caution { background: rgba(255, 217, 61, 0.3); color: #ffd93d; }
        .game-badge.skip { background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }
        
        .game-details {
            background: rgba(0,0,0,0.2);
            padding: 15px 20px;
            display: none;
        }
        
        .game-details.show {
            display: block;
        }
        
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            color: white;
        }
        
        .detail-row:last-child {
            border-bottom: none;
        }
        
        .detail-label {
            color: rgba(255,255,255,0.7);
            font-size: 13px;
        }
        
        .detail-value {
            font-weight: 600;
            font-size: 14px;
        }
        
        .detail-value.green { color: #6bcb77; }
        .detail-value.yellow { color: #ffd93d; }
        .detail-value.red { color: #ff6b6b; }
        
        /* Legend */
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
        
        .legend-dot.yes, .legend-dot.safe { background: #6bcb77; }
        .legend-dot.maybe, .legend-dot.caution { background: #ffd93d; }
        .legend-dot.no, .legend-dot.skip { background: #ff6b6b; }
        
        .no-data {
            text-align: center;
            color: rgba(255,255,255,0.7);
            padding: 40px;
            font-size: 16px;
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
        
        /* System indicator */
        .system-indicator {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 10px;
        }
        
        .system-indicator.mc {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
        }
        
        .system-indicator.legacy {
            background: rgba(255,255,255,0.2);
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🏀 CBB Minimum Totals
                <span class="system-indicator {{ 'mc' if system == 'mc' else 'legacy' }}">
                    {{ 'MONTE CARLO' if system == 'mc' else 'LEGACY' }}
                </span>
            </h1>
            <p class="subtitle">
                {% if system == 'mc' %}
                    Simulation-Based Analysis (5,000 sims per game)
                {% else %}
                    Buffer-Based Analysis (Legacy System)
                {% endif %}
            </p>
            <p class="updated-time">Last updated: {{ now }}</p>
        </div>
        
        <!-- System Toggle -->
        <div class="system-toggle">
            <a href="/?system=mc" class="toggle-btn {{ 'active' if system == 'mc' else '' }}">
                🎲 Monte Carlo
                <span class="badge-count">{{ mc_stats.pending }}</span>
            </a>
            <a href="/?system=legacy" class="toggle-btn {{ 'active' if system == 'legacy' else '' }}">
                📊 Legacy
                <span class="badge-count">{{ legacy_stats.pending }}</span>
            </a>
        </div>
        
        <!-- Stats Grid -->
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
                <div class="stat-label">{{ 'Avg Hit Rate' if system == 'mc' else 'Avg Confidence' }}</div>
                <div class="stat-value">{{ stats.avg_confidence }}</div>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">
            🔄 Refresh Data
        </button>
        
        <!-- MONTE CARLO VIEW -->
        {% if system == 'mc' %}
            <div class="games-section">
                <!-- YES Picks -->
                {% if mc_games.yes %}
                <div class="section-title">🟢 YES - Bet These ({{ mc_games.yes|length }})</div>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-dot yes"></div>
                        <span>88%+ Hit Rate - Bet 3%</span>
                    </div>
                </div>
                {% for game in mc_games.yes %}
                <div class="game-card yes">
                    <div class="game-header" onclick="toggleDetails(this)">
                        <div>
                            <div class="game-teams">{{ game.away_team }} @ {{ game.home_team }}</div>
                            <div class="game-meta">OVER {{ game.minimum_total }} • Sim avg: {{ "%.1f"|format(game.sim_mean) }}</div>
                        </div>
                        <div class="game-stats">
                            <div class="hit-rate high">{{ "%.1f"|format(game.hit_rate) }}%</div>
                            <span class="game-badge yes">YES</span>
                        </div>
                    </div>
                    <div class="game-details">
                        <div class="detail-row">
                            <span class="detail-label">Minimum Total</span>
                            <span class="detail-value">{{ game.minimum_total }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Standard Line</span>
                            <span class="detail-value">{{ game.standard_total }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Simulation Hit Rate</span>
                            <span class="detail-value green">{{ "%.1f"|format(game.hit_rate) }}%</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Sim Mean</span>
                            <span class="detail-value">{{ "%.1f"|format(game.sim_mean) }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Sim Range</span>
                            <span class="detail-value">{{ game.sim_range }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Data Quality</span>
                            <span class="detail-value">{{ game.data_quality }}</span>
                        </div>
                    </div>
                </div>
                {% endfor %}
                {% endif %}
                
                <!-- MAYBE Picks -->
                {% if mc_games.maybe %}
                <div class="section-title">🟡 MAYBE - Caution ({{ mc_games.maybe|length }})</div>
                {% for game in mc_games.maybe %}
                <div class="game-card maybe">
                    <div class="game-header" onclick="toggleDetails(this)">
                        <div>
                            <div class="game-teams">{{ game.away_team }} @ {{ game.home_team }}</div>
                            <div class="game-meta">OVER {{ game.minimum_total }} • Sim avg: {{ "%.1f"|format(game.sim_mean) }}</div>
                        </div>
                        <div class="game-stats">
                            <div class="hit-rate medium">{{ "%.1f"|format(game.hit_rate) }}%</div>
                            <span class="game-badge maybe">MAYBE</span>
                        </div>
                    </div>
                    <div class="game-details">
                        <div class="detail-row">
                            <span class="detail-label">Minimum Total</span>
                            <span class="detail-value">{{ game.minimum_total }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Simulation Hit Rate</span>
                            <span class="detail-value yellow">{{ "%.1f"|format(game.hit_rate) }}%</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Sim Range</span>
                            <span class="detail-value">{{ game.sim_range }}</span>
                        </div>
                    </div>
                </div>
                {% endfor %}
                {% endif %}
                
                <!-- NO Picks -->
                {% if mc_games.no %}
                <div class="section-title">🔴 NO - Skip These ({{ mc_games.no|length }})</div>
                {% for game in mc_games.no %}
                <div class="game-card no">
                    <div class="game-header" onclick="toggleDetails(this)">
                        <div>
                            <div class="game-teams">{{ game.away_team }} @ {{ game.home_team }}</div>
                            <div class="game-meta">OVER {{ game.minimum_total }} • Too risky</div>
                        </div>
                        <div class="game-stats">
                            <div class="hit-rate low">{{ "%.1f"|format(game.hit_rate) }}%</div>
                            <span class="game-badge no">SKIP</span>
                        </div>
                    </div>
                    <div class="game-details">
                        <div class="detail-row">
                            <span class="detail-label">Minimum Total</span>
                            <span class="detail-value">{{ game.minimum_total }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Simulation Hit Rate</span>
                            <span class="detail-value red">{{ "%.1f"|format(game.hit_rate) }}%</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Sim Range</span>
                            <span class="detail-value">{{ game.sim_range }}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Why Skip</span>
                            <span class="detail-value red">Hit rate below 88%</span>
                        </div>
                    </div>
                </div>
                {% endfor %}
                {% endif %}
                
                {% if not mc_games.yes and not mc_games.maybe and not mc_games.no %}
                <div class="no-data">
                    No Monte Carlo picks available.<br>
                    Run: python master_workflow_mc.py
                </div>
                {% endif %}
            </div>
        
        <!-- LEGACY VIEW -->
        {% else %}
            <div class="games-section">
                <div class="section-title">📋 Today's Picks (Legacy System)</div>
                
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
                
                {% if legacy_games %}
                    {% for game in legacy_games %}
                    <div class="game-card {{ 'skip' if game.danger_level == 'SKIP' else 'caution' if game.is_danger else 'safe' }}">
                        <div class="game-header" onclick="toggleDetails(this)">
                            <div>
                                <div class="game-teams">{{ game.away_team }} @ {{ game.home_team }}</div>
                                <div class="game-meta">OVER {{ game.minimum_total }} • Buffer: +{{ "%.1f"|format(game.buffer) }}</div>
                            </div>
                            <div class="game-stats">
                                <div class="hit-rate {{ 'high' if game.confidence >= 85 else 'medium' if game.confidence >= 75 else 'low' }}">
                                    {{ "%.0f"|format(game.confidence) }}%
                                </div>
                                <span class="game-badge {{ 'skip' if game.danger_level == 'SKIP' else 'caution' if game.is_danger else 'safe' }}">
                                    {{ game.danger_level }}
                                </span>
                            </div>
                        </div>
                        <div class="game-details">
                            <div class="detail-row">
                                <span class="detail-label">Minimum Total</span>
                                <span class="detail-value">{{ game.minimum_total }}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Expected Total</span>
                                <span class="detail-value green">{{ "%.1f"|format(game.expected_total) }}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Buffer</span>
                                <span class="detail-value green">+{{ "%.1f"|format(game.buffer) }} points</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Confidence</span>
                                <span class="detail-value">{{ "%.1f"|format(game.confidence) }}%</span>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-data">
                        No legacy picks available.<br>
                        Run: python master_workflow.py
                    </div>
                {% endif %}
            </div>
        {% endif %}
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


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def dashboard():
    system = request.args.get('system', 'mc')  # Default to Monte Carlo
    
    mc_stats = get_mc_stats()
    legacy_stats = get_legacy_stats()
    mc_games = get_mc_games()
    legacy_games = get_legacy_games()
    
    stats = mc_stats if system == 'mc' else legacy_stats
    
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    return render_template_string(
        DASHBOARD_HTML,
        system=system,
        stats=stats,
        mc_stats=mc_stats,
        legacy_stats=legacy_stats,
        mc_games=mc_games,
        legacy_games=legacy_games,
        now=now
    )


@app.route('/api/stats')
def api_stats():
    system = request.args.get('system', 'mc')
    if system == 'mc':
        return jsonify(get_mc_stats())
    return jsonify(get_legacy_stats())


@app.route('/api/picks')
def api_picks():
    system = request.args.get('system', 'mc')
    if system == 'mc':
        return jsonify(get_mc_games())
    return jsonify({'games': get_legacy_games()})


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)