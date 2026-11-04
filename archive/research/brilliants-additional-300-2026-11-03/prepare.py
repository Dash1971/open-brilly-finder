#!/usr/bin/env python3
"""Bounded offline preparation for this additional300 study. Public PGN/gallery reuse only; no network or engines."""
import importlib.util,json,sqlite3,hashlib,collections,sys,resource,io,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'brilliants-600-2026-11-03';PILOT=ROOT.parent/'brilliants-pilot-2026-11-03'
spec=importlib.util.spec_from_file_location('additional_corpus',ROOT/'corpus.py');corpus=importlib.util.module_from_spec(spec);spec.loader.exec_module(corpus)
ACCOUNTS=('KNVB','hansen','GothamChess','Hikaru','nelsi');CATEGORIES=('Queen Sacrifice','Rook Sacrifice','Bishop Sacrifice','Knight Sacrifice')
def canonical(fen):return ' '.join(corpus.chess.Board(fen).fen().split()[:4])
def sources(account):
 if account in ('KNVB','hansen'):
  names=([f'{account.lower()}-gallery-candidates.json'] if account=='hansen' else [f'knvb-gallery-queen-sacrifice.json'])+[f'{account.lower()}-gallery-{x}-sacrifice.json' for x in ('rook','bishop','knight')]
 else:names=[f'{account.lower()}-gallery-eligible.json']
 return [OLD/'evidence'/name for name in names]
def inventory(account):
 excluded=set(json.loads((ROOT/'exclude-games.json').read_text())['game_ids']);seen=set();out=[]
 for path in sources(account):
  for raw in json.loads(path.read_text()):
   x=dict(raw);source=x.get('source_link') or x.get('source_url');gid=str(x.get('game_id') or '');ply=x.get('ply')
   if not gid:
    match=re.search(r'/live/(\d+).*?[?&]move=(\d+)',source or '')
    if not match:continue
    gid=match[1];ply=int(match[2])+1
   key=(gid,ply)
   if gid in excluded or key in seen:continue
   seen.add(key);category=x.get('sampling_category') or x.get('category') or (x.get('categories') or [None])[0]
   if category not in CATEGORIES:raise ValueError('Unverified category')
   x.update(game_id=gid,ply=ply,account=account,source_type='gallery',label='!!',source_link=source,sampling_category=category,categories=[category],prior_gallery_source=str(path.relative_to(OLD)),gallery_capture_reused=True)
   # Legacy DOM class list naming is preserved and also made readable by the shared validator.
   if x.get('pieces') and not x.get('board_placement'):x['gallery_board_pieces']=x['pieces']
   if x.get('board_pieces') and not x.get('board_placement'):x['gallery_board_pieces']=x['board_pieces']
   out.append(x)
 return out
def load_public_games(conn,account,rows):
 old=sqlite3.connect(f'file:{OLD / "corpus.sqlite3"}?mode=ro',uri=True);old.row_factory=sqlite3.Row
 wanted={x['game_id'] for x in rows};wanted-={x[0] for x in conn.execute('SELECT game_id FROM games')};provenance=[]
 for gid in sorted(wanted.copy()):
  g=old.execute('SELECT * FROM games WHERE game_id=?',(gid,)).fetchone()
  if not g:continue
  corpus.import_pgn(conn,g['pgn'],g['source_link'],g['captured_at'],{gid});wanted.remove(gid)
  provenance.append({k:g[k] for k in ('game_id','pgn_sha256','source_link','captured_at')}|{'reuse':'prior validated public PGN in SQLite'})
 old.close()
 for folder in (OLD/'original-pgn',PILOT/'original-pgn'):
  for path in sorted(folder.glob(f'{account.lower()}-*.pgn'),reverse=True):
   if not wanted:break
   # Extract only public provenance fields; raw HTTP response headers are never copied.
   meta=json.loads(path.with_suffix('.response.json').read_text());source=meta['source_link'];captured=meta['captured_at'];stream=io.StringIO(path.read_text());text=stream.getvalue()
   while wanted:
    start=stream.tell();headers=corpus.chess.pgn.read_headers(stream);end=stream.tell()
    if headers is None:break
    gid=corpus.game_id_from(headers.get('Link')) or corpus.game_id_from(headers.get('Site'))
    if gid not in wanted:continue
    corpus.import_pgn(conn,text[start:end],source,captured,{gid});wanted.remove(gid)
    g=conn.execute('SELECT pgn_sha256 FROM games WHERE game_id=?',(gid,)).fetchone()
    provenance.append({'game_id':gid,'pgn_sha256':g['pgn_sha256'],'source_link':source,'captured_at':captured,'monthly_body_sha256':meta['sha256'],'reuse':'selected game from existing local public monthly PGN'})
 (ROOT/f'{account.lower()}-pgn-reuse-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 return sorted(wanted)
def prepare(account):
 if account not in ACCOUNTS:raise ValueError('Outside study accounts')
 conn=corpus.connect(ROOT/'corpus.sqlite3');known={x['canonical_first_four'] for x in json.loads((ROOT/'known-regression-fens.json').read_text())['positions']};rows=inventory(account);missing=load_public_games(conn,account,rows);ready=[];rejected=[]
 for raw in rows:
  x=dict(raw);key=(x['game_id'],x['ply']);p=conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?',key).fetchone()
  if not p:continue
  if canonical(p['fen_before']) in known or canonical(p['fen_after']) in known:rejected.append({'game_id':key[0],'ply':key[1],'reason':'prior_position'});continue
  g=conn.execute('SELECT white,black FROM games WHERE game_id=?',(key[0],)).fetchone();mover=g['white'] if p['fen_before'].split()[1]=='w' else g['black']
  if mover.lower()!=account.lower():rejected.append({'game_id':key[0],'ply':key[1],'reason':'gallery_account_to_move_mismatch'});continue
  board=corpus.observed_board(x)
  if board is not None and board!=p['fen_after'].split()[0]:rejected.append({'game_id':key[0],'ply':key[1],'reason':'captured_gallery_board_mismatch'});continue
  x.update({k:p[k] for k in ('san','uci','fen_before','fen_after')});ready.append(x)
 # Existing new-stage choices are immutable during collection; prepare only appends reserves to their pool.
 path=ROOT/'evidence'/f'{account.lower()}-gallery-selected.json'
 chosen=json.loads(path.read_text()) if path.exists() else []
 used=set()
 for other in (ROOT/'evidence').glob('*-gallery-selected.json'):
  for x in json.loads(other.read_text()):used.add((canonical(x['fen_before']),x['uci']))
 if not chosen:
  groups={c:[x for x in ready if x['sampling_category']==c] for c in CATEGORIES}
  while len(chosen)<30 and any(groups.values()):
   for category in CATEGORIES:
    while groups[category]:
     x=groups[category].pop(0);identity=(canonical(x['fen_before']),x['uci'])
     if identity in used:rejected.append({'game_id':x['game_id'],'ply':x['ply'],'reason':'duplicate_positive_position_move'});continue
     used.add(identity);x.update(selected=True,selection_status='primary',sample_role='positive_candidate',selection_stage='additional300',selected_at=corpus.now());chosen.append(x);break
    if len(chosen)>=30:break
  path.write_text(json.dumps(chosen,indent=2)+'\n')
 corpus.import_evidence(conn,path)
 chosenkeys={(x['game_id'],x['ply']) for x in chosen}
 for x in ready:x['selected']=(x['game_id'],x['ply']) in chosenkeys;x['selection_status']='primary' if x['selected'] else 'reserve';x['sample_role']='positive_candidate'
 (ROOT/f'{account.lower()}-candidate-pool.json').write_text(json.dumps(ready,indent=2)+'\n')
 gameids={x['game_id'] for x in chosen};oldbank=OLD/f'control-candidates-v2-{account.lower()}.json'
 completedbank=ROOT/f'control-candidates-v2-{account.lower()}.json'
 bank=json.loads((completedbank if completedbank.exists() else oldbank).read_text())
 controls=[x for x in bank['rows'] if x['game_id'] in gameids and (x['game_id'],x['ply']) not in chosenkeys and canonical(x['fen_before']) not in known and canonical(x['fen_after']) not in known]
 targets=[]
 for raw in chosen:
  x=dict(raw);x['source_link']=f"https://www.chess.com/analysis/game/{x.get('game_type', 'live')}/{x['game_id']}/review?move={x['ply']-1}";targets.append(x)
 controlsource=bank.get('source') or {'file':str(oldbank.relative_to(OLD)),'sha256':hashlib.sha256(oldbank.read_bytes()).hexdigest(),'policy':'b3585f2 raw-v2 legal offer reused unchanged; bank extension pending for newly reused PGNs'}
 q={'targets':targets,'controls':controls,'account':account,'prepared_at':corpus.now(),'label_status':'Historical gallery candidates; controls UNKNOWN until explicit current review.','control_source':controlsource,'split_policy':json.loads((ROOT/'PLAN.json').read_text())['selection']['partitions']}
 (ROOT/f'{account.lower()}-ui-queue.json').write_text(json.dumps(q,indent=2)+'\n')
 audit={'prepared_at':corpus.now(),'selected':len(chosen),'available_validated_unseen_candidates':len(ready),'categories':dict(collections.Counter(x['sampling_category'] for x in chosen)),'games':len(gameids),'controls':len(controls),'missing_public_pgn_game_ids':missing,'rejected':rejected,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 (ROOT/f'{account.lower()}-preparation-audit.json').write_text(json.dumps(audit,indent=2)+'\n');out=corpus.export(conn);conn.close();audit['identity_mismatches']=out['validation']['indexing_mismatches'];return audit
if __name__=='__main__':
 for account in sys.argv[1:]:
  result=prepare(account);print(json.dumps({k:v for k,v in result.items() if k not in ('rejected','missing_public_pgn_game_ids')},indent=2),flush=True)
