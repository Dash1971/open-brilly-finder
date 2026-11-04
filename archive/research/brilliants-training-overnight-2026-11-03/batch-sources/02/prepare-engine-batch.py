"""Freeze one explicit training-only batch from completed verified game imports."""
from pathlib import Path
import argparse,hashlib,json,sqlite3,shutil
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--batch',default='01');p.add_argument('--min-games',type=int,default=10);a=p.parse_args();output=ROOT/f'ENGINE-BATCH-{a.batch}.json'
 if output.exists():raise ValueError('Batch already frozen; no automatic overwrite')
 cx=sqlite3.connect('file:'+str(ROOT/'dataset.sqlite3')+'?mode=ro',uri=True);cx.row_factory=sqlite3.Row
 games=[dict(g)for g in cx.execute("select *from games where split='training' and game_id not in(select game_id from quarantines) order by imported_at,game_id")]
 previous_batches={p.name:json.loads(p.read_text())for p in ROOT.glob('ENGINE-BATCH-*.json')}
 assigned={str(g['game_id'])for b in previous_batches.values()for g in b['games']};games=[g for g in games if g['game_id']not in assigned]
 if len(games)<a.min_games:print(json.dumps({'status':'awaiting_completed_training_games','have':len(games),'need':a.min_games}));return
 # First fixed-size chronological completed prefix; no model outputs or label-ratio optimization.
 games=games[:a.min_games];packed=[];targets=[];source_files={}
 for g in games:
  gid=g['game_id'];packed.append({'game_id':gid,'split':'training','pgn':g['pgn'],'pgn_sha256':g['pgn_sha256'],'source_account':g['source_account']})
  labels=[dict(x)for x in cx.execute("select l.*,p.san,p.uci,p.fen_before,p.fen_after from labels l join positions p using(game_id,ply) where l.game_id=?and l.dataset_use='training' order by ply",(gid,))]
  selected=[x for x in labels if x['is_brilliant']or x['negative_bucket']=='hard_ordinary'];errors=[x for x in labels if x['negative_bucket']=='easy_error']
  if errors:selected.append(min(errors,key=lambda x:hashlib.sha256(f'mute-overnight-engine-{a.batch}:error:{gid}:{x["ply"]}'.encode()).hexdigest()))
  for x in sorted(selected,key=lambda x:x['ply']):targets.append({'game_id':gid,'ply':x['ply'],'split':'training','san':x['san'],'uci':x['uci'],'fen_before':x['fen_before'],'fen_after':x['fen_after'],'label':x['label'],'is_brilliant':bool(x['is_brilliant']),'negative_bucket':x['negative_bucket'],'individual_rendered_board_verified':bool(x['rendered_board_verified']),'actual_mover':x['mover'],'actual_mover_rating':x['mover_rating'],'source_types':json.loads(x['source_types']),'example_key':x['example_key']})
  for row in cx.execute('select distinct source_file,source_sha256 from observations where game_id=?',(gid,)):
   path=ROOT/row['source_file'];assert sha(path)==row['source_sha256'];source_files[row['source_file']]=row['source_sha256']
  assert sha(ROOT/g['complete_file'])==g['complete_sha256'];source_files[g['complete_file']]=g['complete_sha256']
 cx.close();assert all(g['split']=='training'for g in packed)and all(t['split']=='training'for t in targets)
 metadata={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'One explicitly frozen training-only batch. No assessment PGNs, labels, scores or model outputs in selection. No fitting authorized by this file.','previous_batch_sha256':{name:sha(ROOT/name)for name in previous_batches},'selection':'Next completed training games in import order, excluding every previously frozen batch;  all verified Brilliant and hard-ordinary labels, plus one deterministic hashed error per game. Other raw errors stay in the corpus. Quarantines excluded.','split_rule':"sha256('mute-overnight-2026-11-03-v1:'+gameID) mod5!=0",'plan_sha256':sha(ROOT/'PLAN.json'),'database_sha256_at_freeze':sha(ROOT/'dataset.sqlite3'),'database_live_path_not_an_input':True,'source_files_sha256':source_files,'queue_sha256':{p.name:sha(p)for p in sorted(ROOT.glob('queue-*.json'))},'parser_sha256':sha(ROOT/'import-verified.py'),'assessment_exclusions_sha256':sha(ROOT/'ASSESSMENT-POSITION-EXCLUSIONS.json'),'counts':{'games':len(packed),'targets':len(targets),'brilliant':sum(x['is_brilliant']for x in targets),'hard_ordinary':sum(x['negative_bucket']=='hard_ordinary'for x in targets),'error':sum(x['negative_bucket']=='easy_error'for x in targets),'unique_core_positions':len({(x['game_id'],p)for x in targets for p in range(max(0,x['ply']-2),x['ply']+1)})},'games':packed,'targets':targets}
 archive=ROOT/'batch-sources'/a.batch;archive.mkdir(parents=True,exist_ok=True)
 for filename in ['import-verified.py','prepare-engine-batch.py']:
  shutil.copyfile(ROOT/filename,archive/filename)
 metadata['source_snapshots_sha256']={str((archive/f).relative_to(ROOT)):sha(archive/f)for f in ['import-verified.py','prepare-engine-batch.py']}
 output.write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':'frozen','file':output.name,'sha256':sha(output),'counts':metadata['counts']}))
if __name__=='__main__':main()
