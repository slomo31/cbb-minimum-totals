#!/usr/bin/env python3
"""
Barttorvik Team Stats Fetcher
=============================
Fetches advanced stats for all 365 D1 teams from Barttorvik.
Includes adjusted efficiency ratings and tempo for accurate game total predictions.
"""

import requests
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / 'data'

# Barttorvik column mapping (based on their JSON structure)
COLUMNS = {
    0: 'rank',
    1: 'team',
    2: 'conference',
    3: 'record',
    4: 'adj_o',          # Adjusted Offensive Efficiency (pts per 100 poss)
    5: 'adj_o_rank',
    6: 'adj_d',          # Adjusted Defensive Efficiency (pts allowed per 100 poss)
    7: 'adj_d_rank',
    8: 'barthag',        # Power rating (win probability vs avg team)
    9: 'barthag_rank',
    10: 'efg_pct',       # Effective FG%
    11: 'efg_pct_d',     # Defensive EFG%
    12: 'to_pct',        # Turnover %
    13: 'to_pct_d',      # Defensive TO%
    14: 'conf_record',
    15: 'sos',           # Strength of schedule
    23: 'raw_o',         # Raw offensive efficiency
    24: 'raw_d',         # Raw defensive efficiency
    25: 'adj_o_no_opp',  # Adj O without opponent adjustment
    26: 'adj_d_no_opp',  # Adj D without opponent adjustment
    29: 'off_ftrate',    # Free throw rate offense
    30: 'def_ftrate',    # Free throw rate defense
    44: 'adj_tempo',     # Adjusted tempo (possessions per game)
}


def fetch_barttorvik_stats(year: int = 2026) -> pd.DataFrame:
    """
    Fetch team stats from Barttorvik for given year.
    
    Args:
        year: Academic year (2026 = 2025-26 season)
        
    Returns:
        DataFrame with team stats
    """
    url = f"https://barttorvik.com/{year}_team_results.json"
    
    print(f"Fetching Barttorvik stats from {url}...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"   Retrieved {len(data)} teams")
        
        # Convert to DataFrame
        rows = []
        for team_data in data:
            row = {}
            for idx, col_name in COLUMNS.items():
                if idx < len(team_data):
                    row[col_name] = team_data[idx]
            
            # Calculate derived stats
            if 'adj_o' in row and 'adj_tempo' in row:
                row['est_ppg'] = (row['adj_o'] / 100) * row['adj_tempo']
            if 'adj_d' in row and 'adj_tempo' in row:
                row['est_opp_ppg'] = (row['adj_d'] / 100) * row['adj_tempo']
            if 'est_ppg' in row and 'est_opp_ppg' in row:
                row['est_total'] = row['est_ppg'] + row['est_opp_ppg']
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Parse record into wins/losses
        if 'record' in df.columns:
            df[['wins', 'losses']] = df['record'].str.split('-', expand=True).astype(int)
            df['games'] = df['wins'] + df['losses']
        
        return df
        
    except Exception as e:
        print(f"   Error fetching stats: {e}")
        return pd.DataFrame()


def calculate_matchup_total(home_team: str, away_team: str, df: pd.DataFrame) -> dict:
    """
    Calculate expected game total for a matchup using Barttorvik methodology.
    
    The key insight: when two teams play, the game tempo is roughly the average
    of their tempos, and each team's scoring is their efficiency * game tempo.
    
    Args:
        home_team: Home team name
        away_team: Away team name
        df: DataFrame with team stats
        
    Returns:
        Dict with matchup analysis
    """
    # Find teams (fuzzy match)
    home_row = find_team(home_team, df)
    away_row = find_team(away_team, df)
    
    result = {
        'home_team': home_team,
        'away_team': away_team,
        'home_found': home_row is not None,
        'away_found': away_row is not None,
    }
    
    if home_row is None or away_row is None:
        return result
    
    # Get stats
    home_adj_o = home_row['adj_o']
    home_adj_d = home_row['adj_d']
    home_tempo = home_row['adj_tempo']
    
    away_adj_o = away_row['adj_o']
    away_adj_d = away_row['adj_d']
    away_tempo = away_row['adj_tempo']
    
    # Calculate expected game tempo (average of both teams)
    # Adjusted for league average tempo (~67.5 possessions)
    league_avg_tempo = 67.5
    game_tempo = (home_tempo + away_tempo + league_avg_tempo) / 3
    
    # Calculate expected points
    # Home team scores against away team's defense
    # Away team scores against home team's defense
    # Use geometric mean of offensive and defensive efficiencies
    
    home_expected = ((home_adj_o + (100 - (away_adj_d - 100))) / 2) * (game_tempo / 100)
    away_expected = ((away_adj_o + (100 - (home_adj_d - 100))) / 2) * (game_tempo / 100)
    
    # Simpler calculation: just use efficiency * tempo
    home_simple = (home_adj_o / 100) * game_tempo
    away_simple = (away_adj_o / 100) * game_tempo
    
    # Add home court advantage (~3.5 points)
    home_advantage = 3.5
    
    result.update({
        'home_adj_o': home_adj_o,
        'home_adj_d': home_adj_d,
        'home_tempo': home_tempo,
        'away_adj_o': away_adj_o,
        'away_adj_d': away_adj_d,
        'away_tempo': away_tempo,
        'game_tempo': game_tempo,
        'home_expected': home_simple + (home_advantage / 2),
        'away_expected': away_simple - (home_advantage / 2),
        'expected_total': home_simple + away_simple,
        'home_is_elite_d': home_adj_d < 95,  # Elite defense threshold
        'away_is_elite_d': away_adj_d < 95,
    })
    
    return result


def find_team(name: str, df: pd.DataFrame) -> pd.Series:
    """Fuzzy match team name to DataFrame."""
    name_lower = name.lower()
    
    # Direct match
    for idx, row in df.iterrows():
        if row['team'].lower() == name_lower:
            return row
    
    # Partial match
    for idx, row in df.iterrows():
        team_lower = row['team'].lower()
        # Check if search term is in team name or vice versa
        if name_lower in team_lower or team_lower in name_lower:
            return row
        # Check key words
        name_words = set(name_lower.replace('.', '').split())
        team_words = set(team_lower.split())
        if name_words & team_words:
            return row
    
    # Try removing common suffixes
    suffixes = ['wildcats', 'bulldogs', 'tigers', 'bears', 'eagles', 'hawks', 
                'cardinals', 'blue devils', 'tar heels', 'spartans', 'wolverines',
                'hoyas', 'friars', 'billikens', 'broncos', 'gaels', 'flyers']
    
    clean_name = name_lower
    for suffix in suffixes:
        clean_name = clean_name.replace(suffix, '').strip()
    
    for idx, row in df.iterrows():
        if clean_name in row['team'].lower():
            return row
    
    return None


def save_stats(df: pd.DataFrame, filename: str = 'barttorvik_stats.csv'):
    """Save stats to CSV."""
    DATA_DIR.mkdir(exist_ok=True)
    filepath = DATA_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"   Saved to {filepath}")
    return filepath


def main():
    """Fetch and save Barttorvik stats."""
    print("=" * 60)
    print("BARTTORVIK STATS FETCHER")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Fetch current season
    df = fetch_barttorvik_stats(2026)
    
    if df.empty:
        print("Failed to fetch stats")
        return
    
    # Show sample
    print(f"\nSample data (top 10 by rank):")
    print("-" * 60)
    cols = ['rank', 'team', 'conference', 'record', 'adj_o', 'adj_d', 'adj_tempo', 'est_ppg', 'est_total']
    print(df[cols].head(10).to_string(index=False))
    
    # Save
    print(f"\nSaving stats...")
    save_stats(df)
    
    # Quick matchup test
    print(f"\nSample matchup calculation:")
    print("-" * 60)
    matchup = calculate_matchup_total('Duke', 'North Carolina', df)
    if matchup.get('home_found') and matchup.get('away_found'):
        print(f"Duke vs North Carolina:")
        print(f"  Game tempo: {matchup['game_tempo']:.1f} possessions")
        print(f"  Duke expected: {matchup['home_expected']:.1f}")
        print(f"  UNC expected: {matchup['away_expected']:.1f}")
        print(f"  Expected total: {matchup['expected_total']:.1f}")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
