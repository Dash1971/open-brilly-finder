#!/usr/bin/env python3
"""Merge four completed frozen core partitions, with no replacements or scoring."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
ROOT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan=read(ROOT/'PLAN.json');primary=read(ROOT/'primary-moves.json')
    assert len(primary)==200 and sha(ROOT/'primary-moves.json')==plan['primary_sha256']
    identities={f"{t['game_id']}:{t['ply']}":t for t in primary};assert len(identities)==200
    expected={f"{t['game_id']}:{p}" for t in primary for p in range(max(0,t['ply']-2),t['ply']+1)}
    assert len(expected)<=600 and len(expected)==plan['snapshots']
    snapshots={};targets={};sources=[]
    for part in plan['partitions']:
        path=ROOT/f"analysis-worker-{part['worker']}.json";d=read(path)
        assert d['status']=='complete' and d['nodes_per_position']==300000 and d['threads']==1 and d['hash_mb']==64
        assert d['engine_sha256']==plan['engine']['sha256'] and d['subset_sha256']==part['sha256']
        assert d['script_sha256']==plan['script_hashes']['analysis.py'] and d['plan_sha256']==sha(ROOT/'PLAN.json')
        assert d['primary_selection_sha256']==plan['primary_sha256']
        assert len(d['targets'])==part['cases'] and len(d['snapshots'])==part['snapshots']
        sources.append({'file':path.name,'sha256':sha(path),'wall_seconds':d['wall_seconds'],'recorded_search_seconds':d['recorded_search_seconds']})
        for key,s in d['snapshots'].items():
            assert key in expected and key not in snapshots and s['quality']=='frozen-test-sf18-300000'
            b=chess.Board(s['fen'])
            for which in ('current','previous'):
                w=s.get(which)
                if w is None:continue
                roots=[l['moves'][0] for l in w['lines'] if l['moves']]
                if not s['terminal']:
                    assert len(roots)==min(2,b.legal_moves.count()) and len(set(roots))==len(roots)
                    assert all(chess.Move.from_uci(m) in b.legal_moves for m in roots)
            snapshots[key]=s
        for t in d['targets']:
            key=f"{t['game_id']}:{t['ply']}";assert key in identities and key not in targets
            original=identities[key]
            for field in ('uci','fen_before','fen_after'):assert t[field]==original[field]
            assert snapshots[t['snapshot_ids'][-2]]['fen']==t['fen_before'] and snapshots[t['snapshot_ids'][-1]]['fen']==t['fen_after']
            assert all(snapshots[i]['pgn_sha256']==t['pgn_sha256'] for i in t['snapshot_ids'])
            targets[key]=t
    assert set(snapshots)==expected and set(targets)==set(identities)
    result={'status':'complete','stage':'frozen-fresh-test-core','nodes_per_position':300000,
            'engine_sha256':plan['engine']['sha256'],'threads_per_worker':1,'hash_mb_per_worker':64,
            'plan_sha256':sha(ROOT/'PLAN.json'),'primary_sha256':plan['primary_sha256'],
            'targets':[targets[k] for k in sorted(targets)],'snapshots':snapshots,'source_provenance':sources,
            'missing_actual_prior_iterations':[k for k,s in snapshots.items() if not s['terminal'] and s.get('previous') is None]}
    out=ROOT/'analysis-core.json'
    if out.exists():raise ValueError('Refusing to replace completed core bank')
    temp=out.with_suffix('.json.tmp');temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(out)
    print(json.dumps({'status':'complete','cases':len(targets),'snapshots':len(snapshots),'missing_actual_prior_iterations':len(result['missing_actual_prior_iterations'])}))

if __name__=='__main__':main()
