"""Descriptive comparison of relation witnesses; no fitting or award rule."""
import hashlib,json
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parents[1]
TRAIN=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
PREDS=W/'research/brilliant-evaluation-consistency-2026-11-04/PREDICTIONS.json'
MATCH=W/'research/brilliant-forest-miss-diagnosis-2026-11-04/MATCHES.json'
PANEL=W/'research/brilliant-forest-miss-diagnosis-2026-11-04/PANEL.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rank(score):
    if score['kind']=='mate':return (0,abs(score['value'])) if score['value']<=0 else (2,-score['value'])
    return (1,score['value'])
def describe(c,offer,t):
    first=t['first_reply'];forks=t['forks_geometric'];pins=t['new_absolute_pins_geometric'];links=offer['acceptance_geometry_links']
    direct=bool(first and first['directly_recaptures_acceptor'])
    other_first=any(x['ply']==1 and x['actor']==c['mover'] and not x['is_acceptor'] for x in t['captures'])
    clear=bool(first and first['acceptance_cleared_slider_path']['observed'])
    ffirst=[x for x in forks if x['ply']==1]
    return dict(first_reply_direct_recapture=direct,first_reply_capture_other_piece=other_first,
        acceptance_clears_first_reply_slider_path=clear,
        acceptance_opens_slider_attack=any(x['acceptor_origin_cleared_only_blocker'] for x in links),
        acceptor_becomes_new_slider_target=any(x['new_enemy_target_at_acceptor_destination'] for x in links),
        immediate_recapture_then_fork=direct and bool(ffirst),
        immediate_fork_targets_acceptor=any(t['is_acceptor'] for f in ffirst for t in f['fork_geometric_targets']),
        any_fork_observed_by6=bool(forks),fork_targets_acceptor_by6=any(t['is_acceptor'] for f in forks for t in f['fork_geometric_targets']),
        new_absolute_pin_observed_by6=bool(pins),new_absolute_pin_acceptor_by6=any(p['pinned']['is_acceptor'] for p in pins),
        cleared_path_then_capture_other=clear and other_first,
        acceptor_recaptured_by6=t['acceptor_recaptured_response_ply'] is not None,
        mover_capture_other_square_by6=t['first_mover_capture_other_square_response_ply'] is not None,
        first_reply_check=bool(first and first['check']),
        mover_mates_within6=bool(t['mate_within6'] and t['mate_within6']['winner']==c['mover']))
def select(c,window):
    candidates=[]
    for o in c['offers']:
        win=o['windows'][window]
        if not win.get('responses'):return None
        t=win['responses'][0]
        if not t.get('first_reply'):return None
        candidates.append((rank(t['score_mover']),o['acceptance_uci'],o,t))
    if not candidates:return None
    _,u,o,t=min(candidates,key=lambda row:(row[0],row[1]))
    return dict(acceptance=u,first_reply=t['first_reply']['san'],score_mover=t['score_mover'],
                horizon6_complete=t['horizon6_complete'],response_horizon_plies=t['response_horizon_plies'],
                descriptors=describe(c,o,t))
def aggregate(keys,rows):
    known=[rows[k]['current'] for k in keys if rows[k]['current']]
    observed=Counter(n for r in known for n,v in r['descriptors'].items() if v)
    return dict(cases=len(keys),current_known=len(known),current_unknown=len(keys)-len(known),
                current_observed_counts=dict(observed),horizon6_complete=sum(r['horizon6_complete'] for r in known),
                previous_known=sum(rows[k]['previous'] is not None for k in keys))
def main():
    protocol=json.loads((H/'COMPARISON-PROTOCOL.json').read_text())
    assert sha(Path(__file__))==protocol['script_sha256']
    assert all(sha(k)==v for k,v in protocol['source_sha256'].items())
    cs={c['key']:c for c in json.loads(TRAIN.read_text())['cases']};ps={r['key']:r for r in json.loads(PREDS.read_text())}
    rel=json.loads((H/'RELATIONS.json').read_text())['cases'];matches=json.loads(MATCH.read_text())['rows'];panel=json.loads(PANEL.read_text())
    rows={k:{w:select(c,w) for w in ('current','previous')} for k,c in rel.items()}
    misses=[r['key'] for r in matches]
    ordinary=[k for k in rel if not cs[k]['truth'] and cs[k]['negative_bucket']=='hard_ordinary']
    found=[k for k in rel if cs[k]['truth'] and ps[k]['retuned_baseline']]
    assert len(rows)==1302 and len(misses)==429 and len(ordinary)==226 and len(found)==452
    groups={'misses':misses,'hard_ordinary':ordinary,'found_brilliants':found,
        'miss_ec_true':[k for k in misses if cs[k]['windows']['current']['features']['ec_sacrifice']],
        'miss_ec_false':[k for k in misses if not cs[k]['windows']['current']['features']['ec_sacrifice']]}
    pairs=[];counts={}
    for m in matches:
        k=m['key'];o=m['ordinary']['key'];a,b=rows[k]['current'],rows[o]['current']
        record=dict(miss=k,ordinary=o,exact_anchors=m['ordinary']['exact_anchors'],known=a is not None and b is not None)
        if record['known']:
            record['relations']={n:('both' if va and b['descriptors'][n] else 'miss_only' if va else 'ordinary_only' if b['descriptors'][n] else 'neither_observed') for n,va in a['descriptors'].items()}
            if record['exact_anchors']:
                for n,v in record['relations'].items():counts.setdefault(n,Counter())[v]+=1
        pairs.append(record)
    panel_rows=[dict(pair=i,miss=p['miss']['key'],ordinary=p['ordinary']['key'],exact_anchors=p['pair']['ordinary']['exact_anchors'],
                    miss_observations=rows[p['miss']['key']],ordinary_observations=rows[p['ordinary']['key']]) for i,p in enumerate(panel,1)]
    out=dict(scope=protocol['scope'],protocol_sha256=sha(H/'COMPARISON-PROTOCOL.json'),script_sha256=sha(Path(__file__)),
             relations_sha256=sha(H/'RELATIONS.json'),groups={n:aggregate(keys,rows) for n,keys in groups.items()},
             exact_anchor_pairs=sum(p['exact_anchors'] for p in pairs),known_exact_anchor_pairs=sum(p['exact_anchors'] and p['known'] for p in pairs),
             pair_counts={n:dict(c) for n,c in counts.items()},pairs=pairs,panel=panel_rows,rows=rows,
             limits=['Selected best saved response to opponent-best saved accepting branch only; other branches remain archived.',
                     'Geometric attack/pin/fork and witnessed PV are not exhaustive forced outcomes or causal counterfactuals.',
                     'False descriptor means not observed in saved prefix; missing branches are null. Short-line absence is not proof.',
                     'Match controls reused, enriched known cases, diagnostic only: no independent accuracy or significance claim.'])
    (H/'COMPARISON.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'groups':out['groups'],'pair_counts':out['pair_counts'],'known_exact_pairs':out['known_exact_anchor_pairs']},indent=2))
if __name__=='__main__':main()
