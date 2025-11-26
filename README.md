# 🏀 CBB Minimum Totals Prediction System

A comprehensive College Basketball (CBB) prediction system focused on **minimum alternate totals** betting. This system predicts whether the combined score of both teams will go OVER the minimum alternate total line on DraftKings.

## 📊 Data Sources (IMPORTANT)

This system uses **REAL, CURRENT data** from multiple sources:

| Data Type | Source | Cost | Setup |
|-----------|--------|------|-------|
| **Team Stats** | BALLDONTLIE API | FREE | Sign up at https://www.balldontlie.io/ |
| **Team Stats** | ESPN API | FREE | No key needed (fallback) |
| **Betting Odds** | The Odds API | Paid | You have key already |
| **Betting Odds** | BALLDONTLIE API | FREE | Same key as stats |

### ⚠️ REQUIRED: Get Your BALLDONTLIE API Key

1. Go to https://www.balldontlie.io/
2. Sign up for a FREE account
3. Copy your API key
4. Add to `config/api_config.py`:
   ```python
   BALLDONTLIE_API_KEY = "your_key_here"
   ```

Without this key, the system uses ESPN as a fallback (less data).

---

## 📊 Overview

This system analyzes multiple factors to predict totals outcomes:
- **Offensive Efficiency** (30 points) - Points per possession analysis
- **Game Pace/Tempo** (25 points) - Speed of play analysis
- **Recent Form** (20 points) - Hot/cold streaks
- **Buffer Analysis** (15 points) - Safety margin above minimum
- **Rest/Schedule** (10 points) - Back-to-back detection

## 🎯 Confidence Thresholds

| Decision | Confidence | Action |
|----------|------------|--------|
| **YES** | 80%+ | Bet 3% bankroll |
| **MAYBE** | 75-79% | Consider 2% (optional) |
| **NO** | <75% | Skip |

## 📁 Project Structure

```
cbb_minimum_system/
├── config/
│   ├── api_config.py           # API keys & settings
│   └── season_config.py        # Season settings & thresholds
├── data/                       # All CSVs stored here
├── data_collection/
│   ├── cbb_stats_collector.py  # ESPN data via CBBpy
│   ├── odds_minimum_fetcher.py # DraftKings alternate totals
│   └── game_results_collector.py
├── analyzers/
│   ├── offensive_efficiency.py
│   ├── pace_analyzer.py
│   ├── recent_form_analyzer.py
│   └── rest_days_calculator.py
├── core/
│   └── minimum_total_predictor.py
├── decision/
│   └── yes_no_decider.py
├── ml_models/                  # Optional ML enhancement
│   ├── train_model.py
│   └── model_predictor.py
├── backtesting/
│   └── historical_backtester.py
├── output/
│   └── csv_exporter.py
├── output_archive/
│   ├── decisions/              # Daily prediction CSVs
│   └── backtests/              # Backtest results
├── master_workflow.py          # Main daily workflow
├── compare_thresholds.py       # Threshold analysis
├── track_minimum_results.py    # Results tracking
├── generate_dashboard.py       # HTML dashboard
├── app.py                      # Flask web server
├── requirements.txt            # Local dependencies
├── requirements_web.txt        # Render dependencies
└── render.yaml                 # Render deployment config
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or extract the project
cd cbb_minimum_system

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Edit `config/api_config.py` and verify your Odds API key:
```python
ODDS_API_KEY = "your_api_key_here"
```

### 3. Run the System

```bash
# Full daily workflow
python master_workflow.py

# Or run individual components:
python data_collection/cbb_stats_collector.py   # Collect team stats
python data_collection/odds_minimum_fetcher.py  # Fetch odds
python compare_thresholds.py                    # Analyze thresholds
python track_minimum_results.py                 # Track results
python generate_dashboard.py                    # Generate HTML dashboard
```

## 📅 Daily Workflow Commands

### Evening (Generate Picks)

```bash
cd ~/Documents/cbb_minimum_system && \
python master_workflow.py && \
python compare_thresholds.py && \
python track_minimum_results.py && \
python generate_dashboard.py && \
git add . && \
git commit -m "CBB Picks $(date +%Y-%m-%d)" && \
git push
```

### Morning (Update Results)

```bash
cd ~/Documents/cbb_minimum_system && \
python data_collection/game_results_collector.py && \
python track_minimum_results.py && \
python generate_dashboard.py && \
git add . && \
git commit -m "CBB Results $(date +%Y-%m-%d)" && \
git push
```

## 🧪 Backtesting

Before going live, validate with historical data:

```bash
python backtesting/historical_backtester.py
```

**Target:** 85%+ accuracy on YES picks

## 🤖 Machine Learning (Optional)

If rule-based accuracy is <85%, train ML models:

```bash
# After running backtests
python ml_models/train_model.py
```

## 🌐 Deploy to Render

1. Push code to GitHub
2. Connect repository to Render
3. Render will use `render.yaml` for configuration
4. Access your dashboard at: `https://your-app.onrender.com`

## 📈 Dashboard Features

- **Live Records**: YES, MAYBE, and Combined win rates
- **Today's Picks**: Current predictions with confidence levels
- **Recent Results**: Last 10 resolved predictions
- **Mobile Friendly**: Responsive design for phone access

## 🔧 Configuration

### Adjust Confidence Thresholds

Edit `config/season_config.py`:

```python
CONFIDENCE_THRESHOLDS = {
    'YES': 80,      # Adjust as needed
    'MAYBE': 75,
    'NO': 0
}
```

### Focus Conferences

The system focuses on major conferences for reliable data:
- Power 5: ACC, Big Ten, Big 12, Pac-12, SEC
- Major: Big East, American, Mountain West, West Coast, Atlantic 10

## 📊 Data Sources

| Source | Type | Usage |
|--------|------|-------|
| The Odds API | Paid | Live betting lines |
| ESPN/CBBpy | Free | Team statistics |
| NCAA Stats | Free | Historical data |

## ⚠️ Disclaimer

This system is for educational and entertainment purposes only. Sports betting involves risk. Past performance does not guarantee future results. Always bet responsibly and within your means.

## 📝 License

MIT License - Use freely, but please provide attribution.

## 🤝 Contributing

Contributions welcome! Please submit pull requests with:
1. Clear description of changes
2. Updated tests if applicable
3. Documentation updates

---

**Built with 🏀 for CBB betting enthusiasts**
