"""
CBB Stats Collector - Using BALLDONTLIE API + ESPN Fallback
Collects real-time NCAAB team statistics and game data

PRIMARY: BALLDONTLIE API (Sign up FREE at: https://www.balldontlie.io/)
FALLBACK: ESPN Direct API (no key needed)
"""

import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.season_config import (
    CURRENT_SEASON, FOCUS_CONFERENCES, MIN_GAMES_FOR_ANALYSIS,
    DATA_DIR, TEAM_STATS_FILE
)
from config.api_config import BALLDONTLIE_API_KEY


class CBBStatsCollector:
    """
    Collect NCAAB team statistics using BALLDONTLIE API or ESPN fallback
    """
    
    BALLDONTLIE_URL = "https://api.balldontlie.io/v1"
    ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or BALLDONTLIE_API_KEY
        self.data_dir = Path(__file__).parent.parent / DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.team_stats = None
        self.completed_games = None
        self.use_balldontlie = bool(self.api_key)
        
        if not self.api_key:
            print("ℹ️ No BALLDONTLIE API key - using ESPN fallback")
            print("   For better data, sign up FREE at: https://www.balldontlie.io/")
    
    # ==================== BALLDONTLIE API METHODS ====================
    
    def _balldontlie_request(self, endpoint, params=None):
        """Make authenticated BALLDONTLIE API request"""
        if not self.api_key:
            return None
        
        url = f"{self.BALLDONTLIE_URL}{endpoint}"
        headers = {"Authorization": self.api_key}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print("❌ Invalid BALLDONTLIE API key")
                self.use_balldontlie = False
                return None
            elif response.status_code == 429:
                print("⏳ Rate limited, waiting...")
                time.sleep(60)
                return self._balldontlie_request(endpoint, params)
            else:
                print(f"❌ BALLDONTLIE Error {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ BALLDONTLIE request error: {e}")
            return None
    
    def get_balldontlie_teams(self):
        """Get NCAAB teams from BALLDONTLIE"""
        all_teams = []
        cursor = None
        
        while True:
            params = {"per_page": 100}
            if cursor:
                params["cursor"] = cursor
            
            data = self._balldontlie_request("/ncaab/teams", params)
            if not data:
                break
            
            teams = data.get("data", [])
            all_teams.extend(teams)
            
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break
            time.sleep(0.5)
        
        return all_teams
    
    def get_balldontlie_games(self, start_date, end_date):
        """Get NCAAB games from BALLDONTLIE"""
        all_games = []
        cursor = None
        
        while True:
            params = {
                "per_page": 100,
                "start_date": start_date,
                "end_date": end_date,
                "status": "Final"
            }
            if cursor:
                params["cursor"] = cursor
            
            data = self._balldontlie_request("/ncaab/games", params)
            if not data:
                break
            
            games = data.get("data", [])
            all_games.extend(games)
            
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break
            time.sleep(0.5)
        
        return all_games
    
    # ==================== ESPN FALLBACK METHODS ====================
    
    def _espn_request(self, endpoint):
        """Make ESPN API request (no auth needed)"""
        url = f"{self.ESPN_BASE_URL}{endpoint}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ ESPN Error {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ ESPN request error: {e}")
            return None
    
    def get_espn_teams(self):
        """Get teams from ESPN"""
        all_teams = []
        
        # ESPN returns teams in groups, need to paginate
        for page in range(1, 8):  # ~350 teams / 50 per page
            data = self._espn_request(f"/teams?limit=50&page={page}")
            
            if not data:
                break
            
            sports = data.get("sports", [])
            if sports:
                leagues = sports[0].get("leagues", [])
                if leagues:
                    teams = leagues[0].get("teams", [])
                    for t in teams:
                        team = t.get("team", {})
                        all_teams.append({
                            "id": team.get("id"),
                            "name": team.get("displayName"),
                            "abbreviation": team.get("abbreviation"),
                            "conference": team.get("groups", {}).get("parent", {}).get("name", "Unknown")
                        })
            
            time.sleep(0.5)
        
        return all_teams
    
    def get_espn_scoreboard(self, date_str):
        """Get games for a specific date from ESPN"""
        # Format: YYYYMMDD
        date_formatted = date_str.replace("-", "")
        data = self._espn_request(f"/scoreboard?dates={date_formatted}")
        
        if not data:
            return []
        
        games = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            
            competitors = competition.get("competitors", [])
            if len(competitors) != 2:
                continue
            
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            
            status = event.get("status", {}).get("type", {}).get("name", "")
            
            if status != "STATUS_FINAL":
                continue
            
            games.append({
                "id": event.get("id"),
                "date": event.get("date"),
                "home_team": home.get("team", {}).get("displayName"),
                "home_team_id": home.get("team", {}).get("id"),
                "away_team": away.get("team", {}).get("displayName"),
                "away_team_id": away.get("team", {}).get("id"),
                "home_score": int(home.get("score", 0)),
                "away_score": int(away.get("score", 0)),
                "total_score": int(home.get("score", 0)) + int(away.get("score", 0))
            })
        
        return games
    
    def get_espn_games_range(self, start_date, end_date):
        """Get ESPN games for a date range"""
        all_games = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            print(f"  Fetching {date_str}...", end=" ")
            
            games = self.get_espn_scoreboard(date_str)
            all_games.extend(games)
            
            print(f"{len(games)} games")
            
            current += timedelta(days=1)
            time.sleep(0.3)
        
        return all_games
    
    # ==================== UNIFIED STATS CALCULATION ====================
    
    def calculate_team_stats_from_games(self, games, team_name):
        """Calculate totals stats from games list"""
        team_scores = []
        opp_scores = []
        totals = []
        
        for game in games:
            home_team = game.get("home_team", "")
            away_team = game.get("away_team", "")
            home_score = game.get("home_score", 0)
            away_score = game.get("away_score", 0)
            
            if not home_score or not away_score:
                continue
            
            total = home_score + away_score
            totals.append(total)
            
            # Check if team was home or away (fuzzy match)
            team_lower = team_name.lower()
            if team_lower in str(home_team).lower():
                team_scores.append(home_score)
                opp_scores.append(away_score)
            elif team_lower in str(away_team).lower():
                team_scores.append(away_score)
                opp_scores.append(home_score)
        
        if len(totals) < MIN_GAMES_FOR_ANALYSIS:
            return None
        
        return {
            "games_played": len(totals),
            "avg_points_scored": round(np.mean(team_scores), 1) if team_scores else 0,
            "avg_points_allowed": round(np.mean(opp_scores), 1) if opp_scores else 0,
            "avg_total_points": round(np.mean(totals), 1),
            "std_total_points": round(np.std(totals), 1),
            "max_total_points": max(totals),
            "min_total_points": min(totals),
            "last_5_avg_scored": round(np.mean(team_scores[-5:]), 1) if len(team_scores) >= 5 else round(np.mean(team_scores), 1) if team_scores else 0,
            "last_5_avg_allowed": round(np.mean(opp_scores[-5:]), 1) if len(opp_scores) >= 5 else round(np.mean(opp_scores), 1) if opp_scores else 0,
            "last_5_avg_total": round(np.mean(totals[-5:]), 1) if len(totals) >= 5 else round(np.mean(totals), 1),
        }
    
    def collect_all_stats(self, save=True):
        """Collect stats using BALLDONTLIE or ESPN fallback"""
        print(f"Collecting NCAAB stats for {CURRENT_SEASON-1}-{CURRENT_SEASON} season...")
        print("=" * 60)
        
        # Date range
        start_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Try BALLDONTLIE first
        if self.use_balldontlie:
            print("Using BALLDONTLIE API...")
            return self._collect_with_balldontlie(start_date, end_date, save)
        else:
            print("Using ESPN fallback...")
            return self._collect_with_espn(start_date, end_date, save)
    
    def _collect_with_balldontlie(self, start_date, end_date, save):
        """Collect using BALLDONTLIE"""
        teams = self.get_balldontlie_teams()
        if not teams:
            print("❌ Failed to get teams, trying ESPN...")
            self.use_balldontlie = False
            return self._collect_with_espn(start_date, end_date, save)
        
        print(f"Found {len(teams)} teams")
        
        # Filter conferences
        if FOCUS_CONFERENCES:
            teams = [t for t in teams if t.get("conference") in FOCUS_CONFERENCES]
            print(f"Filtered to {len(teams)} teams in focus conferences")
        
        games = self.get_balldontlie_games(start_date, end_date)
        print(f"Found {len(games)} completed games")
        
        all_stats = []
        for i, team in enumerate(teams):
            team_id = team.get("id")
            team_name = team.get("full_name", team.get("name", "Unknown"))
            conference = team.get("conference", "Unknown")
            
            print(f"Processing {team_name} ({i+1}/{len(teams)})...")
            
            # Filter games for this team
            team_games = [
                {
                    "home_team": g.get("home_team", {}).get("full_name", ""),
                    "away_team": g.get("visitor_team", {}).get("full_name", ""),
                    "home_score": g.get("home_team_score", 0),
                    "away_score": g.get("visitor_team_score", 0)
                }
                for g in games
                if g.get("home_team", {}).get("id") == team_id or 
                   g.get("visitor_team", {}).get("id") == team_id
            ]
            
            stats = self.calculate_team_stats_from_games(team_games, team_name)
            if stats:
                stats["team_id"] = team_id
                stats["team"] = team_name
                stats["conference"] = conference
                all_stats.append(stats)
                print(f"  ✓ {stats['games_played']} games, Avg Total: {stats['avg_total_points']}")
        
        return self._finalize_stats(all_stats, save)
    
    def _collect_with_espn(self, start_date, end_date, save):
        """Collect using ESPN"""
        print("Fetching teams from ESPN...")
        teams = self.get_espn_teams()
        
        if not teams:
            print("❌ Failed to get teams from ESPN")
            return pd.DataFrame()
        
        print(f"Found {len(teams)} teams")
        
        # Filter conferences
        if FOCUS_CONFERENCES:
            teams = [t for t in teams if t.get("conference") in FOCUS_CONFERENCES]
            print(f"Filtered to {len(teams)} teams in focus conferences")
        
        print(f"\nFetching games from {start_date} to {end_date}...")
        games = self.get_espn_games_range(start_date, end_date)
        print(f"Found {len(games)} completed games")
        
        all_stats = []
        for i, team in enumerate(teams):
            team_name = team.get("name", "Unknown")
            conference = team.get("conference", "Unknown")
            
            print(f"Processing {team_name} ({i+1}/{len(teams)})...")
            
            # Filter games for this team
            team_lower = team_name.lower()
            team_games = [
                g for g in games
                if team_lower in str(g.get("home_team", "")).lower() or
                   team_lower in str(g.get("away_team", "")).lower()
            ]
            
            stats = self.calculate_team_stats_from_games(team_games, team_name)
            if stats:
                stats["team_id"] = team.get("id")
                stats["team"] = team_name
                stats["conference"] = conference
                all_stats.append(stats)
                print(f"  ✓ {stats['games_played']} games, Avg Total: {stats['avg_total_points']}")
        
        return self._finalize_stats(all_stats, save)
    
    def _finalize_stats(self, all_stats, save):
        """Save and return stats DataFrame"""
        self.team_stats = pd.DataFrame(all_stats)
        
        if save and not self.team_stats.empty:
            stats_path = self.data_dir / TEAM_STATS_FILE
            self.team_stats.to_csv(stats_path, index=False)
            print(f"\n✅ Saved {len(self.team_stats)} team stats to {stats_path}")
        
        return self.team_stats
    
    def load_existing_stats(self):
        """Load previously saved stats"""
        stats_path = self.data_dir / TEAM_STATS_FILE
        if stats_path.exists():
            self.team_stats = pd.read_csv(stats_path)
            file_time = datetime.fromtimestamp(stats_path.stat().st_mtime)
            age = datetime.now() - file_time
            print(f"Loaded {len(self.team_stats)} team stats (age: {age})")
            return self.team_stats
        return pd.DataFrame()


def main():
    """Main function"""
    collector = CBBStatsCollector()
    
    print("=" * 60)
    print("CBB STATS COLLECTOR")
    print("=" * 60)
    
    stats = collector.collect_all_stats()
    
    if not stats.empty:
        print("\n" + "=" * 60)
        print("TOP TEAMS BY AVERAGE TOTAL")
        print("=" * 60)
        top = stats.nlargest(10, "avg_total_points")[["team", "avg_total_points", "games_played"]]
        print(top.to_string(index=False))


if __name__ == "__main__":
    main()
