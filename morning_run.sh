#!/bin/bash
echo "============================================================"
echo "🏀 CBB MORNING RUN - $(date +%Y-%m-%d)"
echo "============================================================"

cd ~/Documents/cbb_minimum_system

echo "📊 Fetching Barttorvik data..."
python fetch_barttorvik.py

echo ""
echo "🎯 Running picker..."
python unified_picker.py

echo ""
echo "📤 Pushing to Render..."
git add -A
git commit -m "Daily picks $(date +%Y-%m-%d)"
git push

echo ""
echo "============================================================"
echo "✅ DONE - https://cbb-minimum-totals.onrender.com"
echo "============================================================"
