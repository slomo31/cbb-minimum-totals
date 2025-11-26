"""
Odds Minimum Fetcher - Fixed for Alternate Totals
Fetches MINIMUM alternate totals from DraftKings via The Odds API

KEY FIX: Alternate totals require the /events/{eventId}/odds endpoint
"""

import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.api_config import ODDS_API_KEY, ODDS_API_BASE_URL, ODDS_SPORT, PRIMARY_BOOKMAKER
from config.season_config import DATA_DIR, UPCOMING_GAMES_FILE


class OddsMinimumFetcher:
    """Fetch minimum alternate totals from DraftKings"""
    
    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.data_dir = Path(__file__).parent.parent / DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.remaining_requests = None
    
    def _request(self, endpoint, params=None):
        """Make API request"""
        url = f"{ODDS_API_BASE_URL}{endpoint}"
        if params is None:
            params = {}
        params['apiKey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            self.remaining_requests = response.headers.get('x-requests-remaining')
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   API Error {response.status_code}: {response.text[:100]}")
                return None
        except Exception as e:
            print(f"   Request error: {e}")
            return None
    
    def get_events(self):
        """Get list of upcoming NCAAB events"""
        print("   Fetching event list...")
        data = self._request(f"/sports/{ODDS_SPORT}/events")
        
        if data:
            print(f"   Found {len(data)} events")
        return data or []
    
    def get_standard_totals(self):
        """Get standard totals for all games (bulk endpoint)"""
        print("   Fetching standard totals...")
        params = {
            'regions': 'us',
            'markets': 'totals',
            'bookmakers': PRIMARY_BOOKMAKER,
            'oddsFormat': 'american'
        }
        return self._request(f"/sports/{ODDS_SPORT}/odds/", params)
    
    def get_alternate_totals_for_event(self, event_id):
        """Get alternate totals for a specific event"""
        params = {
            'regions': 'us',
            'markets': 'alternate_totals',
            'bookmakers': PRIMARY_BOOKMAKER,
            'oddsFormat': 'american'
        }
        return self._request(f"/sports/{ODDS_SPORT}/events/{event_id}/odds", params)
    
    def fetch_all_games_with_minimums(self, max_alt_lookups=100):
        """
        Fetch games with minimum alternate totals
        
        Strategy:
        1. Get all events
        2. Get standard totals (bulk - cheap)
        3. For top games, fetch alternate totals individually
        """
        print("=" * 60)
        print("FETCHING NCAAB ODDS WITH ALTERNATE TOTALS")
        print("=" * 60)
        
        # Step 1: Get events list
        events = self.get_events()
        if not events:
            print("❌ No events found")
            return pd.DataFrame()
        
        # Step 2: Get standard totals (all games, 1 API call)
        print("\n📊 Getting standard totals (bulk)...")
        std_data = self.get_standard_totals()
        
        # Build game dictionary from standard totals
        games = {}
        if std_data:
            for game in std_data:
                game_id = game.get('id')
                games[game_id] = {
                    'game_id': game_id,
                    'commence_time': game.get('commence_time'),
                    'home_team': game.get('home_team'),
                    'away_team': game.get('away_team'),
                    'standard_total': None,
                    'minimum_total': None,
                    'alternate_lines': [],
                    'has_alternate': False
                }
                
                # Parse date
                if games[game_id]['commence_time']:
                    try:
                        dt = datetime.fromisoformat(games[game_id]['commence_time'].replace('Z', '+00:00'))
                        games[game_id]['game_date'] = dt.strftime('%Y-%m-%d')
                        games[game_id]['game_time'] = dt.strftime('%H:%M')
                    except:
                        pass
                
                # Get standard total from DraftKings
                for book in game.get('bookmakers', []):
                    if book.get('key') == PRIMARY_BOOKMAKER:
                        for market in book.get('markets', []):
                            if market.get('key') == 'totals':
                                for outcome in market.get('outcomes', []):
                                    if outcome.get('name') == 'Over':
                                        games[game_id]['standard_total'] = outcome.get('point')
                                        games[game_id]['minimum_total'] = outcome.get('point')
                                        break
        
        print(f"   Got standard totals for {len(games)} games")
        
        # Step 3: Get alternate totals for events (individual calls)
        print(f"\n📊 Getting alternate totals (up to {max_alt_lookups} games)...")
        
        alt_count = 0
        for event in events[:max_alt_lookups]:
            event_id = event.get('id')
            if event_id not in games:
                continue
            
            print(f"   Checking {games[event_id]['away_team'][:20]} @ {games[event_id]['home_team'][:20]}...", end=" ")
            
            alt_data = self.get_alternate_totals_for_event(event_id)
            
            if alt_data:
                # Parse alternate totals
                for book in alt_data.get('bookmakers', []):
                    if book.get('key') == PRIMARY_BOOKMAKER:
                        for market in book.get('markets', []):
                            if market.get('key') == 'alternate_totals':
                                over_lines = []
                                for outcome in market.get('outcomes', []):
                                    if outcome.get('name') == 'Over':
                                        over_lines.append(outcome.get('point'))
                                
                                if over_lines:
                                    min_line = min(over_lines)
                                    games[event_id]['alternate_lines'] = sorted(over_lines)
                                    games[event_id]['minimum_total'] = min_line
                                    games[event_id]['has_alternate'] = True
                                    print(f"✓ Min: {min_line} (from {len(over_lines)} lines)")
                                    alt_count += 1
                                else:
                                    print("No over lines")
                            else:
                                print(f"Market: {market.get('key')}")
            else:
                print("No data")
            
            time.sleep(0.3)  # Rate limiting
        
        print(f"\n   Found alternate totals for {alt_count} games")
        print(f"   API requests remaining: {self.remaining_requests}")
        
        # Convert to DataFrame
        df = pd.DataFrame(list(games.values()))
        
        if not df.empty:
            df['fetch_time'] = datetime.now().isoformat()
            df = df.sort_values('commence_time')
            
            # Save
            output_path = self.data_dir / UPCOMING_GAMES_FILE
            df.to_csv(output_path, index=False)
            print(f"\n✅ Saved {len(df)} games to {output_path}")
            
            # Show games with alternates
            alt_games = df[df['has_alternate'] == True]
            if not alt_games.empty:
                print(f"\n🎯 Games with ALTERNATE totals ({len(alt_games)}):")
                for _, g in alt_games.head(10).iterrows():
                    print(f"   {g['away_team'][:25]} @ {g['home_team'][:25]}")
                    print(f"      Standard: {g['standard_total']} → Minimum: {g['minimum_total']}")
        
        return df


def main():
    fetcher = OddsMinimumFetcher()
    df = fetcher.fetch_all_games_with_minimums(max_alt_lookups=25)
    
    if not df.empty:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        with_alt = len(df[df['has_alternate'] == True])
        print(f"Total games: {len(df)}")
        print(f"With alternate totals: {with_alt}")
        print(f"Standard only: {len(df) - with_alt}")


if __name__ == "__main__":
    main()
