#!/bin/bash
cd ~/Documents/cbb_minimum_system
source venv/bin/activate

echo "🎲 MONTE CARLO RESULTS"
echo "======================"
python mc_track_results.py

echo ""
echo "📊 LEGACY RESULTS"
echo "================="
python track_minimum_results.py
