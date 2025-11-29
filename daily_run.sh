#!/bin/bash
# ============================================================
# CBB DAILY PICKER - MORNING RUN
# ============================================================
# Run this in the morning to generate picks for today
#
# Usage:
#   ./daily_run.sh              # Pick for today
#   ./daily_run.sh 2025-01-15   # Pick for specific date
# ============================================================

cd ~/Documents/cbb_minimum_system
source venv/bin/activate

DATE=${1:-$(date +%Y-%m-%d)}

echo ""
echo "============================================================"
echo "🏀 CBB DAILY PICKER - $DATE"
echo "============================================================"
echo ""

# Fetch fresh Barttorvik data
echo "📊 Fetching Barttorvik data..."
python fetch_barttorvik.py

echo ""

# Run unified picker (generates BOTH Elite Overs AND Monte Carlo picks)
echo "🎯 Running Unified Picker (Elite + MC)..."
python unified_picker.py --date $DATE

echo ""

# Run Maximum (Under) picker
echo "📉 Running Elite Unders (Maximum) Picker..."
python daily_max_picker.py --date $DATE

echo ""
echo "============================================================"
echo "📤 Pushing picks to Render..."
echo "============================================================"

# Add all pick files
git add data/*.csv

# Commit if there are changes
if git diff --cached --quiet; then
    echo "   No new picks to push"
else
    git commit -m "Daily picks $DATE"
    git push origin main
    echo "   ✅ Picks pushed to Render"
fi

echo ""
echo "============================================================"
echo "✅ PICKS COMPLETE"
echo "============================================================"
echo "   Dashboard: https://cbb-minimum-totals.onrender.com"
echo "============================================================"