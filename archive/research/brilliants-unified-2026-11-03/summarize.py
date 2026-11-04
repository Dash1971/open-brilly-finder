"""Compute transparent agreement counts and independently assigned game groups."""
from pathlib import Path
import json,csv,sys,collections,hashlib,datetime
try:import chess
except ImportError:
 sys.path.insert(0,'/private/tmp/brilly-research-deps');import chess
ROOT=Path(__file__).resolve().parent
load=lambda name:json.loads((ROOT/name).read_text())
def metrics(rows,policy):
 d=dict(TP=0,FN=0,FP=0,TN=0)
 for r in rows:
  yes=r['truth_brilliant'];award=r['annotations'][policy]=='!!';d[('T' if yes==award else 'F')+('P' if award else 'N')]+=1
 n=len(rows);pos=d['TP']+d['FN'];neg=d['FP']+d['TN']
 return dict(d,agreement=(d['TP']+d['TN'])/n if n else None,brilliant_detection=d['TP']/pos if pos else None,false_award_rate=d['FP']/neg if neg else None,precision_in_selected_sample=d['TP']/(d['TP']+d['FP']) if d['TP']+d['FP'] else None)
def group(rows):
 return {'n':len(rows),'positive_n':sum(x['truth_brilliant'] for x in rows),'negative_n':sum(not x['truth_brilliant'] for x in rows),'games':len({(x['game_type'],x['game_id']) for x in rows}),'policies':{p:metrics(rows,p) for p in ['ec_raw','ec_confirmed','mute_v2','mute_v3']}}
def canonical(f):return ' '.join(chess.Board(f).fen().split()[:4])
def main():
 p=load('primary-moves.json');a=load('comparison-v2.json');b=load('comparison-v3.json');assert len(p)==618
 assert not a['python_vs_typescript_material_differences'] and not b['python_vs_typescript_material_differences']
 aa={(x['game_id'],x['ply']):x for x in a['rows']};bb={(x['game_id'],x['ply']):x for x in b['rows']};tt={(x['game_id'],x['ply']):x for x in load('analysis-baseline.json')['targets']};rows=[]
 for x in p:
  key=(x['game_id'],x['ply']);v2,v3,t=aa[key],bb[key],tt[key];assert v2['primary_fresh_binary_label']==v3['primary_fresh_binary_label'];truth=v3['primary_fresh_binary_label']=='brilliant';assert truth==(x['fresh_label']=='!!')
  rows.append({**x,'truth_brilliant':truth,'game_type':'daily' if '/daily/' in x['fresh_source_link'] else 'live','annotations':{'ec_raw':v2['ec_raw_unchanged_oracle'],'ec_confirmed':v2['ec']['symbol'],'mute_v2':v2['mute_v2']['symbol'],'mute_v3':v3['mute_v3']['symbol']},'raw_legal_offer':v3['mute_piece_offer'],'ec_material_sacrifice':v3['ec_sacrifice'],'mapped_loss_pp':v3['baseline_gates']['mapped_loss_pp'],'after_cp_mover':v3['baseline_gates']['after_cp_mover'],'white_rating':t.get('white_rating'),'black_rating':t.get('black_rating'),'time_control':t.get('time_control')})
 dev=[x for x in rows if x['split']!='reserved_validation'];reserved=[x for x in rows if x['split']=='reserved_validation'];devfen={canonical(x[k]) for x in dev for k in ['fen_before','fen_after']};badgames={(x['game_type'],x['game_id']) for x in reserved if any(canonical(x[k]) in devfen for k in ['fen_before','fen_after'])};validation=[x for x in reserved if (x['game_type'],x['game_id']) not in badgames]
 before=collections.defaultdict(list)
 for x in rows:before[canonical(x['fen_before'])].append({'game_id':x['game_id'],'ply':x['ply'],'split':x['split']})
 obs=load('observations-export.json');oi={x['observation_id']:x for x in obs};coach=collections.Counter();missingobs=[]
 for x in rows:
  o=oi.get(x['fresh_observation_id'])
  if o is None:missingobs.append((x['game_id'],x['ply']));continue
  raw=o['raw'];text=o.get('coach_explanation')
  status=raw.get('coach_completeness') or raw.get('coach_capture_status')
  coach['verified_visible_complete' if status in ['verified_visible_complete','explicitly_recorded_visible_complete'] else 'partial_or_unverified' if text else 'absent']+=1
 assert not missingobs,missingobs
 summary={'completed':True,'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'combined':group(rows),'development':group(dev),'validation':group(validation),'reserved_assigned':group(reserved),'prospective':group([x for x in rows if x['source_cohort']=='prospective']),'by_account':{account:group([x for x in rows if x['account']==account]) for account in sorted({x['account'] for x in rows})},'audit':{'board_corrobated':sum(x['board_identity_captured'] for x in rows),'board_missing':sum(not x['board_identity_captured'] for x in rows),'coach_text':dict(coach),'repeated_before_position_groups':[x for x in before.values() if len(x)>1],'validation_overlap_excluded_games':[{'game_type':t,'game_id':g} for t,g in sorted(badgames)],'material_source_parity_differences':0,'source_label_conflicts':0,'book_controls':sum(x['fresh_label']=='book' for x in rows),'negative_raw_offer':{str(offered):{'n':sum(not x['truth_brilliant'] and x['raw_legal_offer']==offered for x in rows),'false_awards':{p:sum(not x['truth_brilliant'] and x['raw_legal_offer']==offered and x['annotations'][p]=='!!' for x in rows) for p in ['ec_raw','mute_v2','mute_v3']}} for offered in [True,False]}},'interpretation':'Conditional agreement on a balanced,enriched challenge set; no ordinary-game prevalence,error-frequency,enjoyment or all-open-source-project claim.'}
 (ROOT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');(ROOT/'moves.json').write_text(json.dumps(rows,indent=2)+'\n')
 fields=['account','game_type','game_id','ply','san','uci','fresh_label','split','source_cohort','time_control','white_rating','black_rating','raw_legal_offer','ec_material_sacrifice','mapped_loss_pp','after_cp_mover','ec_raw','ec_confirmed','mute_v2','mute_v3','fresh_source_link','fen_before','fen_after']
 with (ROOT/'moves.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k: r['annotations'][k] if k in r['annotations'] else r.get(k) for k in fields})
 print(json.dumps({k:summary[k] for k in ['combined','prospective','validation']},indent=2))
if __name__=='__main__':main()
