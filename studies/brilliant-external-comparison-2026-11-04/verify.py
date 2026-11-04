"""Independent accounting, frozen-input and evidence replay checks; no classification/fitting."""
import json,hashlib,sys,collections,subprocess
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
P=Path(__file__).resolve().parent;W=P.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def counts(meta,awards):
 d=collections.Counter()
 for m,a in zip(meta,awards):d[('unresolved_positive' if m['truth'] else 'unresolved_negative') if a is None else ('TP' if m['truth'] else 'FP') if a else ('FN_known' if m['truth'] else 'TN_known')]+=1
 return {k:d[k] for k in ['TP','FP','FN_known','TN_known','unresolved_positive','unresolved_negative']}
def main():
 protocol=load(P/'PROTOCOL.json');results=load(P/'RESULTS.json');meta=load(P/'LABELS-AND-GROUPS.json');pairs=load(P/'PAIRED-CASES.json')
 assert len(meta)==3724 and len({m['group'] for m in meta})==972
 for f,key in [('INPUTS.jsonl','input_sha256'),('LABELS-AND-GROUPS.json','metadata_sha256')]:assert sha(P/f)==protocol[key]
 original=load(W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json')['cases'];orig={c['key']:c for c in original}
 baseline=load(W/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json');base={r['key']:r for r in baseline}
 games={};positions={};ninputs=0
 for m in meta:
  c=orig[m['key']];b=base[m['key']]
  assert c['truth']==m['truth'] and c['group']==m['group']==b['group'] and m['outer_fold']==b['outer_fold'] and m['baseline_awards']==b['outer_awards']
  for key in c['aliases']+[c['key']]:assert games.setdefault(key.rsplit(':',1)[0],m['group'])==m['group']
  assert positions.setdefault(' '.join(c['fen_before'].split()[:4]),m['group'])==m['group']
 for line in (P/'INPUTS.jsonl').read_text().splitlines():
  r=json.loads(line);assert not {'truth','outer_fold','group','baseline_awards'}&r.keys()
  b=chess.Board(r['rootFen'])
  for u in r['historyUcis']:b.push_uci(u)
  assert b.fen()==r['fen_before'];b.push_uci(r['uci']);assert b.fen()==r['fen_after'];ninputs+=1
 assert ninputs==3724
 for name in ['WINTR','KNIGHTS']:
  freeze=load(P/(name+'-FREEZE.json'))
  if name=='WINTR':assert sha(P/'wintr-adapter.mjs')==freeze['adapter_sha256'] and sha(P/'PROTOCOL.json')==freeze['protocol_sha256']
  else:
   for f,h in freeze['files'].items():assert sha(P/f)==h,(f,'freeze changed')
  rows=[json.loads(l) for l in (P/(name+'-PREDICTIONS.jsonl')).read_text().splitlines()];by={r['key']:r for r in rows};assert len(by)==len(rows)==3724
  for mode in ['both','current','previous']:
   arm=name.lower()+'_'+mode;a=[by[m['key']]['award'] if mode=='both' else by[m['key']]['windows'][mode]['award'] for m in meta]
   c=counts(meta,a);actual=results['arms'][arm]['pooled'];assert all(actual[k]==v for k,v in c.items())
   assert sum(c.values())==3724 and actual['confirmed_recall_all_positives']==c['TP']/917
   for f in range(5):
    ix=[i for i,m in enumerate(meta) if m['outer_fold']==f];fc=counts([meta[i] for i in ix],[a[i] for i in ix]);fa=results['arms'][arm]['per_fold'][f]['external'];assert all(fa[k]==v for k,v in fc.items())
   recovered=[m['key'] for m,x in zip(meta,a) if m['truth'] and x is True and not m['baseline_awards']['custom_retuned']]
   wrong=[m['key'] for m,x in zip(meta,a) if not m['truth'] and x is True and not m['baseline_awards']['custom_retuned']]
   assert recovered==pairs['changes'][arm]['recovered_correct']['keys'] and wrong==pairs['changes'][arm]['new_wrong']['keys']
   union=results['arms'][arm]['hypothetical_union']['pooled'];assert union['TP']==452+len(recovered) and union['FP']==6+len(wrong)
  for r in rows:
   vals=[r['windows'][w]['award'] for w in ['current','previous']];expected=False if False in vals else True if vals==[True,True] else None;assert r['award'] is expected
 receipt=load(P/'KNIGHTS-RECEIPT.json');assert receipt['status']=='complete' and receipt['cases']==3724 and receipt['engine_seconds']<=901
 assert receipt['output_sha256']==sha(P/'KNIGHTS-PREDICTIONS.jsonl')
 nsearch=npv=0
 for line in (P/'KNIGHTS-ENGINE-EVIDENCE.jsonl').read_text().splitlines():
  r=json.loads(line);b=chess.Board(r['rootFen'])
  for u in r['historyUcis']:b.push_uci(u)
  assert b.fen()==chess.Board(r['request']['fen']).fen();ev=r.get('evidence');nsearch+=1
  if not ev:continue
  assert chess.Board(ev['fen']).fen()==b.fen();a=ev['analysis'];roots=[];depths=[]
  for i,c in enumerate(a['candidates'],1):
   assert c['multipv']==i and not c.get('upperbound') and not c.get('lowerbound')
   board=b.copy(stack=True)
   for u in c['pv']:board.push_uci(u)
   roots.append(c['pv'][0]);depths.append(c['depth']);npv+=1
  assert len(set(roots))==len(roots) and len(set(depths))==1 and a['depth']==depths[0]
  if r['request'].get('rootMoves') is not None:assert set(roots)==set(r['request']['rootMoves'])
  if r['reason'] is None:assert a['depth']>=r['request']['depth']
 assert nsearch==receipt['searches']
 result={'status':'pass','input_histories_replayed':ninputs,'supplemental_searches_replayed':nsearch,'supplemental_pvs_replayed':npv,'checks':['frozen input/adapters/driver/evaluator hashes','same original game-position-alias groups and fold assignments','all six arms pooled/fold accounting','unknowns separate from FN/TN','recovered/newwrong identities and hypothetical union counts','exact fullhistory and restricted root scope for supplemental evidence','source and supplemental PV legality and required depth'],'outputs_sha256':{f:sha(P/f) for f in ['RESULTS.json','PAIRED-CASES.json','WINTR-PREDICTIONS.jsonl','KNIGHTS-PREDICTIONS.jsonl','KNIGHTS-ENGINE-EVIDENCE.jsonl']},'caveat':'Source snapshots contain no ratings. Hard_ordinary subgroup follows a source cohort flag which can include positive labels; do not interpret that subgroup as exclusively negative cases.'}
 (P/'VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
