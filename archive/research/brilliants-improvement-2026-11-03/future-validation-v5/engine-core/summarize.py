#!/usr/bin/env python3
"""Identity-keyed fresh-test metrics after all fixed predictions are complete."""
import csv,hashlib,json,math
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def interval(success,n):
    if not n:return {'point':None,'n':0,'wilson95':None}
    z=1.959963984540054;p=success/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;delta=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {'point':p,'n':n,'wilson95':[max(0,center-delta),min(1,center+delta)]}

def tally(rows,name):
    c={k:0 for k in ('TP','FN','FP','TN')}
    for r in rows:c[('TP' if r['awards'][name] else 'FN') if r['truth'] else ('FP' if r['awards'][name] else 'TN')]+=1
    return {**c,'n':len(rows),'games':len({r['game_id'] for r in rows}),
            'recognition':interval(c['TP'],c['TP']+c['FN']),
            'extra_control_rate':interval(c['FP'],c['FP']+c['TN']),
            'sample_badge_precision':interval(c['TP'],c['TP']+c['FP']),
            'agreement':interval(c['TP']+c['TN'],len(rows))}

def main():
    sfile=ROOT/'../engine-s/results.json'
    paths={'core':ROOT/'analysis-core.json','primary':ROOT/'primary-moves.json',
           'forest':ROOT/'forest-predictions.json','rules':ROOT/'rule-predictions.json','S':sfile,
           'core_freeze':ROOT/'../CORE-FREEZE.json'}
    assert sha(paths['core_freeze'])=='99bcffb5a77209f13e61bd0c495625950da6950c028ab9b64a5a1b8eea6a3394'
    primary=read(paths['primary']);forest=read(paths['forest']);rules=read(paths['rules']);sequence=read(sfile)
    bykey=lambda rs:{r['key']:r for r in rs}
    f=bykey(forest['rows']);r=bykey(rules['rows']);s=bykey(sequence['rows'])
    keys={f"{t['game_id']}:{t['ply']}" for t in primary}
    assert len(keys)==200 and set(f)==set(r)==set(s)==keys and len(forest['rows'])==len(rules['rows'])==len(sequence['rows'])==200
    assert forest['core_sha256']==rules['core_sha256']==sha(paths['core'])
    rows=[]
    for t in primary:
        k=f"{t['game_id']}:{t['ply']}";truth=t['fresh_label']=='!!'
        if 'truth' in s[k]:assert truth==s[k]['truth']
        assert s[k]['base']['symbol']==r[k]['A']['symbol']
        rows.append({'key':k,'game_id':t['game_id'],'ply':t['ply'],'san':t['san'],'account':t['account'],
                     'truth':truth,'label':t['fresh_label'],'source_link':t['fresh_source_link'],
                     'awards':{'forest':f[k]['forest']['award'],'S':bool(s[k]['awarded']),
                               'A':r[k]['A']['symbol']=='!!','v4':r[k]['v4']['symbol']=='!!',
                               'ec_direct':r[k]['ec_direct_symbol']=='!!','ec_confirmed':r[k]['ec_confirmed']['symbol']=='!!'},
                     'trace':{'forest':f[k],'rules':r[k],'S':s[k]}})
    names=list(rows[0]['awards']);accounts=sorted({t['account'] for t in rows})
    unknown={};features={}
    for window in ('current','previous'):
        missing=Counter();missing_cases=[];ineligible=[]
        for k,p in f.items():
            fs=p['features']['windows'][window]['features'];assert len(fs)==75
            holes=[n for n,v in fs.items() if v is None];missing.update(holes)
            if holes:missing_cases.append({'key':k,'features':holes})
            if not p['features']['windows'][window]['eligible']:ineligible.append(k)
        features[window]={'rows':200,'features_per_row':75,'missing_values':sum(missing.values()),'missing_by_feature':dict(missing),
                          'cases_with_missing':missing_cases,'ineligible_keys':ineligible}
    unknown['insufficient_confidence_keys']=[k for k,p in f.items() if not p['features']['confidence_sufficient']]
    unknown['physical_unknown_keys']=[k for k,p in f.items() if p['features']['diagnostics'].get('physical_unknown')]
    unknown['explicit_unknown_feature_counts']={w:dict(Counter(n for p in f.values() for n,v in p['features']['windows'][w]['features'].items() if 'unknown' in n and v)) for w in ('current','previous')}
    unknown['S_unknown_keys']=[k for k,p in s.items() if p.get('proof',{}).get('status')=='unknown']
    unknown['forest_diagnostics']={k:p['features']['diagnostics'] for k,p in f.items()}
    result={'scope':'Frozen prospective 200-move test,100Brilliant/100explicitnon-Brilliant; neither model nor threshold changed after labels.',
            'input_hashes':{k:{'path':str(p.resolve()),'sha256':sha(p)} for k,p in paths.items()},
            'total_moves':200,'games':len({t['game_id'] for t in rows}),
            'overall':{name:tally(rows,name) for name in names},
            'by_account':{a:{name:tally([t for t in rows if t['account']==a],name) for name in names} for a in accounts},
            'feature_missingness':features,'unknowns':unknown,
            'missingness_note':'None does not uniformly mean proof failure: cp/mate alternate fields, unavailable played top2 roots, absent safe alternatives and no-offer physical debt are inapplicable/absent observations. Explicit physical_unknown and avoidability_unknown flags are reported separately; optional unknowns retain frozen missing-value routing.',
            'interval_caveat':'Wilson intervals treat moves as independent. Moves share games; these are descriptive binomial intervals, not game-cluster-adjusted uncertainty. Balanced/enriched controls do not estimate natural-game prevalence or deployment badge precision. Zero observed errors is point0 with a nonzero upper interval, never a universal guarantee.',
            'domain':'Pinned SF18,300k requestednodes,Threads1,Hash64,complete current/prior iterations/fullPGN. NativeSF19 unvalidated.',
            'rows':rows}
    (ROOT/'fresh-results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (ROOT/'fresh-predictions.csv').open('w',newline='') as out:
        fields=['key','game_id','ply','san','account','label','truth',*names,'source_link'];writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({**{k:row[k] for k in fields if k in row},**row['awards']})
    print(json.dumps({'overall':{n:{k:v for k,v in c.items() if k in ('TP','FN','FP','TN','n')} for n,c in result['overall'].items()},
                      'missing':{w:d['missing_values'] for w,d in features.items()},'unknown':{k:v for k,v in unknown.items() if k!='forest_diagnostics'}},indent=2))

if __name__=='__main__':main()
