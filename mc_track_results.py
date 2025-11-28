#!/usr/bin/env python3
"""
Monte Carlo Results Tracker - FIXED VERSION
Strict team name matching to prevent false matches
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import re

DATA_DIR = Path(__file__).parent / 'data'
MC_PICKS_FILE = DATA_DIR / 'monte_carlo_picks.csv'
MC_TRACKING_FILE = DATA_DIR / 'mc_tracking_results.csv'

NCAA_API = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"

# Team name mappings - normalize variations to a standard key
TEAM_NAME_MAP = {
    # Michigan schools
    'michigan st': 'michigan_st',
    'michigan st.': 'michigan_st',
    'michigan state': 'michigan_st',
    'michigan st spartans': 'michigan_st',
    'michigan state spartans': 'michigan_st',
    'mich st': 'michigan_st',
    'msu': 'michigan_st',
    'michigan': 'michigan',
    'michigan wolverines': 'michigan',
    
    # North Carolina schools - CRITICAL: these must be distinct
    'north carolina': 'north_carolina',
    'north carolina tar heels': 'north_carolina',
    'unc': 'north_carolina',
    'carolina': 'north_carolina',
    'tar heels': 'north_carolina',
    'east carolina': 'east_carolina',
    'east carolina pirates': 'east_carolina',
    'ecu': 'east_carolina',
    'north carolina st': 'nc_state',
    'north carolina st.': 'nc_state',
    'nc state': 'nc_state',
    'nc st': 'nc_state',
    'n.c. state': 'nc_state',
    'south carolina': 'south_carolina',
    'south carolina st': 'south_carolina_st',
    'south carolina st.': 'south_carolina_st',
    'sc state': 'south_carolina_st',
    
    # St. Bonaventure
    'st. bonaventure': 'st_bonaventure',
    'st bonaventure': 'st_bonaventure',
    'saint bonaventure': 'st_bonaventure',
    'st. bonaventure bonnies': 'st_bonaventure',
    'bonnies': 'st_bonaventure',
    
    # Richmond / Furman
    'richmond': 'richmond',
    'richmond spiders': 'richmond',
    'furman': 'furman',
    'furman paladins': 'furman',
    
    # UNLV / Rutgers
    'unlv': 'unlv',
    'unlv rebels': 'unlv',
    'rutgers': 'rutgers',
    'rutgers scarlet knights': 'rutgers',
    
    # Saint Louis / Santa Clara
    'saint louis': 'saint_louis',
    'st. louis': 'saint_louis',
    'st louis': 'saint_louis',
    'saint louis billikens': 'saint_louis',
    'billikens': 'saint_louis',
    'slu': 'saint_louis',
    'santa clara': 'santa_clara',
    'santa clara broncos': 'santa_clara',
    
    # BYU / Miami
    'byu': 'byu',
    'byu cougars': 'byu',
    'brigham young': 'byu',
    'miami': 'miami_fl',
    'miami hurricanes': 'miami_fl',
    'miami (fl)': 'miami_fl',
    'miami fl': 'miami_fl',
    'miami ohio': 'miami_oh',
    'miami (oh)': 'miami_oh',
    'miami oh': 'miami_oh',
    'miami redhawks': 'miami_oh',
    
    # Providence / Wisconsin
    'providence': 'providence',
    'providence friars': 'providence',
    'wisconsin': 'wisconsin',
    'wisconsin badgers': 'wisconsin',
    
    # Georgetown / Dayton
    'georgetown': 'georgetown',
    'georgetown hoyas': 'georgetown',
    'hoyas': 'georgetown',
    'dayton': 'dayton',
    'dayton flyers': 'dayton',
    'flyers': 'dayton',
    
    # Duke / Arkansas
    'duke': 'duke',
    'duke blue devils': 'duke',
    'blue devils': 'duke',
    'arkansas': 'arkansas',
    'arkansas razorbacks': 'arkansas',
    'razorbacks': 'arkansas',
    
    # Minnesota / Stanford
    'minnesota': 'minnesota',
    'minnesota golden gophers': 'minnesota',
    'golden gophers': 'minnesota',
    'stanford': 'stanford',
    'stanford cardinal': 'stanford',
    
    # Charlotte / Illinois St
    'charlotte': 'charlotte',
    'charlotte 49ers': 'charlotte',
    '49ers': 'charlotte',
    'illinois st': 'illinois_st',
    'illinois st.': 'illinois_st',
    'illinois state': 'illinois_st',
    'illinois st redbirds': 'illinois_st',
    'redbirds': 'illinois_st',
    
    # Vanderbilt / VCU
    'vanderbilt': 'vanderbilt',
    'vanderbilt commodores': 'vanderbilt',
    'commodores': 'vanderbilt',
    'vandy': 'vanderbilt',
    'vcu': 'vcu',
    'vcu rams': 'vcu',
    
    # Virginia Tech / Saint Mary's
    'virginia tech': 'virginia_tech',
    'virginia tech hokies': 'virginia_tech',
    'hokies': 'virginia_tech',
    'va tech': 'virginia_tech',
    'saint marys': 'saint_marys',
    "saint mary's": 'saint_marys',
    'st marys': 'saint_marys',
    "st. mary's": 'saint_marys',
    'saint marys gaels': 'saint_marys',
    "saint mary's (ca)": 'saint_marys',
    "saint marys (ca)": 'saint_marys',
    "st. mary's (ca)": 'saint_marys',
    'gaels': 'saint_marys',
    
    # Nevada / Washington - IMPORTANT: distinguish from Washington St
    'nevada': 'nevada',
    'nevada wolf pack': 'nevada',
    'wolf pack': 'nevada',
    'washington': 'washington',
    'washington huskies': 'washington',
    'huskies': 'washington',
    'uw': 'washington',
    'washington st': 'washington_st',
    'washington st.': 'washington_st',
    'washington state': 'washington_st',
    'washington st cougars': 'washington_st',
    'wazzu': 'washington_st',
    'wsu': 'washington_st',
    
    # Colorado / San Francisco
    'colorado': 'colorado',
    'colorado buffaloes': 'colorado',
    'buffaloes': 'colorado',
    'buffs': 'colorado',
    'san francisco': 'san_francisco',
    'san francisco dons': 'san_francisco',
    'usf': 'san_francisco',
    'dons': 'san_francisco',
    
    # Oregon / Creighton
    'oregon': 'oregon',
    'oregon ducks': 'oregon',
    'ducks': 'oregon',
    'creighton': 'creighton',
    'creighton bluejays': 'creighton',
    'bluejays': 'creighton',
    
    # TCU / Florida
    'tcu': 'tcu',
    'tcu horned frogs': 'tcu',
    'horned frogs': 'tcu',
    'florida': 'florida',
    'florida gators': 'florida',
    'gators': 'florida',
    
    # Colorado St / Wichita St
    'colorado st': 'colorado_st',
    'colorado st.': 'colorado_st',
    'colorado state': 'colorado_st',
    'colorado st rams': 'colorado_st',
    'wichita st': 'wichita_st',
    'wichita st.': 'wichita_st',
    'wichita state': 'wichita_st',
    'wichita st shockers': 'wichita_st',
    'shockers': 'wichita_st',
    
    # Oklahoma St / Northwestern
    'oklahoma st': 'oklahoma_st',
    'oklahoma st.': 'oklahoma_st',
    'oklahoma state': 'oklahoma_st',
    'oklahoma st cowboys': 'oklahoma_st',
    'cowboys': 'oklahoma_st',
    'osu': 'oklahoma_st',  # context dependent but defaulting
    'northwestern': 'northwestern',
    'northwestern wildcats': 'northwestern',
    
    # Western Kentucky / South Florida
    'western kentucky': 'western_kentucky',
    'western kentucky hilltoppers': 'western_kentucky',
    'wku': 'western_kentucky',
    'hilltoppers': 'western_kentucky',
    'south florida': 'south_florida',
    'south florida bulls': 'south_florida',
    'usf bulls': 'south_florida',
    's florida': 'south_florida',
    'sf bulls': 'south_florida',
}


def normalize_team_name(name):
    """Normalize team name to a standard key"""
    if not name:
        return None
    
    # Clean up the name
    clean = name.lower().strip()
    clean = re.sub(r'[^\w\s]', '', clean)  # Remove punctuation except spaces
    clean = re.sub(r'\s+', ' ', clean)  # Normalize whitespace
    
    # Direct lookup
    if clean in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[clean]
    
    # Try without common suffixes
    for suffix in ['wildcats', 'bulldogs', 'tigers', 'bears', 'eagles', 'hawks', 'knights']:
        test = clean.replace(suffix, '').strip()
        if test in TEAM_NAME_MAP:
            return TEAM_NAME_MAP[test]
    
    # Try first word(s) - handle "St." and "Saint" specially
    words = clean.split()
    if len(words) >= 2:
        # Try first two words
        two_word = ' '.join(words[:2])
        if two_word in TEAM_NAME_MAP:
            return TEAM_NAME_MAP[two_word]
        
        # Try first word only
        if words[0] in TEAM_NAME_MAP:
            return TEAM_NAME_MAP[words[0]]
    elif len(words) == 1:
        if words[0] in TEAM_NAME_MAP:
            return TEAM_NAME_MAP[words[0]]
    
    # Return cleaned name as fallback (will likely not match, which is safer)
    return clean.replace(' ', '_')


def strict_match(pick_home, pick_away, api_home, api_away):
    """
    Strictly match teams - both teams must match (tries both directions)
    Returns True only if we're confident this is the same game
    """
    pick_home_norm = normalize_team_name(pick_home)
    pick_away_norm = normalize_team_name(pick_away)
    api_home_norm = normalize_team_name(api_home)
    api_away_norm = normalize_team_name(api_away)
    
    # Try normal direction: pick_home=api_home, pick_away=api_away
    if pick_home_norm == api_home_norm and pick_away_norm == api_away_norm:
        return True
    
    # Try swapped direction: pick_home=api_away, pick_away=api_home
    # (handles cases where home/away are flipped between sources)
    if pick_home_norm == api_away_norm and pick_away_norm == api_home_norm:
        return True
    
    # Debug output for near-misses (one team matches but not the other)
    if (pick_home_norm == api_home_norm or pick_away_norm == api_away_norm or
        pick_home_norm == api_away_norm or pick_away_norm == api_home_norm):
        print(f"   ⚠️  Partial match: {pick_away}@{pick_home} vs {api_away}@{api_home}")
        print(f"       Normalized: {pick_away_norm}@{pick_home_norm} vs {api_away_norm}@{api_home_norm}")
    
    return False


def fetch_final_scores(date_str):
    """Fetch final scores from NCAA API"""
    url = f"{NCAA_API}/{date_str}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            games = data.get('games', [])
            
            results = []
            for game_wrapper in games:
                game = game_wrapper.get('game', game_wrapper)
                
                if game.get('gameState') == 'final' or game.get('finalMessage') == 'FINAL':
                    home = game.get('home', {})
                    away = game.get('away', {})
                    
                    home_names = home.get('names', {})
                    away_names = away.get('names', {})
                    
                    home_name = home_names.get('short', '') or home_names.get('full', '')
                    away_name = away_names.get('short', '') or away_names.get('full', '')
                    
                    try:
                        home_score = int(home.get('score', 0))
                        away_score = int(away.get('score', 0))
                    except:
                        continue
                    
                    total = home_score + away_score
                    
                    if home_name and away_name:
                        results.append({
                            'home_team': home_name,
                            'away_team': away_name,
                            'home_score': home_score,
                            'away_score': away_score,
                            'total': total
                        })
            
            return results
    except Exception as e:
        print(f"Error fetching scores: {e}")
    
    return []


def update_tracking():
    """Update Monte Carlo tracking with final scores"""
    
    # Load or initialize tracking
    if MC_TRACKING_FILE.exists():
        tracking = pd.read_csv(MC_TRACKING_FILE)
    else:
        picks = pd.read_csv(MC_PICKS_FILE) if MC_PICKS_FILE.exists() else pd.DataFrame()
        if picks.empty:
            print("No Monte Carlo picks found")
            return
        tracking = picks.copy()
        tracking['status'] = 'PENDING'
        tracking['result'] = ''
        tracking['actual_total'] = 0
        tracking['date_added'] = datetime.now().strftime('%Y-%m-%d')
    
    if tracking.empty:
        print("No tracking data")
        return
    
    # Get pending picks
    pending = tracking[tracking['status'] == 'PENDING']
    if pending.empty:
        print("No pending picks to update")
    
    # Fetch scores for last 5 days (to catch any missed games)
    all_scores = []
    for days_ago in range(0, 5):
        date = datetime.now() - timedelta(days=days_ago)
        date_str = date.strftime('%Y/%m/%d')
        print(f"📅 Checking {date_str}...")
        
        scores = fetch_final_scores(date_str)
        print(f"   Found {len(scores)} final games")
        all_scores.extend(scores)
    
    # Update each pending pick
    updated = 0
    for idx, row in tracking.iterrows():
        if row['status'] != 'PENDING':
            continue
            
        home = str(row.get('home_team', ''))
        away = str(row.get('away_team', ''))
        min_total = float(row.get('minimum_total', 0))
        
        # Try to find matching game with STRICT matching
        matched = False
        for score_data in all_scores:
            if strict_match(home, away, score_data['home_team'], score_data['away_team']):
                actual = score_data['total']
                tracking.at[idx, 'actual_total'] = actual
                tracking.at[idx, 'status'] = 'COMPLETE'
                
                if actual >= min_total:
                    tracking.at[idx, 'result'] = 'WIN'
                    print(f"   ✅ {away} @ {home}: {actual} >= {min_total} WIN")
                else:
                    tracking.at[idx, 'result'] = 'LOSS'
                    print(f"   ❌ {away} @ {home}: {actual} < {min_total} LOSS")
                
                updated += 1
                matched = True
                break
        
        if not matched and row['status'] == 'PENDING':
            # Show what we tried to match
            print(f"   ⏳ No match found for: {away} @ {home}")
    
    # Save
    tracking.to_csv(MC_TRACKING_FILE, index=False)
    print(f"\n✅ Updated {updated} games")
    
    # Print summary
    print_summary(tracking)


def print_summary(tracking):
    """Print results summary"""
    complete = tracking[tracking['status'] == 'COMPLETE']
    pending = tracking[tracking['status'] == 'PENDING']
    
    print(f"\n" + "=" * 60)
    print(f"📊 MONTE CARLO RESULTS SUMMARY")
    print(f"=" * 60)
    
    if not complete.empty:
        # YES picks only (what we actually bet on)
        yes_complete = complete[complete['decision'] == 'YES']
        yes_wins = len(yes_complete[yes_complete['result'] == 'WIN'])
        yes_losses = len(yes_complete[yes_complete['result'] == 'LOSS'])
        
        print(f"\n🎯 YES PICKS (bets placed):")
        print(f"   Record: {yes_wins}-{yes_losses}")
        if yes_wins + yes_losses > 0:
            print(f"   Win rate: {yes_wins/(yes_wins+yes_losses)*100:.1f}%")
        
        # Show YES losses with details
        yes_loss_games = yes_complete[yes_complete['result'] == 'LOSS']
        if not yes_loss_games.empty:
            print(f"\n❌ YES PICK LOSSES:")
            for _, game in yes_loss_games.iterrows():
                missed_by = game['minimum_total'] - game['actual_total']
                print(f"   {game['away_team']} @ {game['home_team']}")
                print(f"      Min: {game['minimum_total']} | Actual: {game['actual_total']} | Missed by: {missed_by:.1f}")
                print(f"      Confidence: {game.get('hit_rate', 'N/A')}% | Sim Mean: {game.get('sim_mean', 'N/A')}")
        
        # NO/MAYBE picks for reference
        no_complete = complete[complete['decision'].isin(['NO', 'MAYBE'])]
        if not no_complete.empty:
            no_would_win = len(no_complete[no_complete['result'] == 'WIN'])
            no_would_loss = len(no_complete[no_complete['result'] == 'LOSS'])
            print(f"\n📋 NO/MAYBE PICKS (not bet, for reference):")
            print(f"   Would have been: {no_would_win}-{no_would_loss}")
    
    # Pending
    yes_pending = pending[pending['decision'] == 'YES'] if not pending.empty else pd.DataFrame()
    if not yes_pending.empty:
        print(f"\n⏳ PENDING YES PICKS ({len(yes_pending)}):")
        for _, game in yes_pending.iterrows():
            print(f"   {game['away_team']} @ {game['home_team']} OVER {game['minimum_total']}")


def recheck_all():
    """Re-check ALL completed games to verify accuracy"""
    print("=" * 60)
    print("🔍 RE-CHECKING ALL COMPLETED RESULTS")
    print("=" * 60)
    
    if not MC_TRACKING_FILE.exists():
        print("No tracking file found")
        return
    
    tracking = pd.read_csv(MC_TRACKING_FILE)
    
    # Reset all completed games to pending for re-check
    tracking.loc[tracking['status'] == 'COMPLETE', 'status'] = 'PENDING'
    tracking.loc[tracking['status'] == 'PENDING', 'result'] = ''
    tracking.loc[tracking['status'] == 'PENDING', 'actual_total'] = 0
    
    tracking.to_csv(MC_TRACKING_FILE, index=False)
    
    # Now run normal update
    update_tracking()


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("🎲 MONTE CARLO RESULTS TRACKER (FIXED)")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--recheck':
        recheck_all()
    else:
        update_tracking()