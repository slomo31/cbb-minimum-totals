#!/bin/bash
echo "============================================================"
echo "🌙 CBB EVENING RUN - $(date +%Y-%m-%d)"
echo "============================================================"

cd ~/Documents/cbb_minimum_system

echo "📥 Fetching game scores..."
python fetch_ncaa_games.py

echo ""
echo "📊 Scoring picks..."
python score_picks.py

echo ""
echo "📈 Today's Results:"
echo "------------------------------------------------------------"
grep "$(date +%Y-%m-%d)" data/tracking_results.csv 2>/dev/null || echo "No results yet"

echo ""
echo "============================================================"
echo "✅ DONE"
echo "============================================================"
