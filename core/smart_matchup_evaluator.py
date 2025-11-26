"""
SMART MATCHUP EVALUATOR v4
==========================
Evaluates CBB minimum total bets using NCAA team risk database.
Handles name matching between DraftKings (full names) and NCAA (short names).
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# File paths
DATA_DIR = Path(__file__).parent.parent / 'data'
RISK_DB_FILE = DATA_DIR / 'team_risk_database.json'

# Common mascots to strip from team names
MASCOTS = [
    'Wildcats', 'Tigers', 'Bears', 'Lions', 'Eagles', 'Hawks', 'Bulldogs',
    'Cardinals', 'Cavaliers', 'Cougars', 'Cowboys', 'Crimson Tide', 'Demons',
    'Devils', 'Ducks', 'Falcons', 'Gators', 'Golden Eagles', 'Hoosiers',
    'Hurricanes', 'Huskies', 'Jayhawks', 'Knights', 'Longhorns', 'Miners',
    'Mustangs', 'Orange', 'Owls', 'Panthers', 'Pioneers', 'Pirates', 'Raiders',
    'Rams', 'Razorbacks', 'Red Raiders', 'Rebels', 'Seminoles', 'Spartans',
    'Sun Devils', 'Tar Heels', 'Terrapins', 'Terriers', 'Thundering Herd',
    'Trojans', 'Volunteers', 'Wolfpack', 'Wolverines', 'Yellow Jackets',
    'Aggies', 'Badgers', 'Bearcats', 'Beavers', 'Bison', 'Blue Devils',
    'Boilermakers', 'Broncos', 'Bruins', 'Buckeyes', 'Buffaloes', 'Catamounts',
    'Commodores', 'Cornhuskers', 'Cyclones', 'Demon Deacons', 'Flames',
    'Flyers', 'Friars', 'Gamecocks', 'Gaels', 'Golden Gophers', 'Governors',
    'Greyhounds', 'Grizzlies', 'Highlanders', 'Hilltoppers', 'Hokies',
    'Horned Frogs', 'Illini', 'Jaguars', 'Jaspers', 'Kangaroos', 'Lumberjacks',
    'Mastodons', 'Matadors', 'Mean Green', 'Minutemen', 'Mocs', 'Monarchs',
    'Musketeers', 'Nittany Lions', 'Norse', 'Ospreys', 'Paladins', 'Peacocks',
    'Penguins', 'Phoenix', 'Pilots', 'Privateers', 'Purple Aces', 'Racers',
    'Rainbow Warriors', 'Rattlers', 'Red Foxes', 'Red Storm', 'Redhawks',
    'Redbirds', 'Runnin Bulldogs', 'Salukis', 'Scarlet Knights', 'Seahawks',
    'Seawolves', 'Shockers', 'Skyhawks', 'Sooners', 'Spiders', 'Stags',
    'Sycamores', 'Thunderbirds', 'Titans', 'Tribe', 'Tritons', 'Trojans',
    'Vandals', 'Vikings', 'Waves', 'Wolf Pack', 'Zips', 'Antelopes', 'Aztecs',
    'Banana Slugs', 'Battlin Bears', 'Beacons', 'Big Green', 'Buccaneers',
    'Bulls', 'Camels', 'Chanticleers', 'Chippewas', 'Clan', 'Cobras',
    'Colonels', 'Colonials', 'Coyotes', 'Crusaders', 'Delta Devils', 'Dolphins',
    'Dukes', 'Engineers', 'Express', 'Fighting Camels', 'Fighting Irish',
    'Fighting Scots', 'Firebirds', 'Golden Bears', 'Golden Flashes',
    'Golden Griffins', 'Golden Hurricane', 'Golden Knights', 'Golden Panthers',
    'Great Danes', 'Green Wave', 'Hatters', 'Hawkeyes', 'Heels', 'Hornets',
    'Ichabods', 'Jackrabbits', 'Jacks', 'Keydets', 'Lakers', 'Lancers',
    'Leathernecks', 'Leopards', 'Lobos', 'Lynx', 'Maple Leafs', 'Marauders',
    'Maroons', 'Mastiffs', 'Mavericks', 'Midshipmen', 'Moccasins', 'Mountaineers',
    'Mudcats', 'Nighthawks', 'Nor\'easters', 'Oles', 'Orangemen', 'Otters',
    'Paladins', 'Patriots', 'Pelicans', 'Phoenix', 'Pride', 'Privateers',
    'Purples', 'Quakers', 'Ramblers', 'Rangers', 'Ravens', 'Redskins',
    'Regals', 'River Hawks', 'Roadrunners', 'Rockets', 'Saints', 'Sammies',
    'Saxons', 'Screaming Eagles', 'Seagulls', 'Sentinels', 'Setters',
    'Sharks', 'Skippers', 'Spartans', 'Spirits', 'Stallions', 'Storm',
    'Sultans', 'Suns', 'Swarm', 'Tar', 'Tars', 'Texans', 'Thoroughbreds',
    'Tommies', 'Toppers', 'Toreros', 'Tornados', 'Tornadoes', 'Tribe',
    'Trojans', 'Troopers', 'Tuckers', 'Turtles', 'Twins', 'Vaqueros',
    'Voyagers', 'Vulcans', 'Warriors', 'Wasps', 'Westerners', 'Whalers',
    'Wildcats', 'Wolves', 'Wombats', 'Yellowjackets', 'Zips', 'Bearkats',
    '49ers', 'Bengals', 'Blue Jays', 'Bobcats', 'Bonnies', 'Broncs',
    'Braves', 'Canucks', 'Cavaliers', 'Centaurs', 'Chants', 'Chiefs',
    'Clippers', 'Conquistadors', 'Dons', 'Duhawks', 'Fighting Illini',
    'Friars', 'Gauchos', 'Hawks', 'Hoyas', 'Hounds', 'Kings', 'Lakers',
    'Lions', 'Lopes', 'Mastodons', 'Mavs', 'Metros', 'Monks', 'Mountain Hawks',
    'Nighthawks', 'Oaks', 'Orangewomen', 'Owls', 'Pack', 'Peacocks', 'Penmen',
    'Plainsmen', 'Pointers', 'Ponies', 'Raiders', 'Royals', 'Runnin', 'Saxons',
    'Scarlet', 'Screaming Eagles', 'Statesmen', 'Thunder', 'Thunderwolves',
    'Tommies', 'Wave', 'Wolves'
]

# Name mappings: DraftKings name -> NCAA short name
NAME_MAPPINGS = {
    # State abbreviations
    'uconn': 'uconn',
    'vcu': 'vcu',
    'lsu': 'lsu',
    'smu': 'smu',
    'tcu': 'tcu',
    'ucf': 'ucf',
    'unlv': 'unlv',
    'utep': 'utep',
    'usc': 'southern california',
    'ucla': 'ucla',
    'ole miss': 'ole miss',
    'uab': 'uab',
    'fiu': 'fiu',
    'fdu': 'fdu',
    'uic': 'uic',
    
    # Northern Iowa special case
    'northern iowa': 'uni',
    'uni': 'uni',
    
    # Saint/St variations
    "saint mary's": "saint mary's (ca)",
    "st. mary's": "saint mary's (ca)",
    "saint mary's gaels": "saint mary's (ca)",
    "st mary's": "saint mary's (ca)",
    
    "st. john's": "st. john's (ny)",
    "saint john's": "st. john's (ny)",
    "st john's": "st. john's (ny)",
    
    # Miami disambiguation
    'miami': 'miami (fl)',
    'miami (oh)': 'miami (oh)',
    'miami (fl)': 'miami (fl)',
    'miami redhawks': 'miami (oh)',
    'miami hurricanes': 'miami (fl)',
    
    # Louisiana schools
    'louisiana': 'louisiana',
    'louisiana tech': 'louisiana tech',
    'louisiana-lafayette': 'louisiana',
    'ul lafayette': 'louisiana',
    'louisiana-monroe': 'ulm',
    
    # NC schools
    'nc state': 'nc state',
    'nc st.': 'nc state',
    'north carolina st.': 'nc state',
    'north carolina state': 'nc state',
    'unc': 'north carolina',
    'north carolina': 'north carolina',
    
    # Tar Heels specific (in case mascot stripping fails)
    'north carolina tar heels': 'north carolina',
    
    # Other common variations
    'pitt': 'pittsburgh',
    'cal': 'california',
    'uva': 'virginia',
    'penn': 'pennsylvania',
    'umass': 'massachusetts',
    'unh': 'new hampshire',
    'uri': 'rhode island',
    
    # Southeastern Louisiana
    'southeastern la': 'southeastern la.',
    'southeastern la.': 'southeastern la.',
    'se louisiana': 'southeastern la.',
    'southeastern louisiana': 'southeastern la.',
    
    # UNCW / UNC Wilmington
    'unc wilmington': 'uncw',
    'uncw': 'uncw',
    
    # FIU/FDU
    "florida int'l": 'fiu',
    'florida international': 'fiu',
    'fairleigh dickinson': 'fdu',
    
    # Army
    'army': 'army west point',
    'army knights': 'army west point',
    
    # Grand Canyon
    'grand canyon': 'grand canyon',
    
    # App State
    'app state': 'app state',
    'appalachian st': 'app state',
    'appalachian st.': 'app state',
    'appalachian state': 'app state',
    
    # Sam Houston
    'sam houston st': 'sam houston',
    'sam houston st.': 'sam houston',
    'sam houston state': 'sam houston',
    
    # Southern schools
    'south fla': 'south fla.',
    'south fla.': 'south fla.',
    'south florida': 'south fla.',
    'usf': 'south fla.',
    
    # SE Missouri
    'se missouri st': 'southeast mo. st.',
    'se missouri st.': 'southeast mo. st.',
    'southeast missouri': 'southeast mo. st.',
    'southeast missouri st': 'southeast mo. st.',
    'southeast missouri st.': 'southeast mo. st.',
    
    # NJIT
    'njit': 'njit',
    
    # Long Beach State
    'long beach st': 'long beach st.',
    'long beach st.': 'long beach st.',
    'long beach state': 'long beach st.',
    
    # Colorado State
    'colorado st': 'colorado st.',
    'colorado st.': 'colorado st.',
    'colorado state': 'colorado st.',
    'csu': 'colorado st.',
    
    # San Diego State
    'san diego st': 'san diego st.',
    'san diego st.': 'san diego st.',
    'san diego state': 'san diego st.',
    'sdsu': 'san diego st.',
    
    # Fresno State
    'fresno st': 'fresno st.',
    'fresno st.': 'fresno st.',
    'fresno state': 'fresno st.',
    
    # Boise State
    'boise st': 'boise st.',
    'boise st.': 'boise st.',
    'boise state': 'boise st.',
    
    # Arizona State
    'arizona st': 'arizona st.',
    'arizona st.': 'arizona st.',
    'arizona state': 'arizona st.',
    'asu': 'arizona st.',
    
    # Michigan State
    'michigan st': 'michigan st.',
    'michigan st.': 'michigan st.',
    'michigan state': 'michigan st.',
    'msu': 'michigan st.',
    
    # Ohio State
    'ohio st': 'ohio st.',
    'ohio st.': 'ohio st.',
    'ohio state': 'ohio st.',
    'osu': 'ohio st.',
    
    # Penn State
    'penn st': 'penn st.',
    'penn st.': 'penn st.',
    'penn state': 'penn st.',
    'psu': 'penn st.',
    
    # Iowa State  
    'iowa st': 'iowa st.',
    'iowa st.': 'iowa st.',
    'iowa state': 'iowa st.',
    
    # Kansas State
    'kansas st': 'kansas st.',
    'kansas st.': 'kansas st.',
    'kansas state': 'kansas st.',
    'k-state': 'kansas st.',
    
    # Oklahoma State
    'oklahoma st': 'oklahoma st.',
    'oklahoma st.': 'oklahoma st.',
    'oklahoma state': 'oklahoma st.',
    'ok state': 'oklahoma st.',
    
    # Washington State
    'washington st': 'washington st.',
    'washington st.': 'washington st.',
    'washington state': 'washington st.',
    'wsu': 'washington st.',
    'wazzu': 'washington st.',
    
    # Oregon State
    'oregon st': 'oregon st.',
    'oregon st.': 'oregon st.',
    'oregon state': 'oregon st.',
    
    # Mississippi State
    'mississippi st': 'mississippi st.',
    'mississippi st.': 'mississippi st.',
    'mississippi state': 'mississippi st.',
    'miss state': 'mississippi st.',
    'miss st.': 'mississippi st.',
    
    # Utah State
    'utah st': 'utah st.',
    'utah st.': 'utah st.',
    'utah state': 'utah st.',
    
    # Ball State
    'ball st': 'ball st.',
    'ball st.': 'ball st.',
    'ball state': 'ball st.',
    
    # Kent State  
    'kent st': 'kent st.',
    'kent st.': 'kent st.',
    'kent state': 'kent st.',
    
    # Wichita State
    'wichita st': 'wichita st.',
    'wichita st.': 'wichita st.',
    'wichita state': 'wichita st.',
}


def load_risk_database() -> Dict:
    """Load the team risk database"""
    if not RISK_DB_FILE.exists():
        print(f"   ⚠️ Risk database not found at {RISK_DB_FILE}")
        return {}
    
    with open(RISK_DB_FILE, 'r') as f:
        db = json.load(f)
    
    updated = db.get('updated', 'unknown')[:10]
    teams_count = len(db.get('all_teams', {}))
    elite_count = len(db.get('elite_defense', {}))
    low_off_count = len(db.get('low_offense', {}))
    
    print(f"   Loaded risk database (updated: {updated})")
    print(f"   Teams tracked: {teams_count} | Elite def: {elite_count} | Low off: {low_off_count}")
    
    return db


def normalize_team_name(name: str) -> str:
    """
    Normalize a team name for matching.
    Strips mascots and converts to lowercase.
    Converts "State" to "St." to match NCAA format.
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower().strip()
    
    # Check explicit mappings first
    if normalized in NAME_MAPPINGS:
        return NAME_MAPPINGS[normalized]
    
    # Remove mascots (sort by length to remove longer ones first)
    for mascot in sorted(MASCOTS, key=len, reverse=True):
        mascot_lower = mascot.lower()
        if normalized.endswith(' ' + mascot_lower):
            normalized = normalized[:-len(mascot_lower)-1].strip()
            break
    
    # Check mappings again after mascot removal
    if normalized in NAME_MAPPINGS:
        return NAME_MAPPINGS[normalized]
    
    # CRITICAL: Convert "state" to "st." to match NCAA format
    # "iowa state" -> "iowa st."
    # "michigan state" -> "michigan st."
    normalized = normalized.replace(' state', ' st.')
    
    # Handle "St" without period -> "St."
    if ' st' in normalized and ' st.' not in normalized:
        normalized = normalized.replace(' st', ' st.')
    
    # Handle "Saint" -> check if should be different
    # Keep "saint" as is for saint mary's etc
    
    return normalized


def find_team_in_database(team_name: str, risk_db: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Find a team in the risk database.
    Returns (matched_name, team_data) or (None, None) if not found.
    """
    if not risk_db or 'all_teams' not in risk_db:
        return None, None
    
    all_teams = risk_db['all_teams']
    
    # Normalize the input name
    normalized = normalize_team_name(team_name)
    
    # Direct match
    if normalized in all_teams:
        return normalized, all_teams[normalized]
    
    # Try matching by checking if normalized name is contained in database keys
    for db_name, data in all_teams.items():
        db_normalized = db_name.lower()
        
        # Exact match
        if normalized == db_normalized:
            return db_name, data
        
        # Check if one contains the other (for partial matches)
        if len(normalized) >= 4 and len(db_normalized) >= 4:
            # "duke" matches "duke"
            if normalized == db_normalized:
                return db_name, data
            
            # "texas tech" in "texas tech" 
            if normalized in db_normalized or db_normalized in normalized:
                # Make sure it's a significant match (not just "a" in "alabama")
                if len(normalized) >= 5 or len(db_normalized) >= 5:
                    return db_name, data
    
    # Try matching by SEO slug if available
    for db_name, data in all_teams.items():
        seo_raw = data.get('seo', '')
        # Handle NaN or non-string values
        if seo_raw is None or (isinstance(seo_raw, float) and str(seo_raw) == 'nan'):
            continue
        seo = str(seo_raw).lower().replace('-', ' ')
        if seo and (normalized == seo or normalized in seo or seo in normalized):
            if len(normalized) >= 4:
                return db_name, data
    
    return None, None


def evaluate_matchup(game: Dict, risk_db: Dict) -> Dict:
    """
    Evaluate a single matchup for risk.
    
    Returns dict with:
    - recommendation: 'YES', 'NO', 'MAYBE'
    - confidence: 0-100
    - risk_score: total risk points
    - risk_factors: list of risk factors
    - teams_found: which teams were found in database
    """
    away_team = game.get('away_team', '')
    home_team = game.get('home_team', '')
    min_total = game.get('minimum_total')  # Column name from odds fetcher
    std_total = game.get('standard_total')
    
    # Handle NaN values
    import math
    if min_total is None or (isinstance(min_total, float) and math.isnan(min_total)):
        min_total = None
    if std_total is None or (isinstance(std_total, float) and math.isnan(std_total)):
        std_total = None
    
    # Skip if no alternate total
    if not min_total:
        return {
            'recommendation': 'SKIP',
            'confidence': 0,
            'risk_score': 0,
            'risk_factors': ['No alternate total available'],
            'teams_found': {'away': False, 'home': False},
            'away_team': away_team,
            'home_team': home_team,
            'min_total': None
        }
    
    # Find teams in database
    away_match, away_data = find_team_in_database(away_team, risk_db)
    home_match, home_data = find_team_in_database(home_team, risk_db)
    
    risk_score = 0
    risk_factors = []
    teams_found = {
        'away': away_match is not None,
        'home': home_match is not None,
        'away_name': away_match,
        'home_name': home_match
    }
    
    # Track if either team is unknown
    unknown_teams = []
    if not away_match:
        unknown_teams.append(away_team)
    if not home_match:
        unknown_teams.append(home_team)
    
    # Check risk categories
    elite_def = risk_db.get('elite_defense', {})
    low_off = risk_db.get('low_offense', {})
    slow_pace = risk_db.get('slow_pace', {})
    low_total = risk_db.get('low_total_teams', {})
    
    elite_def_count = 0
    low_off_count = 0
    slow_pace_count = 0
    
    # Check away team risks
    if away_match:
        away_lower = away_match.lower()
        
        if away_lower in elite_def:
            data = elite_def[away_lower]
            risk_score += data.get('risk', 18)
            tier = data.get('tier', 2)
            risk_factors.append(f"🛡️ {away_team} - Elite Defense T{tier} ({data.get('opp_ppg', 'N/A')} opp PPG)")
            elite_def_count += 1
        
        if away_lower in low_off:
            data = low_off[away_lower]
            risk_score += data.get('risk', 15)
            risk_factors.append(f"📉 {away_team} - Low Offense ({data.get('ppg', 'N/A')} PPG)")
            low_off_count += 1
        
        if away_lower in slow_pace:
            data = slow_pace[away_lower]
            risk_score += data.get('risk', 8)
            risk_factors.append(f"🐢 {away_team} - Slow Pace ({data.get('pace', 'N/A')})")
            slow_pace_count += 1
        
        if away_lower in low_total:
            data = low_total[away_lower]
            risk_score += data.get('risk', 5)
            risk_factors.append(f"📊 {away_team} - Low game totals (avg {data.get('total_avg', 'N/A')})")
    
    # Check home team risks
    if home_match:
        home_lower = home_match.lower()
        
        if home_lower in elite_def:
            data = elite_def[home_lower]
            risk_score += data.get('risk', 18)
            tier = data.get('tier', 2)
            risk_factors.append(f"🛡️ {home_team} - Elite Defense T{tier} ({data.get('opp_ppg', 'N/A')} opp PPG)")
            elite_def_count += 1
        
        if home_lower in low_off:
            data = low_off[home_lower]
            risk_score += data.get('risk', 15)
            risk_factors.append(f"📉 {home_team} - Low Offense ({data.get('ppg', 'N/A')} PPG)")
            low_off_count += 1
        
        if home_lower in slow_pace:
            data = slow_pace[home_lower]
            risk_score += data.get('risk', 8)
            risk_factors.append(f"🐢 {home_team} - Slow Pace ({data.get('pace', 'N/A')})")
            slow_pace_count += 1
        
        if home_lower in low_total:
            data = low_total[home_lower]
            risk_score += data.get('risk', 5)
            risk_factors.append(f"📊 {home_team} - Low game totals (avg {data.get('total_avg', 'N/A')})")
    
    # Compound risk: BOTH teams elite defense
    if elite_def_count >= 2:
        risk_score += 20
        risk_factors.append("🚨 BOTH teams elite defense - HIGH UNDER RISK")
    
    # Compound risk: BOTH teams low offense
    if low_off_count >= 2:
        risk_score += 15
        risk_factors.append("🚨 BOTH teams low offense - HIGH UNDER RISK")
    
    # Compound risk: BOTH teams slow pace
    if slow_pace_count >= 2:
        risk_score += 12
        risk_factors.append("🚨 BOTH teams slow pace")
    
    # Line-based risk
    if min_total:
        if min_total < 120:
            risk_score += 20
            risk_factors.append(f"⚠️ Very low line ({min_total})")
        elif min_total < 125:
            risk_score += 15
            risk_factors.append(f"⚠️ Low line ({min_total})")
        elif min_total < 130:
            risk_score += 8
            risk_factors.append(f"📊 Below average line ({min_total})")
    
    # Unknown team handling
    if unknown_teams:
        for ut in unknown_teams:
            risk_factors.append(f"❓ Unknown team (no data): {ut}")
    
    # Calculate confidence and recommendation
    # Base confidence: 92% (historical hit rate)
    # Risk factors reduce confidence
    base_confidence = 92
    confidence = max(40, base_confidence - risk_score)
    
    # Cap confidence for unknown teams
    if unknown_teams:
        confidence = min(confidence, 85)
    
    # Determine recommendation
    if risk_score >= 45:
        recommendation = 'NO'
        confidence = min(confidence, 50)
    elif risk_score >= 30:
        recommendation = 'MAYBE'
    else:
        recommendation = 'YES'
    
    return {
        'recommendation': recommendation,
        'confidence': confidence,
        'risk_score': risk_score,
        'risk_factors': risk_factors,
        'teams_found': teams_found,
        'unknown_teams': unknown_teams,
        'away_team': away_team,
        'home_team': home_team,
        'min_total': min_total,
        'std_total': std_total
    }


def evaluate_all_games(games: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Evaluate all games and return results with summary.
    """
    risk_db = load_risk_database()
    
    results = []
    for game in games:
        result = evaluate_matchup(game, risk_db)
        results.append(result)
    
    # Calculate summary
    summary = {
        'total': len(results),
        'analyzed': sum(1 for r in results if r['recommendation'] != 'SKIP'),
        'yes_verified': sum(1 for r in results if r['recommendation'] == 'YES' and not r.get('unknown_teams')),
        'yes_unverified': sum(1 for r in results if r['recommendation'] == 'YES' and r.get('unknown_teams')),
        'maybe': sum(1 for r in results if r['recommendation'] == 'MAYBE'),
        'no': sum(1 for r in results if r['recommendation'] == 'NO'),
        'skip': sum(1 for r in results if r['recommendation'] == 'SKIP'),
        'unknown_team_games': sum(1 for r in results if r.get('unknown_teams'))
    }
    
    return results, summary


def print_evaluation_report(results: List[Dict], summary: Dict):
    """Print formatted evaluation report"""
    print("\n" + "=" * 70)
    print("🏀 CBB MINIMUM TOTALS - SMART MATCHUP ANALYSIS")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Games: {summary['total']} | Analyzed: {summary['analyzed']}")
    print(f"Games with unknown teams: {summary['unknown_team_games']}")
    print("=" * 70)
    
    # NO picks
    no_picks = [r for r in results if r['recommendation'] == 'NO']
    if no_picks:
        print(f"\n🔴 NO PICKS ({len(no_picks)}) - SKIP THESE GAMES")
        print("-" * 50)
        for r in sorted(no_picks, key=lambda x: x['risk_score'], reverse=True):
            print(f"\n  {r['away_team']} @ {r['home_team']}")
            print(f"  Minimum: {r['min_total']} | Risk: {r['risk_score']} | Conf: {r['confidence']}%")
            for rf in r['risk_factors']:
                print(f"    {rf}")
    
    # MAYBE picks
    maybe_picks = [r for r in results if r['recommendation'] == 'MAYBE']
    if maybe_picks:
        print(f"\n🟡 MAYBE PICKS ({len(maybe_picks)}) - USE CAUTION")
        print("-" * 50)
        for r in sorted(maybe_picks, key=lambda x: x['confidence'], reverse=True):
            print(f"\n  {r['away_team']} @ {r['home_team']}")
            print(f"  Minimum: {r['min_total']} | Risk: {r['risk_score']} | Conf: {r['confidence']}%")
            for rf in r['risk_factors']:
                print(f"    {rf}")
    
    # YES picks - verified (both teams found)
    yes_verified = [r for r in results if r['recommendation'] == 'YES' and not r.get('unknown_teams')]
    if yes_verified:
        print(f"\n🟢 YES PICKS - VERIFIED ({len(yes_verified)}) - Both teams have data")
        print("-" * 50)
        
        # Group by confidence
        high_conf = [r for r in yes_verified if r['confidence'] >= 90]
        med_conf = [r for r in yes_verified if 80 <= r['confidence'] < 90]
        low_conf = [r for r in yes_verified if r['confidence'] < 80]
        
        if high_conf:
            print(f"\n  💪 HIGH CONFIDENCE ({len(high_conf)} games, 90%+)")
            for r in sorted(high_conf, key=lambda x: x['confidence'], reverse=True):
                factors = f" - {r['risk_factors'][0]}" if r['risk_factors'] else ""
                print(f"    • {r['away_team']} @ {r['home_team']} - O{r['min_total']} ({r['confidence']}%){factors}")
        
        if med_conf:
            print(f"\n  👍 MEDIUM CONFIDENCE ({len(med_conf)} games, 80-89%)")
            for r in sorted(med_conf, key=lambda x: x['confidence'], reverse=True):
                factors = f" - {r['risk_factors'][0]}" if r['risk_factors'] else ""
                print(f"    • {r['away_team']} @ {r['home_team']} - O{r['min_total']} ({r['confidence']}%){factors}")
        
        if low_conf:
            print(f"\n  🤔 LOWER CONFIDENCE ({len(low_conf)} games, <80%)")
            for r in sorted(low_conf, key=lambda x: x['confidence'], reverse=True):
                print(f"    • {r['away_team']} @ {r['home_team']} - O{r['min_total']} ({r['confidence']}%)")
                for rf in r['risk_factors']:
                    print(f"      {rf}")
    
    # YES picks - unverified (missing team data)
    yes_unverified = [r for r in results if r['recommendation'] == 'YES' and r.get('unknown_teams')]
    if yes_unverified:
        print(f"\n❓ YES PICKS - UNVERIFIED ({len(yes_unverified)}) - Missing team data")
        print("-" * 50)
        print("   ⚠️  These teams have NO statistical data in our database.")
        print("   USE YOUR JUDGMENT on these picks.\n")
        
        for r in sorted(yes_unverified, key=lambda x: x['min_total'] or 0):
            unknown = ", ".join(r.get('unknown_teams', []))
            print(f"    • {r['away_team']} @ {r['home_team']} - O{r['min_total']}")
            print(f"      ❓ No data: {unknown}")
    
    # Skipped
    skipped = [r for r in results if r['recommendation'] == 'SKIP']
    if skipped:
        print(f"\n⚪ SKIPPED ({len(skipped)}) - NO ALTERNATE TOTAL FROM DRAFTKINGS")
        for r in skipped:
            print(f"    • {r['away_team']} @ {r['home_team']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print(f"   🟢 YES (verified): {summary['yes_verified']} picks - Both teams have data")
    print(f"   ❓ YES (unverified): {summary['yes_unverified']} picks - Missing team data")
    print(f"   🟡 MAYBE: {summary['maybe']} picks")
    print(f"   🔴 NO: {summary['no']} picks")
    print(f"   ⚪ SKIP: {summary['skip']} (no alternate line)")
    print("=" * 70)


if __name__ == "__main__":
    # Test with sample data
    print("Smart Matchup Evaluator v4")
    print("Run with odds data to evaluate games")