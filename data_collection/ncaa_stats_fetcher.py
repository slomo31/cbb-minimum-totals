"""
NCAA STATS FETCHER - Incremental Updates
=========================================
Pulls game data from NCAA API, saves to CSV, only fetches NEW games.
Rate limited: 5 requests/second max (we'll use 2/second to be safe)

Data saved to:
- data/ncaa_games_history.csv (all games)
- data/team_risk_database.json (calculated stats)
"""

import requests
import json
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set

# File paths
DATA_DIR = Path(__file__).parent.parent / 'data'
GAMES_CSV = DATA_DIR / 'ncaa_games_history.csv'
RISK_DB_FILE = DATA_DIR / 'team_risk_database.json'
FETCH_LOG = DATA_DIR / 'ncaa_fetch_log.json'

# NCAA API
NCAA_API_BASE = "https://ncaa-api.henrygd.me"
RATE_LIMIT_DELAY = 0.5  # 2 requests per second (safe margin)

# Season start date (2025-26 season started Nov 3, 2025)
SEASON_START = datetime(2025, 11, 3)


def load_fetch_log() -> Dict:
    """Load log of what dates we've already fetched"""
    if FETCH_LOG.exists():
        with open(FETCH_LOG, 'r') as f:
            return json.load(f)
    return {'dates_fetched': [], 'last_update': None}


def save_fetch_log(log: Dict):
    """Save fetch log"""
    log['last_update'] = datetime.now().isoformat()
    with open(FETCH_LOG, 'w') as f:
        json.dump(log, f, indent=2)


def load_existing_games() -> pd.DataFrame:
    """Load existing games from CSV"""
    if GAMES_CSV.exists():
        df = pd.read_csv(GAMES_CSV)
        print(f"   Loaded {len(df)} existing games from CSV")
        return df
    return pd.DataFrame()


def save_games(df: pd.DataFrame):
    """Save games to CSV"""
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(GAMES_CSV, index=False)
    print(f"   Saved {len(df)} games to {GAMES_CSV}")


def fetch_scoreboard_for_date(date_str: str) -> List[Dict]:
    """
    Fetch all games for a specific date from NCAA API
    
    Args:
        date_str: Date in YYYY/MM/DD format for NCAA API
        
    Returns:
        List of game dictionaries
    """
    # NCAA API uses format: /scoreboard/basketball-men/d1/YYYY/MM/DD
    url = f"{NCAA_API_BASE}/scoreboard/basketball-men/d1/{date_str}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            games = data.get('games', [])
            return games
        elif response.status_code == 429:
            print(f"   ⚠️ Rate limited! Waiting 60 seconds...")
            time.sleep(60)
            return fetch_scoreboard_for_date(date_str)  # Retry
        else:
            print(f"   Error {response.status_code} for {date_str}")
            return []
    except Exception as e:
        print(f"   Exception for {date_str}: {e}")
        return []


def parse_game(game_data: Dict, date: datetime) -> Dict:
    """Parse a single game from NCAA API response"""
    game = game_data.get('game', {})
    
    # Only process completed games
    if game.get('gameState') != 'final':
        return None
    
    away = game.get('away', {})
    home = game.get('home', {})
    
    # Get scores
    try:
        away_score = int(away.get('score', 0))
        home_score = int(home.get('score', 0))
    except (ValueError, TypeError):
        return None
    
    # Skip games with 0 scores
    if away_score == 0 or home_score == 0:
        return None
    
    return {
        'game_id': game.get('gameID'),
        'date': date.strftime('%Y-%m-%d'),
        'away_team': away.get('names', {}).get('short', 'Unknown'),
        'away_team_seo': away.get('names', {}).get('seo', ''),
        'away_score': away_score,
        'home_team': home.get('names', {}).get('short', 'Unknown'),
        'home_team_seo': home.get('names', {}).get('seo', ''),
        'home_score': home_score,
        'total_points': away_score + home_score,
        'home_win': home_score > away_score
    }


def fetch_new_games(start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
    """
    Fetch games we haven't fetched before (incremental update)
    
    Args:
        start_date: Start of range (defaults to season start)
        end_date: End of range (defaults to yesterday)
        
    Returns:
        DataFrame of new games
    """
    print("=" * 60)
    print("NCAA STATS FETCHER - Incremental Update")
    print("=" * 60)
    
    # Load fetch log to see what we've already done
    fetch_log = load_fetch_log()
    dates_fetched = set(fetch_log.get('dates_fetched', []))
    
    if fetch_log.get('last_update'):
        print(f"Last update: {fetch_log['last_update'][:10]}")
    print(f"Dates already fetched: {len(dates_fetched)}")
    
    # Set date range
    if start_date is None:
        start_date = SEASON_START
    if end_date is None:
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
    
    print(f"Checking date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Generate list of dates to fetch
    dates_to_fetch = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y/%m/%d')
        if date_str not in dates_fetched:
            dates_to_fetch.append(current)
        current += timedelta(days=1)
    
    print(f"New dates to fetch: {len(dates_to_fetch)}")
    
    if not dates_to_fetch:
        print("✅ Already up to date!")
        return pd.DataFrame()
    
    # Fetch games
    new_games = []
    for i, date in enumerate(dates_to_fetch):
        date_str = date.strftime('%Y/%m/%d')
        print(f"   [{i+1}/{len(dates_to_fetch)}] Fetching {date_str}...", end=" ")
        
        games = fetch_scoreboard_for_date(date_str)
        
        completed = 0
        for game_data in games:
            parsed = parse_game(game_data, date)
            if parsed:
                new_games.append(parsed)
                completed += 1
        
        print(f"{completed} completed games")
        
        # Mark date as fetched
        dates_fetched.add(date_str)
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
        
        # Save progress every 10 dates (in case of interruption)
        if (i + 1) % 10 == 0:
            fetch_log['dates_fetched'] = list(dates_fetched)
            save_fetch_log(fetch_log)
    
    # Final save of fetch log
    fetch_log['dates_fetched'] = list(dates_fetched)
    save_fetch_log(fetch_log)
    
    print(f"\n✅ Fetched {len(new_games)} new completed games")
    
    return pd.DataFrame(new_games)


def update_games_database():
    """
    Main function: Fetch new games and merge with existing data
    """
    # Fetch new games
    new_games_df = fetch_new_games()
    
    if new_games_df.empty:
        print("No new games to add")
        existing_df = load_existing_games()
        return existing_df
    
    # Load existing games
    existing_df = load_existing_games()
    
    # Merge (avoid duplicates based on game_id)
    if not existing_df.empty:
        existing_ids = set(existing_df['game_id'].astype(str))
        new_games_df = new_games_df[~new_games_df['game_id'].astype(str).isin(existing_ids)]
        all_games_df = pd.concat([existing_df, new_games_df], ignore_index=True)
    else:
        all_games_df = new_games_df
    
    # Sort by date
    all_games_df = all_games_df.sort_values('date', ascending=False)
    
    # Save
    save_games(all_games_df)
    
    return all_games_df


def calculate_team_stats(games_df: pd.DataFrame, min_games: int = 2) -> pd.DataFrame:
    """
    Calculate team stats from games history
    
    Args:
        games_df: DataFrame of all games
        min_games: Minimum games required to include team
        
    Returns:
        DataFrame with team stats
    """
    print("\n📊 Calculating team statistics...")
    
    team_stats = {}
    
    for _, game in games_df.iterrows():
        # Away team stats
        away = game['away_team']
        if away not in team_stats:
            team_stats[away] = {'points_for': [], 'points_against': [], 'seo': game['away_team_seo']}
        team_stats[away]['points_for'].append(game['away_score'])
        team_stats[away]['points_against'].append(game['home_score'])
        
        # Home team stats
        home = game['home_team']
        if home not in team_stats:
            team_stats[home] = {'points_for': [], 'points_against': [], 'seo': game['home_team_seo']}
        team_stats[home]['points_for'].append(game['home_score'])
        team_stats[home]['points_against'].append(game['away_score'])
    
    # Calculate averages
    stats_list = []
    for team, data in team_stats.items():
        games = len(data['points_for'])
        if games >= min_games:
            ppg = sum(data['points_for']) / games
            opp_ppg = sum(data['points_against']) / games
            total_avg = ppg + opp_ppg
            
            stats_list.append({
                'name': team,
                'seo': data['seo'],
                'games': games,
                'ppg': round(ppg, 1),
                'opp_ppg': round(opp_ppg, 1),
                'total_avg': round(total_avg, 1),
                'pace': round(total_avg * 0.55, 1)  # Rough pace estimate
            })
    
    stats_df = pd.DataFrame(stats_list)
    print(f"   Calculated stats for {len(stats_df)} teams with {min_games}+ games")
    
    return stats_df


def build_risk_database(stats_df: pd.DataFrame) -> Dict:
    """
    Build the risk database from team stats
    Top/bottom 20% for each category
    """
    print("\n🛡️ Building risk database...")
    
    if stats_df.empty:
        print("   No stats to build from!")
        return {}
    
    # Thresholds (20%)
    opp_ppg_threshold = stats_df['opp_ppg'].quantile(0.20)
    ppg_threshold = stats_df['ppg'].quantile(0.20)
    pace_threshold = stats_df['pace'].quantile(0.20)
    total_threshold = 140  # Games under 140 total are concerning
    
    print(f"   Elite Defense threshold: {opp_ppg_threshold:.1f} opp PPG or lower")
    print(f"   Low Offense threshold: {ppg_threshold:.1f} PPG or lower")
    print(f"   Slow Pace threshold: {pace_threshold:.1f} or lower")
    
    risk_db = {
        'updated': datetime.now().isoformat(),
        'source': 'ncaa_api',
        'teams_analyzed': len(stats_df),
        'thresholds': {
            'elite_defense_opp_ppg': round(opp_ppg_threshold, 1),
            'low_offense_ppg': round(ppg_threshold, 1),
            'slow_pace': round(pace_threshold, 1)
        },
        'elite_defense': {},
        'low_offense': {},
        'slow_pace': {},
        'low_total_teams': {},
        'all_teams': {}
    }
    
    # Store all teams for lookup
    for _, t in stats_df.iterrows():
        risk_db['all_teams'][t['name'].lower()] = {
            'ppg': t['ppg'],
            'opp_ppg': t['opp_ppg'],
            'total_avg': t['total_avg'],
            'games': t['games'],
            'seo': t['seo']
        }
    
    # Elite Defense (top 20% - lowest opp PPG)
    elite_def = stats_df[stats_df['opp_ppg'] <= opp_ppg_threshold].sort_values('opp_ppg')
    print(f"\n   🛡️ ELITE DEFENSES ({len(elite_def)} teams):")
    for _, t in elite_def.head(15).iterrows():
        if t['opp_ppg'] < 60:
            risk, tier = 22, 1
        elif t['opp_ppg'] < 65:
            risk, tier = 18, 2
        else:
            risk, tier = 14, 3
        
        risk_db['elite_defense'][t['name'].lower()] = {
            'opp_ppg': t['opp_ppg'],
            'games': t['games'],
            'risk': risk,
            'tier': tier
        }
        print(f"      {t['name'][:30]:30} - {t['opp_ppg']:.1f} opp PPG ({t['games']} games) T{tier}")
    
    # Low Offense (bottom 20% - lowest PPG)
    low_off = stats_df[stats_df['ppg'] <= ppg_threshold].sort_values('ppg')
    print(f"\n   📉 LOW OFFENSES ({len(low_off)} teams):")
    for _, t in low_off.head(15).iterrows():
        if t['ppg'] < 60:
            risk = 22
        elif t['ppg'] < 65:
            risk = 18
        else:
            risk = 12
        
        risk_db['low_offense'][t['name'].lower()] = {
            'ppg': t['ppg'],
            'games': t['games'],
            'risk': risk
        }
        print(f"      {t['name'][:30]:30} - {t['ppg']:.1f} PPG ({t['games']} games)")
    
    # Slow Pace (bottom 20%)
    slow = stats_df[stats_df['pace'] <= pace_threshold].sort_values('pace')
    print(f"\n   🐢 SLOW PACE ({len(slow)} teams):")
    for _, t in slow.head(15).iterrows():
        if t['pace'] < 70:
            risk = 12
        elif t['pace'] < 75:
            risk = 8
        else:
            risk = 5
        
        risk_db['slow_pace'][t['name'].lower()] = {
            'pace': t['pace'],
            'games': t['games'],
            'risk': risk
        }
        print(f"      {t['name'][:30]:30} - {t['pace']:.1f} pace ({t['games']} games)")
    
    # Low Total Teams
    low_total = stats_df[stats_df['total_avg'] <= total_threshold].sort_values('total_avg')
    print(f"\n   📊 LOW TOTAL GAMES ({len(low_total)} teams, avg under 140):")
    for _, t in low_total.head(10).iterrows():
        risk_db['low_total_teams'][t['name'].lower()] = {
            'total_avg': t['total_avg'],
            'games': t['games'],
            'risk': max(5, int((total_threshold - t['total_avg']) * 0.3))
        }
        print(f"      {t['name'][:30]:30} - {t['total_avg']:.1f} avg total ({t['games']} games)")
    
    # Save risk database
    with open(RISK_DB_FILE, 'w') as f:
        json.dump(risk_db, f, indent=2)
    
    print(f"\n✅ Risk database saved to {RISK_DB_FILE}")
    print(f"   Elite defenses: {len(risk_db['elite_defense'])} teams")
    print(f"   Low offenses: {len(risk_db['low_offense'])} teams")
    print(f"   Slow pace: {len(risk_db['slow_pace'])} teams")
    print(f"   Low total teams: {len(risk_db['low_total_teams'])} teams")
    print(f"   All teams tracked: {len(risk_db['all_teams'])}")
    
    return risk_db


def main():
    """Main execution: Update games and rebuild risk database"""
    print("=" * 60)
    print("NCAA STATS FETCHER")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Fetch new games (incremental)
    all_games_df = update_games_database()
    
    if all_games_df.empty:
        all_games_df = load_existing_games()
    
    if all_games_df.empty:
        print("❌ No games data available!")
        return
    
    print(f"\n📊 Total games in database: {len(all_games_df)}")
    print(f"   Date range: {all_games_df['date'].min()} to {all_games_df['date'].max()}")
    
    # Step 2: Calculate team stats
    stats_df = calculate_team_stats(all_games_df, min_games=2)
    
    # Step 3: Build risk database
    risk_db = build_risk_database(stats_df)
    
    print("\n" + "=" * 60)
    print("✅ UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()