#!/bin/bash
cd ~/Documents/cbb_minimum_system
source venv/bin/activate

echo ""
echo "============================================================"
echo "🏀 CBB END-OF-DAY RESULTS TRACKER"
echo "============================================================"

echo ""
echo "📈 ELITE OVERS RESULTS (TIERS 1-4)"
echo "==================================="
python elite_track_results.py

echo ""
echo "🎲 MONTE CARLO RESULTS (OVERS)"
echo "=============================="
python mc_track_results.py

echo ""
echo "📉 ELITE UNDERS RESULTS (MAX)"
echo "=============================="
python mc_max_track_results.py

echo ""
echo "📊 LEGACY RESULTS"
echo "================="
python track_minimum_results.py

echo ""
echo "============================================================"
echo "✅ TRACKING COMPLETE"
echo "============================================================"
