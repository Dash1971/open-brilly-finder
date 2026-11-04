"""Append one systematic reserve for this study; never infer a current label."""
from pathlib import Path
import json, importlib.util, sys, datetime
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('study_corpus',ROOT/'corpus.py')
corpus=importlib.util.module_from_spec(spec);spec.loader.exec_module(corpus)
account,failed_id,failed_ply=sys.argv[1],sys.argv[2],int(sys.argv[3])
canon=lambda f:' '.join(corpus.chess.Board(f).fen().split()[:4])
queuepath=ROOT/f'{account.lower()}-ui-queue.json';queue=json.loads(queuepath.read_text())
failed=next(x for x in queue['targets'] if x['game_id']==failed_id and x['ply']==failed_ply)
reviews=json.loads((ROOT/'evidence'/f'{account.lower()}-reviews-01.json').read_text())
assert any(x['game_id']==failed_id and x['ply']==failed_ply and x.get('sample_role')=='gallery_review_disagreement' for x in reviews)
known={x['canonical_first_four'] for x in json.loads((ROOT/'known-regression-fens.json').read_text())['positions']}
used={(canon(x['fen_before']),x['uci']) for p in (ROOT/'evidence').glob('*-gallery-selected.json') for x in json.loads(p.read_text())}
pp=ROOT/f'{account.lower()}-candidate-pool.json';pool=json.loads(pp.read_text());attempted={(x['game_id'],x['ply']) for x in queue['targets']}
ordered=[x for x in pool if x['sampling_category']==failed['sampling_category']]+[x for x in pool if x['sampling_category']!=failed['sampling_category']]
row=next(dict(x) for x in ordered if (x['game_id'],x['ply']) not in attempted and (canon(x['fen_before']),x['uci']) not in used and canon(x['fen_before']) not in known and canon(x['fen_after']) not in known)
row['gallery_analysis_source_link']=row['source_link']
row['source_link']=f"https://www.chess.com/analysis/game/{row.get('game_type','live')}/{row['game_id']}/review?move={row['ply']-1}"
row.update(selected=True,selection_status='reserve_selected',sample_role='positive_candidate',selected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_reason=f'First unused same-category reserve after displayed disagreement {failed_id}:{failed_ply}; fixed source order, no classifier-score selection.')
queue['targets'].append(row);queuepath.write_text(json.dumps(queue,indent=2)+'\n')
gp=ROOT/'evidence'/f'{account.lower()}-gallery-selected.json';gallery=json.loads(gp.read_text());gallery.append(row);gp.write_text(json.dumps(gallery,indent=2)+'\n')
for x in pool:
 if (x['game_id'],x['ply'])==(row['game_id'],row['ply']):x.update(row)
pp.write_text(json.dumps(pool,indent=2)+'\n')
c=corpus.connect(ROOT/'corpus.sqlite3');corpus.import_evidence(c,gp);c.close()
print(json.dumps({k:row[k] for k in ['game_id','ply','san','sampling_category','source_link']}))
