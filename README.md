# CBB Minimum Totals System - Operations Guide

A smart betting analysis system for college basketball alternate totals. Uses NCAA game data to identify high-risk matchups and provide confident betting recommendations.

---

##   NEW COMMAND LIST 

# Morning: Run both systems
python master_workflow_mc.py    # Monte Carlo (14 picks)
python master_workflow.py       # Legacy (61 picks)

./morning_run.sh
./evening_run.sh

## Every mornin easy command ##
~/Documents/cbb_minimum_system/daily_run.sh

# Evening: Track results
python mc_track_results.py      # Check MC results
python track_minimum_results.py # Check Legacy results

#####
## 🏀 What This System Does

1. **Pulls historical game data** from NCAA API (scores, teams, dates)
2. **Calculates team statistics** (PPG, opponent PPG, pace, game totals)
3. **Identifies risk factors** (elite defenses, low offenses, slow pace teams)
4. **Fetches today's odds** from DraftKings (standard + alternate totals)
5. **Analyzes each matchup** and provides YES/NO/MAYBE recommendations

---

## 📁 Project Setup

```bash
cd ~/Documents/cbb_minimum_system
source venv/bin/activate
```

---

## 🔄 Daily Workflow

### Option 1: Single Command (Recommended)

Run everything with one command:

```bash
python master_workflow.py
```

**Flags:**
- `--skip-update` - Skip NCAA stats update (faster, use existing data)
- `--max-games 50` - Limit how many games to fetch alternate lines for

```bash
# Examples
python master_workflow.py                  # Full analysis
python master_workflow.py --skip-update    # Skip NCAA update (faster)
python master_workflow.py --max-games 50   # Limit to 50 games
```

---

### Option 2: Manual Steps

#### Step 1: Update Team Stats (run once daily, ~15 seconds)

Fetches yesterday's completed games and recalculates team statistics.

```bash
python data_collection/ncaa_stats_fetcher.py
```

#### Step 2: Run Analysis on Today's Games

Fetches current odds and evaluates all matchups.

```bash
python -c "
from data_collection.odds_minimum_fetcher import OddsMinimumFetcher
from core.smart_matchup_evaluator import evaluate_all_games, print_evaluation_report

fetcher = OddsMinimumFetcher()
df = fetcher.fetch_all_games_with_minimums(max_alt_lookups=100)
results, summary = evaluate_all_games(df.to_dict('records'))
print_evaluation_report(results, summary)
"
```

---

## 📊 Interpreting Results

| Symbol | Meaning | Risk Score | Action |
|--------|---------|------------|--------|
| 🔴 NO | High risk | 45+ points | **SKIP** |
| 🟡 MAYBE | Medium risk | 30-44 points | Use caution |
| 🟢 YES 90%+ | Low risk, both teams known | <18 points | **BET** |
| 🟢 YES 80-89% | Minor risk factors | 18-29 points | Good bet |
| 🟢 YES 70-79% | Some risk factors | 18-29 points | Evaluate |
| ❓ Unverified | Missing team data | N/A | Your judgment |
| ⚪ Skip | No alternate line available | N/A | Can't bet |

---

## 🛡️ Risk Factors Detected

| Factor | What It Means | Risk Points |
|--------|---------------|-------------|
| Elite Defense T1 | Team holds opponents under 60 PPG | +22 |
| Elite Defense T2 | Team holds opponents under 65 PPG | +18 |
| Elite Defense T3 | Top 20% defensive team | +14 |
| Low Offense | Team scores under 65-70 PPG | +12-22 |
| Slow Pace | Bottom 20% in possessions | +5-12 |
| Low Game Totals | Team's games average under 140 | +5-10 |
| BOTH Elite Defense | Both teams are elite defenders | +20 |
| Very Low Line | Minimum total under 120 | +20 |
| Low Line | Minimum total 120-125 | +15 |
| Below Avg Line | Minimum total 125-130 | +8 |

---

## 📂 Project Files

| File | Purpose |
|------|---------|
| `master_workflow.py` | **Single command to run everything** |
| `data_collection/ncaa_stats_fetcher.py` | Pulls game data from NCAA API |
| `data_collection/odds_minimum_fetcher.py` | Pulls odds from DraftKings API |
| `core/smart_matchup_evaluator.py` | Analyzes matchups for risk |
| `data/ncaa_games_history.csv` | All completed games (auto-generated) |
| `data/team_risk_database.json` | Team stats & risk factors (auto-generated) |
| `data/ncaa_fetch_log.json` | Tracks which dates have been fetched |
| `data/upcoming_games.csv` | Today's games with odds (auto-generated) |

---

## 🚀 Push to Render (Git)

```bash
cd ~/Documents/cbb_minimum_system

# Check what's changed
git status

# Add all changes
git add .

# Commit with message
git commit -m "Your commit message here"

# Push to trigger Render deploy
git push origin main

git add . && git commit -m "Update" && git push origin main
```

---

## 🔧 Troubleshooting Commands

### Check teams in database
```bash
python -c "
import json
with open('data/team_risk_database.json') as f:
    db = json.load(f)
print(f'Teams tracked: {len(db[\"all_teams\"])}')
print(f'Elite defenses: {len(db[\"elite_defense\"])}')
print(f'Low offenses: {len(db[\"low_offense\"])}')
print(f'Slow pace: {len(db[\"slow_pace\"])}')
"
```

### Check games in history
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/ncaa_games_history.csv')
print(f'Total games: {len(df)}')
print(f'Date range: {df[\"date\"].min()} to {df[\"date\"].max()}')
"
```

### Check fetch log
```bash
python -c "
import json
with open('data/ncaa_fetch_log.json') as f:
    log = json.load(f)
print(f'Dates fetched: {len(log[\"dates_fetched\"])}')
print(f'Last update: {log[\"last_update\"]}')
"
```

### Force re-fetch all dates (reset)
```bash
rm data/ncaa_fetch_log.json
rm data/ncaa_games_history.csv
python data_collection/ncaa_stats_fetcher.py
```

---

## ⏰ Recommended Schedule

| When | Command |
|------|---------|
| Daily (before betting) | `python master_workflow.py` |
| Quick re-check (same day) | `python master_workflow.py --skip-update` |
| Weekly | `git push` any code changes to Render |

---

## 📈 How the System Works

### Data Flow
```
                    master_workflow.py
                          |
         +----------------+----------------+
         |                                 |
         v                                 v
NCAA API (ncaa.com)              DraftKings API (the-odds-api.com)
         |                                 |
         v                                 v
ncaa_stats_fetcher.py            odds_minimum_fetcher.py
         |                                 |
         v                                 v
ncaa_games_history.csv           upcoming_games.csv
         |                                 |
         v                                 v
team_risk_database.json -----> smart_matchup_evaluator.py
                                           |
                                           v
                               Recommendations (YES/NO/MAYBE)
```

### Incremental Updates
- `ncaa_stats_fetcher.py` only fetches NEW dates not already in the log
- First run: Downloads entire season (~1,300+ games)
- Daily runs: Only fetches yesterday's games (~60-80 games, ~5 seconds)

---

## 🎯 Historical Performance

Based on backtesting 2023-24 season data:
- **92% of games** hit the minimum alternate total
- **Risk factors** successfully identify the 8% that don't
- System correctly flags elite defense matchups as high-risk

---

## 📝 Notes

- The Odds API has rate limits - the system tracks remaining requests
- NCAA API is rate-limited to 5 requests/second (we use 2/sec to be safe)
- Data files in `/data` are auto-generated and git-ignored
- Season start date: November 3, 2025

---

## 🆘 Support

If something breaks:
1. Check that your virtual environment is activated
2. Verify API keys are set (for DraftKings odds)
3. Check the fetch log to see what dates have been downloaded
4. Try force re-fetching if data seems stale

---

*Last updated: November 26, 2025*