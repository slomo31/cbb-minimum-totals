"""
Season Configuration for CBB Minimum Totals System
2025-2026 Season
"""

from datetime import datetime, date

# Current Season
CURRENT_SEASON = 2026
SEASON_START_DATE = date(2025, 11, 1)
SEASON_END_DATE = date(2026, 4, 15)

# Historical season for backtesting
BACKTEST_SEASON = 2025

# Focus Conferences - DISABLED for now (ESPN uses different names)
FOCUS_CONFERENCES = []  # Empty = include all teams

# Minimum games required for reliable stats
MIN_GAMES_FOR_ANALYSIS = 3

# Scoring thresholds for confidence calculation
CONFIDENCE_WEIGHTS = {
    'offensive_efficiency': 30,
    'pace_tempo': 25,
    'recent_form': 20,
    'buffer_analysis': 15,
    'rest_schedule': 10
}

# Decision thresholds
CONFIDENCE_THRESHOLDS = {
    'YES': 80,
    'MAYBE': 75,
    'NO': 0
}

# Bankroll allocation
BANKROLL_ALLOCATION = {
    'YES': 0.03,
    'MAYBE': 0.02
}

# Data paths
DATA_DIR = "data"
OUTPUT_DIR = "output"
OUTPUT_ARCHIVE_DIR = "output_archive"

# File names
TEAM_STATS_FILE = f"cbb_team_stats_{CURRENT_SEASON-1}_{CURRENT_SEASON}.csv"
COMPLETED_GAMES_FILE = f"cbb_completed_games_{CURRENT_SEASON-1}_{CURRENT_SEASON}.csv"
UPCOMING_GAMES_FILE = "upcoming_games.csv"

def get_current_date():
    return datetime.now().date()

def is_season_active():
    today = get_current_date()
    return SEASON_START_DATE <= today <= SEASON_END_DATE
