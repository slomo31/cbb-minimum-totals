#!/bin/bash
cd ~/Documents/cbb_minimum_system
source venv/bin/activate

echo "🏀 Running Monte Carlo Analysis..."
python master_workflow_mc.py

echo "📤 Pushing to Render..."
git add data/monte_carlo_picks.csv data/yes_picks_today.csv
git commit -m "Daily MC picks $(date +%m-%d)" 
git push origin main

echo "✅ Done! Dashboard will update in 2-3 minutes."
