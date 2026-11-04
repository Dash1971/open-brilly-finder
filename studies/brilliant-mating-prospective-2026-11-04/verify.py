"""Focused verification of prospective frozen inference, independence and label accounting."""
import collections,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
from base_rule import mating_rule
H=Path(__file__).resolve().parent;W=H.parents[1]
def read(n):return json.loads((H/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=read('CANDIDATE-FREEZE.json');run=read('RUN-FREEZE.json');pre=read('PRELABEL-FREEZE.json');inputs=read('INPUTS.json');mined=read('MINED.json');scored=read('SCORED.json');queue=read('REVIEW-QUEUE.json');model=read('forest.json')
for path,digest in run['source_sha256'].items():assert sha(Path(path))==digest
for path,digest in p['source_sha256'].items():assert sha(W/path)==digest
for name,digest in p['artifact_sha256'].items():assert sha(H/name)==digest
for name,digest in pre['sha256'].items():assert sha(H/name)==digest
assert mined['inputs_sha256']==sha(H/'INPUTS.json') and mined['script_sha256']==sha(H/'mine.py')
assert scored['candidate_freeze_sha256']==sha(H/'CANDIDATE-FREEZE.json') and scored['run_freeze_sha256']==sha(H/'RUN-FREEZE.json')
assert queue['scored_sha256']==sha(H/'SCORED.json')
excluded=set(inputs['excluded_game_ids']);oldpos=set(inputs['excluded_positions']);ids=set();afterpos=set()
for c in mined['candidates']:
 assert c['game_id'] not in excluded and c['key'] not in ids;ids.add(c['key'])
 for f in ['fen_before','fen_after']:assert ' '.join(c[f].split()[:4]) not in oldpos
 pos=' '.join(c['fen_after'].split()[:4]);assert pos not in afterpos;afterpos.add(pos)
 assert hashlib.sha256(c['pgn'].encode()).hexdigest()==c['pgn_sha256']
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
for c in mined['candidates']:
 b=chess.Board(c['fen_before']);b.push_uci(c['uci']);assert b.fen()==c['fen_after']
 for u,w in c['witnesses'].items():
  a=b.copy();a.push_uci(u);assert a.fen()==w['fen_after_acceptance']
  for reply in w['mate_replies']:
   z=a.copy();z.push_uci(reply['uci']);assert z.is_checkmate() and z.fen()==reply['fen_after_mate']
source={c['key']:c for c in mined['candidates']};rows={c['key']:c for c in scored['rows']}
for k,c in rows.items():
 assert k in source and c['fen_before']==source[k]['fen_before'] and c['pgn_sha256']==source[k]['pgn_sha256']
 f=c['features'];values={};scores={}
 for w in ['current','previous']:
  fs=f['windows'][w]['features'];values[w]=[float(fs[n]) if fs[n] is not None else None for n in model['features'][:75]]+[float(fs[n] is None) for n in model['features'][:75]];ps=[]
  for tree in model['trees']:
   n=tree
   while n['kind']=='split':
    v=values[w][n['feature_index']];n=n['left' if v is None or v<=n['threshold'] else 'right']
   ps.append(n['raw_p'])
  scores[w]=sum(ps)/len(ps);assert abs(scores[w]-c['window_scores'][w])<1e-12
 eligible=f['confidence_sufficient'] and all(f['windows'][w]['eligible'] and not f['windows'][w]['features']['physical_unknown'] for w in ['current','previous'])
 assert c['eligible']==bool(eligible)
 base=eligible and min(scores.values())>=p['forest_threshold'];br=mating_rule(f);material=c['material_features'];extra=br and material is not None and all(material[w]['nonmate_material_win']==0 for w in ['current','previous'])
 assert c['base_rule']==br and c['refined_rule']==bool(extra)
 assert c['baseline_award']==bool(base) and c['candidate_award']==bool(base or extra) and c['new_award']==bool(extra and not base)
 assert not c['baseline_award'] or c['candidate_award']
keys=[c['key'] for c in queue['rows']];assert len(keys)==len(set(keys)) and len({c['game_id'] for c in queue['rows']})==len(keys)
assert len({' '.join(c['fen_before'].split()[:4]) for c in queue['rows']})==len(keys)
for q in queue['rows']:
 for f in ['pgn','fen_before','fen_after','baseline_award','candidate_award','new_award']:assert q[f]==rows[q['key']][f]
assert sum(c['new_award'] for c in queue['rows'])==pre['new_award_targets']<=12
assert sum(not c['new_award'] for c in queue['rows'])==pre['near_control_targets']<=12
checks=['frozen candidate/model/code/source and prelabel queue hashes','all mined games/targetpositions outside exclusions','all exact playedmoves and acceptance-mate witnesses legally replayed','all fixedforest scores/guards/thresholds/exception decisions independently recomputed','no baseline awards removed','one case pergame and distinct targetposition','queue integrity and fixedsample limits; no model fit']
out={'status':'pass','checks':checks,'mined_cases':len(source),'scored_cases':len(rows),'queued_cases':len(keys),'new_award_targets':pre['new_award_targets'],'baseline_awards_in_scored_pool':sum(c['baseline_award'] for c in rows.values()),'new_awards_in_scored_pool':sum(c['new_award'] for c in rows.values()),'labels_checked':False}
if (H/'LABELS.json').exists():
 labels=read('LABELS.json');ll={x['key']:x for x in labels['rows']};assert set(ll)==set(keys)
 for k,l in ll.items():
  assert l['game_id']==rows[k]['game_id'] and l['ply']==rows[k]['ply']
  assert l['status'] in ['verified','unresolved']
  if l['status']=='verified':assert l['label'] in ['Brilliant','Great','Best','Excellent','Good','Book','Inaccuracy','Mistake','Miss','Blunder','Forced'] and l['visible_text']
 out['labels_checked']=True;out['verified_labels']=sum(x['status']=='verified' for x in ll.values());out['unresolved_labels']=sum(x['status']=='unresolved' for x in ll.values());checks.append('all frozen queued cases retained with verified or explicit unresolved label')
out['artifact_sha256']={f:sha(H/f) for f in ['CANDIDATE-FREEZE.json','RUN-FREEZE.json','MINED.json','SCORED.json','REVIEW-QUEUE.json','PRELABEL-FREEZE.json','verify.py']}
(H/'VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
