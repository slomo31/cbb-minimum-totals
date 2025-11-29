#!/bin/bash
cd ~/Documents/cbb_minimum_system
source venv/bin/activate

echo "📈 Running Elite Overs (Minimum) Picker..."
python daily_elite_picker.py

echo "📉 Running Elite Unders (Maximum) Picker..."
python daily_max_picker.py

echo "🎲 Running Monte Carlo Analysis..."
python master_workflow_mc.py

echo "📤 Pushing to Render..."
git add data/elite_picks.csv data/max_picks.csv data/monte_carlo_picks.csv data/yes_picks_today.csv
git commit -m "Daily picks $(date +%m-%d)" 
git push origin main

echo "✅ Done! Dashboard will update in 2-3 minutes."
echo "   View at: https://your-app.onrender.com"