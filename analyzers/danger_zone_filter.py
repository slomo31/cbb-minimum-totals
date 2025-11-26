"""
Danger Zone Filter
Flags games at risk of going under 130 total
"""

# Teams known for elite defense / slow pace
ELITE_DEFENSE_TEAMS = [
    'Houston Cougars',
    'Texas Tech Red Raiders', 
    'Virginia Cavaliers',
    'San Diego State Aztecs',
    'Saint Mary\'s Gaels',
    'Princeton Tigers',
    'Yale Bulldogs',
    'Kansas Jayhawks',
    'UConn Huskies',
    'Tennessee Volunteers',
    'Texas A&M Aggies',
    'Auburn Tigers',
    'UCLA Bruins',
    'Michigan State Spartans',
    'Purdue Boilermakers',
]

# Teams known for very low scoring
LOW_OFFENSE_TEAMS = [
    'Oakland City',
    'Lyon Scots',
    'Maryland Eastern Shore',
    'Bryant Bulldogs',
    'Merrimack Warriors',
    'Sacramento State',
    'Lehigh',
    'Towson Tigers',
]


def check_danger_zone(home_team, away_team, minimum_total):
    """
    Check if a game is in the danger zone (risk of under 130)
    
    Returns:
        dict with is_danger, reason, risk_level
    """
    warnings = []
    risk_level = 0
    
    # Check for elite defense teams
    for team in ELITE_DEFENSE_TEAMS:
        if team.lower() in home_team.lower() or team.lower() in away_team.lower():
            warnings.append(f"Elite defense: {team}")
            risk_level += 2
    
    # Check for low offense teams
    for team in LOW_OFFENSE_TEAMS:
        if team.lower() in home_team.lower() or team.lower() in away_team.lower():
            warnings.append(f"Low offense: {team}")
            risk_level += 3
    
    # Check if minimum is already low
    if minimum_total < 125:
        warnings.append(f"Very low line: {minimum_total}")
        risk_level += 2
    elif minimum_total < 130:
        warnings.append(f"Low line: {minimum_total}")
        risk_level += 1
    
    # Determine danger status
    is_danger = risk_level >= 2
    
    return {
        'is_danger': is_danger,
        'risk_level': risk_level,
        'warnings': warnings,
        'recommendation': 'SKIP' if risk_level >= 3 else 'CAUTION' if is_danger else 'OK'
    }


def filter_predictions(predictions_df):
    """Add danger zone flags to predictions"""
    
    results = []
    for _, row in predictions_df.iterrows():
        danger = check_danger_zone(
            row.get('home_team', ''),
            row.get('away_team', ''),
            row.get('minimum_total', 150)
        )
        
        results.append({
            **row.to_dict(),
            'is_danger_zone': danger['is_danger'],
            'danger_risk_level': danger['risk_level'],
            'danger_warnings': '; '.join(danger['warnings']),
            'danger_recommendation': danger['recommendation']
        })
    
    return results


if __name__ == "__main__":
    # Test
    test_games = [
        ("Houston Cougars", "Notre Dame Fighting Irish", 132.5),
        ("Alabama Crimson Tide", "Maryland Terrapins", 166.5),
        ("Princeton Tigers", "Vermont Catamounts", 130.5),
        ("Auburn Tigers", "St. John's Red Storm", 154.5),
    ]
    
    print("🚨 DANGER ZONE TEST")
    print("=" * 60)
    
    for home, away, minimum in test_games:
        result = check_danger_zone(home, away, minimum)
        icon = '🔴' if result['recommendation'] == 'SKIP' else '🟡' if result['is_danger'] else '🟢'
        print(f"\n{icon} {away} @ {home}")
        print(f"   Minimum: {minimum}")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Recommendation: {result['recommendation']}")
        if result['warnings']:
            print(f"   Warnings: {', '.join(result['warnings'])}")
