"""
DYNAMIC TEAM RISK DATABASE - EXPANDED
=====================================
Uses top 25% thresholds and adds more risk categories
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

RISK_DB_FILE = Path(__file__).parent.parent / 'data' / 'team_risk_database.json'


def fetch_kenpom_style_stats() -> pd.DataFrame:
    """Fetch team stats from ESPN game results"""
    print("Fetching team statistics from ESPN...")
    
    team_scores = {}
    base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    
    # Fetch last 30 days
    for days_ago in range(0, 30):
        date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
        try:
            response = requests.get(f"{base_url}?dates={date}", timeout=15)
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                for event in events:
                    status = event.get('status', {}).get('type', {})
                    if status.get('completed', False):
                        competitions = event.get('competitions', [])
                        if competitions:
                            comp = competitions[0]
                            competitors = comp.get('competitors', [])
                            
                            if len(competitors) == 2:
                                team1 = competitors[0]
                                team2 = competitors[1]
                                
                                t1_name = team1.get('team', {}).get('displayName', '').lower()
                                t2_name = team2.get('team', {}).get('displayName', '').lower()
                                
                                try:
                                    t1_score = int(team1.get('score', 0))
                                    t2_score = int(team2.get('score', 0))
                                except:
                                    continue
                                
                                if t1_name and t2_name and t1_score > 0 and t2_score > 0:
                                    if t1_name not in team_scores:
                                        team_scores[t1_name] = []
                                    if t2_name not in team_scores:
                                        team_scores[t2_name] = []
                                    
                                    team_scores[t1_name].append((t1_score, t2_score))
                                    team_scores[t2_name].append((t2_score, t1_score))
        except:
            continue
        
        if days_ago % 10 == 0:
            print(f"   Processed {days_ago} days back...")
    
    print(f"   Collected data for {len(team_scores)} teams")
    
    # Calculate averages - lower threshold to 2 games
    teams = []
    for team, scores in team_scores.items():
        if len(scores) >= 2:  # Lowered from 3
            ppg = sum(s[0] for s in scores) / len(scores)
            opp_ppg = sum(s[1] for s in scores) / len(scores)
            total_avg = ppg + opp_ppg
            
            teams.append({
                'name': team,
                'games': len(scores),
                'ppg': round(ppg, 1),
                'opp_ppg': round(opp_ppg, 1),
                'total_avg': round(total_avg, 1),
                'pace': round(total_avg * 0.55, 1)  # Rough pace estimate
            })
    
    print(f"   Calculated stats for {len(teams)} teams (2+ games)")
    
    return pd.DataFrame(teams)


def update_risk_database():
    """Update the risk database with current stats - EXPANDED thresholds"""
    print("=" * 60)
    print("UPDATING TEAM RISK DATABASE (EXPANDED)")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats_df = fetch_kenpom_style_stats()
    
    if stats_df.empty:
        print("❌ Could not fetch team stats")
        return None
    
    print(f"\n📊 Stats Summary ({len(stats_df)} teams):")
    
    # Best defenses (lowest opponent PPG) - TOP 25%
    print("\n🛡️ ELITE DEFENSES (top 25% - lowest opp PPG):")
    opp_ppg_25 = stats_df['opp_ppg'].quantile(0.25)
    print(f"   Threshold: {opp_ppg_25:.1f} opp PPG or lower")
    best_def = stats_df[stats_df['opp_ppg'] <= opp_ppg_25].sort_values('opp_ppg')
    for _, t in best_def.iterrows():
        print(f"   {t['name'][:35]:35} - Opp PPG: {t['opp_ppg']:.1f} ({t['games']} games)")
    
    # Worst offenses (lowest PPG) - BOTTOM 25%
    print("\n📉 LOW OFFENSES (bottom 25% - lowest PPG):")
    ppg_25 = stats_df['ppg'].quantile(0.25)
    print(f"   Threshold: {ppg_25:.1f} PPG or lower")
    worst_off = stats_df[stats_df['ppg'] <= ppg_25].sort_values('ppg')
    for _, t in worst_off.iterrows():
        print(f"   {t['name'][:35]:35} - PPG: {t['ppg']:.1f} ({t['games']} games)")
    
    # Slowest pace - BOTTOM 25%
    print("\n🐢 SLOW PACE (bottom 25%):")
    pace_25 = stats_df['pace'].quantile(0.25)
    print(f"   Threshold: {pace_25:.1f} or lower")
    slow = stats_df[stats_df['pace'] <= pace_25].sort_values('pace')
    for _, t in slow.iterrows():
        print(f"   {t['name'][:35]:35} - Pace: {t['pace']:.1f} ({t['games']} games)")
    
    # Lowest scoring games (teams whose games average lowest totals)
    print("\n📉 LOW TOTAL TEAMS (games avg under 140):")
    low_total = stats_df[stats_df['total_avg'] <= 140].sort_values('total_avg')
    for _, t in low_total.iterrows():
        print(f"   {t['name'][:35]:35} - Avg Total: {t['total_avg']:.1f} ({t['games']} games)")
    
    # Build risk database
    risk_db = {
        'updated': datetime.now().isoformat(),
        'source': 'espn_game_logs',
        'teams_analyzed': len(stats_df),
        'thresholds': {
            'elite_defense_opp_ppg': opp_ppg_25,
            'low_offense_ppg': ppg_25,
            'slow_pace': pace_25
        },
        'elite_defense': {},
        'low_offense': {},
        'slow_pace': {},
        'low_total_teams': {},
        'all_teams': {}  # Store all team stats for reference
    }
    
    # Store all teams
    for _, t in stats_df.iterrows():
        risk_db['all_teams'][t['name']] = {
            'ppg': t['ppg'],
            'opp_ppg': t['opp_ppg'],
            'total_avg': t['total_avg'],
            'games': t['games']
        }
    
    # Elite defense: top 25%
    for _, t in best_def.iterrows():
        # Risk scales with how dominant the defense is
        # Lower opp_ppg = higher risk
        if t['opp_ppg'] < 60:
            risk = 22
            tier = 1
        elif t['opp_ppg'] < 64:
            risk = 18
            tier = 2
        else:
            risk = 14
            tier = 3
        
        risk_db['elite_defense'][t['name']] = {
            'opp_ppg': t['opp_ppg'],
            'games': t['games'],
            'risk': risk,
            'tier': tier
        }
    
    # Low offense: bottom 25%
    for _, t in worst_off.iterrows():
        if t['ppg'] < 65:
            risk = 20
        elif t['ppg'] < 72:
            risk = 15
        else:
            risk = 10
        
        risk_db['low_offense'][t['name']] = {
            'ppg': t['ppg'],
            'games': t['games'],
            'risk': risk
        }
    
    # Slow pace: bottom 25%
    for _, t in slow.iterrows():
        if t['pace'] < 75:
            risk = 12
        elif t['pace'] < 80:
            risk = 8
        else:
            risk = 5
        
        risk_db['slow_pace'][t['name']] = {
            'pace': t['pace'],
            'games': t['games'],
            'risk': risk
        }
    
    # Low total teams (games consistently under 140)
    for _, t in low_total.iterrows():
        risk_db['low_total_teams'][t['name']] = {
            'total_avg': t['total_avg'],
            'games': t['games'],
            'risk': max(5, int((140 - t['total_avg']) * 0.5))
        }
    
    # Save
    RISK_DB_FILE.parent.mkdir(exist_ok=True)
    with open(RISK_DB_FILE, 'w') as f:
        json.dump(risk_db, f, indent=2)
    
    print(f"\n✅ Risk database saved to {RISK_DB_FILE}")
    print(f"   Elite defenses: {len(risk_db['elite_defense'])} teams")
    print(f"   Low offenses: {len(risk_db['low_offense'])} teams")
    print(f"   Slow pace: {len(risk_db['slow_pace'])} teams")
    print(f"   Low total teams: {len(risk_db['low_total_teams'])} teams")
    print(f"   All teams tracked: {len(risk_db['all_teams'])}")
    
    return risk_db


if __name__ == "__main__":
    update_risk_database()
