"""Fetch ESPN read-only data and publish an allowlisted snapshot. Never log cookies."""
import json, os, sys, math, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode, unquote

ROOT = Path(__file__).resolve().parents[1]
POS = {0:'PG',1:'SG',2:'SF',3:'PF',4:'C',5:'G',6:'F',7:'SG/SF',8:'G/F',9:'PF/C',10:'F/C',11:'UTIL',12:'BE',13:'IR'}

def fetch(url, headers):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                data = json.load(response)
            if not isinstance(data, dict) or 'messages' in data:
                raise ValueError('Unexpected ESPN response')
            return data
        except Exception:
            if attempt == 2:
                raise RuntimeError('ESPN fetch failed. Check season, access, and ESPN secrets; previous deployment remains intact.') from None
            time.sleep(2 ** attempt)

def player(p, year, weights):
    def stat(source, season):
        return next((s for s in p.get('stats',[]) if s.get('seasonId')==season and s.get('statSourceId')==source and s.get('statSplitTypeId')==0 and s.get('scoringPeriodId')==0 and s.get('stats')), None)
    def points(s):
        if s is None: return None
        stats=s['stats']
        if any(str(k) not in stats for k in weights): return None
        return round(sum(stats[str(k)]*v for k,v in weights.items()),2)
    forecast, prior = stat(1, year), stat(0, year-1)
    total, last = points(forecast), points(prior)
    games=forecast.get('stats',{}).get('42') if forecast else None
    return {'id':p['id'],'name':p.get('fullName','Unknown player'),'positions':[POS[i] for i in p.get('eligibleSlots',[]) if i<=4], 'status':p.get('injuryStatus','UNKNOWN'), 'projection':total,'games':games,'ppg':round(total/games,2) if total is not None and games else None,'blend':round(.75*total+.25*last,2) if total is not None and last is not None else total,'prior':last,'adp':p.get('ownership',{}).get('averageDraftPosition')}

def normalize(league, pool, year, team_id):
    scoring=league['settings']['scoringSettings']
    if scoring['scoringType'] != 'H2H_POINTS': raise ValueError('This model requires H2H points scoring.')
    if any(s.get('pointsOverrides') for s in scoring['scoringItems']): raise ValueError('Position-specific scoring requires a model update.')
    weights={s['statId']:s['points'] for s in scoring['scoringItems']}
    players={}; teams=[]
    for t in league['teams']:
        ids=[]
        for entry in t.get('roster',{}).get('entries',[]):
            p=entry['playerPoolEntry']['player']; row=player(p,year,weights)
            row.update(teamId=t['id'],slot=POS.get(entry['lineupSlotId'],'?'))
            players[p['id']]=row; ids.append(p['id'])
        record=t.get('record',{}).get('overall',{})
        teams.append({'id':t['id'],'name':t.get('name') or ' '.join([t.get('location',''),t.get('nickname','')]).strip() or f"Team {t['id']}",'players':ids,'wins':record.get('wins',0),'losses':record.get('losses',0)})
    for entry in pool:
        p=entry.get('player',{})
        if p.get('id') and p['id'] not in players:
            row=player(p,year,weights); row.update(teamId=entry.get('onTeamId',0),slot=None); players[p['id']]=row
    picks=[{k:p.get(k) for k in ('overallPickNumber','roundId','roundPickNumber','playerId','teamId')} for p in league.get('draftDetail',{}).get('picks',[])]
    schedule=[]
    for match in league.get('schedule',[]):
        if 'home' in match and 'away' in match:
            schedule.append({'period':match['matchupPeriodId'],'home':match['home']['teamId'],'away':match['away']['teamId'],'homeScore':match['home'].get('totalPoints',0),'awayScore':match['away'].get('totalPoints',0),'winner':match.get('winner')})
    return {'updatedAt':datetime.now(timezone.utc).isoformat(),'leagueId':league['id'],'season':year,'name':league['settings']['name'],'myTeamId':team_id,'scoringType':scoring['scoringType'],'scoring':weights,'period':league['status']['currentMatchupPeriod'],'draft':{'complete':league.get('draftDetail',{}).get('drafted',False),'inProgress':league.get('draftDetail',{}).get('inProgress',False),'picks':picks},'teams':teams,'players':list(players.values()),'schedule':schedule}

def main():
    year=int(os.getenv('ESPN_SEASON','2027')); league_id=int(os.getenv('ESPN_LEAGUE_ID','618015977'))
    headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'}
    if os.getenv('ESPN_S2') and os.getenv('ESPN_SWID'):
        headers['Cookie']='espn_s2='+unquote(os.environ['ESPN_S2'])+'; SWID='+os.environ['ESPN_SWID']
    base=f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{year}/segments/0/leagues/{league_id}'
    league=fetch(base+'?'+urlencode({'view':['mSettings','mTeam','mRoster','mDraftDetail','mMatchup']},doseq=True),headers)
    pool=[]
    for offset in range(0,10000,500):
        h={**headers,'x-fantasy-filter':json.dumps({'players':{'limit':500,'offset':offset,'sortPercOwned':{'sortPriority':1,'sortAsc':False}}})}
        page=fetch(base+'?view=kona_player_info',h).get('players')
        if not isinstance(page,list): raise ValueError('Missing player pool')
        if offset and page and page[0].get('id')==pool[0].get('id'): raise ValueError('ESPN ignored pagination')
        pool.extend(page)
        if len(page)<500: break
    else: raise ValueError('Player pool exceeded pagination limit')
    data=normalize(league,pool,year,int(os.getenv('ESPN_TEAM_ID','2')))
    if not data['teams'] or not data['players']: raise ValueError('Empty league')
    target=ROOT/'site/data/league.json'; target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp'); temp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False)); temp.replace(target)
    print(f"Synced {len(data['teams'])} teams, {len(data['players'])} players, {len(data['draft']['picks'])} picks; season {year}.")

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(str(exc) if isinstance(exc,(RuntimeError,ValueError)) else 'Sync failed; previous deployment remains intact.',file=sys.stderr); sys.exit(1)
