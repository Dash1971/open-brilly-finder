"""Single paired reserved evaluation, only after root's model/input hash freeze."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent/'brilliants-improvement-2026-11-03/astra/v5/fresh-extractor';sys.path.insert(0,str(E));import extractor

def en_croissant_direct(case):
 # En Croissant v0.15 direct current-window annotation !!, original contract.
 # No forest physical-unknown abstention, prior-window or confidence gate.
 f=case['windows']['current']['features']
 return bool(f['window_complete'] and f['ec_sacrifice'] and f['before_roots']>1 and
             f['mapped_loss_pp'] is not None and f['mapped_loss_pp']<=5 and
             f['best_second_gap_pp'] is not None and f['best_second_gap_pp']>10 and
             f['same_root_rank']==1)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
go=json.loads(Path(sys.argv[1]).read_text());assert go['evaluation_authorized'] and go['script_sha256']==sha(__file__)
model_path=Path(go['candidate_path']);assert sha(model_path)==go['candidate_sha256'];candidate=json.loads(model_path.read_text());baseline=json.loads(extractor.MODEL_PATH.read_text());assert sha(extractor.MODEL_PATH)=='44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7'
training_path=Path(go['training_path']);assert sha(training_path)==go['training_sha256'];training=json.loads(training_path.read_text());games={c['game_id'] for c in training['cases']};before={' '.join(c['fen_before'].split()[:4]) for c in training['cases']};after={' '.join(c['fen_after'].split()[:4]) for c in training['cases']}
games.update(k.rsplit(':',1)[0] for c in training['cases'] for k in c.get('aliases',[]))
games.update(k.rsplit(':',1)[0] for q in training.get('quarantine',[]) for k in q['keys'])
exclusion_path=Path(go['exclusion_path']);assert sha(exclusion_path)==go['exclusion_sha256'];exclusions=json.loads(exclusion_path.read_text());old_positions=set(exclusions['canonical_first_four']);old_games=set(map(str,exclusions['reviewed_game_ids']))
# The root-frozen queue must document importer exclusions; independently reject
# overlap with the actual frozen fit list as a second check, never modify labels.
rows=[];seen=set();counts={}
for batch in go['batches']:
 ap=Path(batch['analysis_path']);fp=Path(batch['features_path']);assert sha(ap)==batch['analysis_sha256'] and sha(fp)==batch['features_sha256'];a=json.loads(ap.read_text());f=json.loads(fp.read_text());assert a['status']==f['status']=='complete';targets={str(t['game_id'])+':'+str(t['ply']):t for t in a['targets']}
 assert len(targets)==len(a['targets']) and len(f['rows'])==len(targets) and {r['key'] for r in f['rows']}==set(targets), 'Assessment target/feature key mismatch'
 for r in f['rows']:
  t=targets[r['key']];assert t['split']==r['split']=='assessment' and str(t['game_id']) not in games and str(t['game_id']) not in old_games
  assert ' '.join(t['fen_before'].split()[:4]) not in old_positions and ' '.join(t['fen_after'].split()[:4]) not in old_positions
  assert ' '.join(t['fen_before'].split()[:4]) not in before|after and ' '.join(t['fen_after'].split()[:4]) not in before|after
  assert r['key'] not in seen;seen.add(r['key']);c=r['features'];unknown=any(c['windows'][w]['features']['physical_unknown'] for w in ['current','previous'])
  b=extractor.score_fixed_forest(c,baseline);n=extractor.score_fixed_forest(c,candidate);truth=t['is_brilliant'];bucket='positive' if truth else t['negative_bucket'];pair={}
  for name,s in [('baseline',b),('candidate',n)]:
   award=s['award'] and not unknown;pair[name]={'award':award,'window_scores':s['window_scores']};m=counts.setdefault(bucket,{}).setdefault(name,{'TP':0,'FN':0,'FP':0,'TN':0});m[('T' if award==truth else 'F')+('P' if award else 'N')]+=1
  ec_award=en_croissant_direct(c);pair['en_croissant']={'award':ec_award}
  m=counts.setdefault(bucket,{}).setdefault('en_croissant',{'TP':0,'FN':0,'FP':0,'TN':0});m[('T' if ec_award==truth else 'F')+('P' if ec_award else 'N')]+=1
  rows.append({'key':r['key'],'truth':truth,'bucket':bucket,'physical_unknown_abstention':unknown,**pair})
out=Path(sys.argv[2]);assert not out.exists();out.write_text(json.dumps({'scope':'Reserved new games; hard controls and easy errors reported separately; no parameter selection or promotion','peer_contract':'En Croissant v0.15 direct current-window, original contract; no forest physicalUnknown or two-window gate','go_sha256':sha(sys.argv[1]),'model_sha256':sha(model_path),'counts_by_bucket':counts,'rows':rows},indent=2)+'\n');print(json.dumps(counts))
