"""
API Configuration for CBB Minimum Totals System

DATA SOURCES:
1. BALLDONTLIE API - Team stats & odds (FREE signup: https://www.balldontlie.io/)
2. The Odds API - Betting lines (Paid: https://the-odds-api.com/)
3. ESPN Direct API - Fallback for stats (No key needed)
"""

# =============================================================================
# BALLDONTLIE API (PRIMARY for team stats + NCAAB data)
# Sign up FREE at: https://www.balldontlie.io/
# =============================================================================
BALLDONTLIE_API_KEY = "bb4af2df-581f-4ca5-ad9a-2b1578067de8"

# =============================================================================
# The Odds API (for betting odds/lines)
# =============================================================================
ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
ODDS_SPORT = "basketball_ncaab"

# Default bookmaker to focus on
PRIMARY_BOOKMAKER = "draftkings"

# API request settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5
