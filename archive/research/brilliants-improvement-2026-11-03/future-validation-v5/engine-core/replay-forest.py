#!/usr/bin/env python3
"""Replay unchanged frozen extractor/model only after complete core merge; no fits."""
import hashlib,json,sqlite3,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
IMPROVE=ROOT.parents[1]
sys.path.insert(0,str(IMPROVE/'astra/v5/fresh-extractor'))
from extractor import extract_batch,score_fixed_forest
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())

def main():
    plan=read(ROOT/'PLAN.json');bank=read(ROOT/'analysis-core.json')
    assert bank['status']=='complete' and bank['nodes_per_position']==300000 and len(bank['targets'])==200
    assert bank['plan_sha256']==sha(ROOT/'PLAN.json') and bank['primary_sha256']==plan['primary_sha256']
    modelpath=IMPROVE/'learning-v5/forest-diagnostic/forest-full.json'
    assert sha(modelpath)=='44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7'
    frozen=read(IMPROVE/'astra/v5/fresh-extractor/FREEZE.json')
    for path,expected in frozen['sha256'].items():
        if sha(Path(path))!=expected:raise ValueError('Frozen extraction dependency changed: '+path)
    db=sqlite3.connect('file:'+plan['db_path']+'?mode=ro',uri=True)
    if sha(Path(plan['db_path']))!=plan['db_sha256']:raise ValueError('Frozen corpus DB changed')
    requests=[]
    for t in bank['targets']:
        pgn,recorded=db.execute('select pgn,pgn_sha256 from games where game_id=?',(t['game_id'],)).fetchone()
        assert recorded==t['pgn_sha256']
        requests.append({'pgn':pgn,'ply':t['ply'],'snapshots':[bank['snapshots'][i] for i in t['snapshot_ids']]})
    db.close();model=read(modelpath)
    cases=extract_batch(requests)
    rows=[{'key':f"{t['game_id']}:{t['ply']}",'features':c,'forest':score_fixed_forest(c,model)} for t,c in zip(bank['targets'],cases)]
    assert len(rows)==200
    out=ROOT/'forest-predictions.json'
    if out.exists():raise ValueError('Refusing to replace frozen replay')
    out.write_text(json.dumps({'model_sha256':sha(modelpath),'core_sha256':sha(ROOT/'analysis-core.json'),
                              'extractor_freeze':frozen,'rows':rows},indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':'complete','predictions':len(rows),'metrics_computed':False}))

if __name__=='__main__':main()
