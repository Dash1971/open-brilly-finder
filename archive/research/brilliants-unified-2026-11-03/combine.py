"""Build one reproducible benchmark from frozen, disjoint game cohorts."""
from pathlib import Path
import json,hashlib,sqlite3,shutil,datetime,sys
ROOT=Path(__file__).resolve().parent
SOURCES=[ROOT.parent/'brilliants-600-2026-11-03',ROOT.parent/'brilliants-additional-300-2026-11-03']
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 primary=[];targets=[];snapshots={};provenance=[];seen=set();game_sets=[]
 baselines=[load(s/'analysis-baseline.json') for s in SOURCES]
 assert all(b['status']=='complete' for b in baselines)
 assert len({b['engine_sha256'] for b in baselines})==1
 assert all(b['nodes_per_position']==300000 and b['threads']==1 and b['hash_mb']==64 for b in baselines)
 for i,(source,b) in enumerate(zip(SOURCES,baselines)):
  p=load(source/'primary-moves.json');assert len(p)==[318,300][i]
  keys={(x['game_id'],x['ply']) for x in p};assert keys=={(x['game_id'],x['ply']) for x in b['targets']};assert not keys&seen;seen|=keys
  games={x['game_id'] for x in p};game_sets.append(games)
  for x in p:
   y=dict(x);y['source_cohort']='development_reference' if i==0 else 'prospective';y['original_split']=y['split']
   if i==0:y['split']='development'
   primary.append(y)
  for x in b['targets']:
   y=dict(x);y['source_cohort']='development_reference' if i==0 else 'prospective';y['original_split']=y['split']
   if i==0:y['split']='development'
   targets.append(y)
  assert not snapshots.keys()&b['snapshots'].keys();snapshots.update(b['snapshots'])
  provenance.append({'cohort':i,'original_study_id':source.name,'engine_collection_started':b['started_at'],'engine_collection_completed':b['completed_at'],'collector_sha256':b['script_sha256'],'primary_sha256':digest(source/'primary-moves.json'),'analysis_sha256':digest(source/'analysis-baseline.json')})
 assert not game_sets[0]&game_sets[1]
 assert len(primary)==618 and sum(x['fresh_label']=='!!' for x in primary)==309
 save(ROOT/'primary-moves.json',primary)
 merged={k:v for k,v in baselines[0].items() if k not in ('targets','snapshots','rejected_identity_rows','script_sha256','started_at','resumed_at','completed_at')}
 merged.update(started_at=baselines[0]['started_at'],quantity_limit=618,status='complete',targets=targets,snapshots=snapshots,source_cohorts=provenance,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),primary_selection_sha256=digest(ROOT/'primary-moves.json'))
 save(ROOT/'analysis-baseline.json',merged)
 # The public database contains only the primary games, with full positions/history.
 db=ROOT/'corpus.sqlite3'
 if db.exists():db.unlink()
 old=sqlite3.connect(f'file:{SOURCES[0]/"corpus.sqlite3"}?mode=ro',uri=True);conn=sqlite3.connect(db);old.backup(conn);old.close()
 conn.execute('PRAGMA foreign_keys=OFF')
 conn.execute('CREATE TEMP TABLE keep_game(game_id TEXT PRIMARY KEY)');conn.executemany('INSERT INTO keep_game VALUES(?)',[(x,) for x in game_sets[0]])
 for table in ('observations','positions','games'):conn.execute(f'DELETE FROM {table} WHERE game_id NOT IN (SELECT game_id FROM keep_game)')
 conn.execute("UPDATE games SET split='development',split_reason='Development reference used to select the frozen candidate'")
 other=sqlite3.connect(f'file:{SOURCES[1]/"corpus.sqlite3"}?mode=ro',uri=True);other.row_factory=sqlite3.Row
 for table in ('games','positions','observations'):
  for row in other.execute('SELECT * FROM '+table):
   if row['game_id'] not in game_sets[1]:continue
   vals=tuple(row);conn.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in vals)+')',vals)
 other.close();conn.execute('DELETE FROM metadata');meta={'study_id':'brilliant-moves-unified','quantity_completion_authorized':True,'tuning_authorized':False,'quantity_limit':618,'candidate_source':'ac298a0d69ab51808857b089063348f2adac1101'}
 conn.executemany('INSERT INTO metadata VALUES(?,?)',[(k,json.dumps(v)) for k,v in meta.items()]);conn.commit();conn.execute('VACUUM')
 games=conn.execute('SELECT game_id,pgn,pgn_sha256,source_link,captured_at FROM games ORDER BY game_id').fetchall()
 (ROOT/'selected-games.pgn').write_text('\n\n'.join(x[1].strip() for x in games)+'\n')
 save(ROOT/'public-pgn-provenance.json',{'games':len(games),'scope':'Only the299primarygames; no monthly archives or HTTP metadata.','pgn_sha256':digest(ROOT/'selected-games.pgn'),'records':[dict(zip(('game_id','pgn','pgn_sha256','source_link','captured_at'),x)) for x in games]})
 # Avoid duplicating complete PGNs in the provenance index.
 x=load(ROOT/'public-pgn-provenance.json')
 for row in x['records']:row.pop('pgn')
 save(ROOT/'public-pgn-provenance.json',x)
 conn.row_factory=sqlite3.Row;obs=[dict(x) for x in conn.execute('SELECT * FROM active_observations ORDER BY game_id,ply,captured_at')]
 for row in obs:row['raw']=json.loads(row.pop('raw_json'))
 save(ROOT/'observations-export.json',obs);conn.close()
 save(ROOT/'manifest.json',{'metadata':meta,'primary_moves':618,'primary_games':len(games),'source_cohorts':provenance})
 save(ROOT/'policy-proposal.json',{'sample_moves':618,'collection_complete':True,'candidate_source_frozen':True,'source_commit':meta['candidate_source'],'development_was_used_to_choose_candidate':True,'prospective_candidate_tuning':False})
 save(ROOT/'methodology.json',load(SOURCES[1]/'methodology.json'))
 for file in ('hero-case.json','illustrative-cases.json'):
  shutil.copy2(SOURCES[0]/file,ROOT/file)
 for name in ('current-v2','proposed-v3'):
  dst=ROOT/'reference'/name;dst.mkdir(parents=True,exist_ok=True)
  for p in (SOURCES[1]/'reference'/name).iterdir():
   if p.is_file() and not p.is_symlink():shutil.copy2(p,dst/p.name)
  link=dst/'node_modules'
  if not link.exists():link.symlink_to('/private/tmp/mute-brilliants-native/node_modules',target_is_directory=True)
 for file in ('ec-score.ts','GPL-3.0.txt','AGPL-3.0.txt','package.json'):
  shutil.copy2(SOURCES[1]/'reference'/file,ROOT/'reference'/file)
 for file in ('analysis.py','replay.mts','replay-v3.mts'):
  text=(SOURCES[1]/file).read_text().replace('> 300','> 618').replace('quantity_limit: 300','quantity_limit: 618').replace("'quantity_limit': 300","'quantity_limit': 618").replace('proposal.sample_moves !== 300','proposal.sample_moves !== 618')
  if file=='replay-v3.mts':
   a=text.index('const proposal =');z=text.index('guard();',a)+len('guard();')
   text=text[:a]+'''const proposal = JSON.parse(readFileSync(join(root, 'policy-proposal.json'), 'utf8'));
const guard = () => { if (proposal.sample_moves !== 618 || !proposal.collection_complete || !proposal.candidate_source_frozen) throw new Error('Expected completed frozen-policy benchmark'); };
guard();'''+text[z:]
  text=text.replace("['discovery', 'reserved_validation']","['development', 'discovery', 'reserved_validation']")
  text=text.replace('Selected 600-move study; frozen policies only, no classifier tuning or population-generalization claim.', 'Selected benchmark with development and separate prospective games; no population-generalization claim.').replace('300 additional challenge moves. V3 was frozen before these labels; any later candidate requires discovery-only tuning and reserved-game evaluation.', 'Selected benchmark: development examples used to choose v3 are distinct from prospective and reserved validation games.')
  (ROOT/file).write_text(text)
 print(json.dumps({'moves':len(primary),'games':len(games),'snapshots':len(snapshots),'engine':merged['engine_sha256']}))
if __name__=='__main__':main()
