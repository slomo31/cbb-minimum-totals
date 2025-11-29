#!/usr/bin/env python3
"""
Fetch 2024-25 CBB season game results from Barttorvik
"""

import requests
import pandas as pd
from pathlib import Path
import json

DATA_DIR = Path(__file__).parent / "data"


def fetch_barttorvik_games():
    print("\n" + "=" * 70)
    print("�� Fetching 2024-25 Season Data from Barttorvik")
    print("=" * 70)
    
    url = "https://barttorvik.com/getgamestats.php?year=2025"
    
    print(f"\nFetching from {url}...")
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return None
        
        data = response.json()
        print(f"✅ Retrieved {len(data)} records")
        
        # Parse games - each record is a list
        # Sample: ["12/9/24",0,"Abilene Christian","WAC","Baylor","A","L, 88-57",...]
        all_games = []
        seen_games = set()
        
        for record in data:
            try:
                date_str = record[0]  # "12/9/24"
                team = record[2]       # Team name
                opponent = record[4]   # Opponent name
                location = record[5]   # H/A/N
                result = record[6]     # "L, 88-57" or "W, 75-60"
                
                # Parse score from result string
                if ', ' not in result:
                    continue
                    
                score_part = result.split(', ')[1]
                if '-' not in score_part:
                    continue
                
                scores = score_part.split('-')
                team_score = int(scores[0])
                opp_score = int(scores[1])
                
                # Convert date format from "12/9/24" to "2024-12-09"
                parts = date_str.split('/')
                if len(parts) == 3:
                    month = parts[0].zfill(2)
                    day = parts[1].zfill(2)
                    year = "20" + parts[2] if len(parts[2]) == 2 else parts[2]
                    date_formatted = f"{year}-{month}-{day}"
                else:
                    continue
                
                # Determine home/away
                if location == 'H':
                    home_team = team
                    away_team = opponent
                    home_score = team_score
                    away_score = opp_score
                elif location == 'A':
                    home_team = opponent
                    away_team = team
                    home_score = opp_score
                    away_score = team_score
                else:  # Neutral - skip or assign arbitrarily
                    continue
                
                # Create unique game ID to avoid duplicates
                teams = sorted([home_team, away_team])
                game_id = f"{date_formatted}_{teams[0]}_{teams[1]}"
                
                if game_id in seen_games:
                    continue
                seen_games.add(game_id)
                
                total = home_score + away_score
                
                all_games.append({
                    'date': date_formatted,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'total_points': total,
                })
                
            except Exception as e:
                continue
        
        print(f"✅ Parsed {len(all_games)} unique home/away games")
        return all_games
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    games = fetch_barttorvik_games()
    
    if not games:
        print("Failed to fetch games")
        return
    
    df = pd.DataFrame(games)
    df = df.sort_values('date', ascending=False)
    
    # Show date range
    print(f"\n📅 Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"📊 Total games: {len(df)}")
    
    # Count by month
    df['month'] = df['date'].str[:7]
    print("\n📆 Games by month:")
    print(df.groupby('month').size().sort_index())
    
    # Save
    output_file = DATA_DIR / "barttorvik_2024_25_games.csv"
    df.drop('month', axis=1).to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")
    
    # Show sample
    print("\nSample games:")
    print(df[['date', 'away_team', 'home_team', 'away_score', 'home_score', 'total_points']].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
