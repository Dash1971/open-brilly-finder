#!/usr/bin/env python3
"""Frozen independent200 preparation. Cached public PGNs only; no engine or current labels."""
import sys,json,sqlite3,hashlib,io,re,collections,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
s=importlib.util.spec_from_file_location('validation_corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);chess=m.chess
STUDIES=[BASE/'research'/x for x in ('brilliants-pilot-2026-11-03','brilliants-600-2026-11-03','brilliants-additional-300-2026-11-03','brilliants-unified-2026-11-03')]
CATS=('Queen Sacrifice','Rook Sacrifice','Bishop Sacrifice','Knight Sacrifice','All Types')
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def canon(f):return ' '.join(chess.Board(f).fen().split()[:4])
def walk(x):
 if isinstance(x,dict):
  if x.get('game_id') and isinstance(x.get('ply'),int):yield x
  for y in x.values():yield from walk(y)
 elif isinstance(x,list):
  for y in x:yield from walk(y)
def fens(x):
 if isinstance(x,dict):
  for y in x.values():yield from fens(y)
 elif isinstance(x,list):
  for y in x:yield from fens(y)
 elif isinstance(x,str) and re.match(r'^[rnbqkpRNBQKP1-8/]+ [wb] ',x):
  try:yield canon(x)
  except ValueError:pass
ex=json.loads((ROOT/'EXCLUSION-AUDIT.json').read_text());excluded=set(ex['numeric_game_ids']);save(ROOT/'exclude-games.json',{'game_ids':sorted(excluded),'source':'EXCLUSION-AUDIT.json; primary and all secondary reviewed/development games'})
games={};positions={};known=set()
for study in STUDIES:
 c=sqlite3.connect('file:'+str(study/'corpus.sqlite3')+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 for g in c.execute('SELECT * FROM games'):games.setdefault(g['game_id'],dict(g))
 for p in c.execute('SELECT * FROM positions'):
  positions.setdefault((p['game_id'],p['ply']),dict(p))
  if p['game_id'] in excluded:known.update((canon(p['fen_before']),canon(p['fen_after'])))
 c.close()
 for name in ('known-regression-fens.json','analysis-baseline.json','comparison-rules.json','primary-moves.json','observations-export.json'):
  p=study/name
  if p.exists():
   payload=json.loads(p.read_text())
   if name=='observations-export.json':payload=[x for x in walk(payload) if x.get('source_type')=='fresh_review']
   known.update(fens(payload))
for p in ROOT.parent.glob('*.json'):
 if p.stat().st_size<20000000:known.update(fens(json.loads(p.read_text())))
# Include full source histories from the original published examples.
p=BASE/'research/brilliants-2026-11-02/results.json'
if p.exists():
 payload=json.loads(p.read_text());known.update(fens(payload))
 for sample in payload.get('samples',[]):
  game=chess.pgn.read_game(io.StringIO(sample.get('moves','')))
  if game:
   b=game.board();known.add(canon(b.fen()))
   for move in game.mainline_moves():b.push(move);known.add(canon(b.fen()))
save(ROOT/'known-regression-fens.json',{'policy':'Conservative development exclusions; first four FEN fields, before and after sampled move','count':len(known),'positions':[{'canonical_first_four':x} for x in sorted(known)]})
cache=json.loads((ROOT/'cached-candidates-COLLECTOR-ONLY.json').read_text());rawcache={}
def original(x):
 for source in reversed(x.get('sources',[])):
  path=BASE/source
  if path not in rawcache:rawcache[path]=list(walk(json.loads(path.read_text())))
  found=next((r for r in rawcache[path] if str(r.get('game_id'))==x['game_id'] and r.get('ply')==x['ply']),None)
  if found:return dict(found)
 return dict(x)
conn=m.connect(ROOT/'corpus.sqlite3');usedgames=set();usedident=set();summary={}
for account in sys.argv[1:] or ('hansen','KNVB','GothamChess','nelsi','Hikaru'):
 top=ROOT/'evidence'/f'{account.lower()}-gallery-topup.json'
 inputs=[original(x) for x in cache if x['account']==account and x['status']=='eligible_cached_position_checked']
 if top.exists():inputs+=json.loads(top.read_text())
 unique={}
 for raw in inputs:
  gid=str(raw.get('game_id'));ply=raw.get('ply')
  if gid in excluded or not isinstance(ply,int):continue
  unique.setdefault((gid,ply),raw)
 wanted={g for g,p in unique};missing=wanted-set(games)
 # Cached monthly archives are scanned only for missing new source games.
 for study in STUDIES:
  for path in sorted((study/'original-pgn').glob(f'{account.lower()}-*.pgn'),reverse=True):
   if not missing:break
   text=path.read_text();stream=io.StringIO(text)
   meta_path=path.with_suffix('.response.json');meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
   while missing:
    start=stream.tell();headers=chess.pgn.read_headers(stream);end=stream.tell()
    if headers is None:break
    gid=m.game_id_from(headers.get('Link')) or m.game_id_from(headers.get('Site'))
    if gid not in missing:continue
    pg=text[start:end].strip()+'\n';game=chess.pgn.read_game(io.StringIO(pg));b=game.board()
    for ply,node in enumerate(game.mainline(),1):
     before=b.fen();san=b.san(node.move);b.push(node.move);positions[(gid,ply)]={'game_id':gid,'ply':ply,'san':san,'uci':node.move.uci(),'fen_before':before,'fen_after':b.fen(),'clock_seconds':node.clock()}
    games[gid]={'pgn':pg,'source_link':meta.get('source_link',f'https://api.chess.com/pub/player/{account.lower()}/games/'+headers.get('UTCDate','').replace('.','/')[:7]+'/pgn'),'captured_at':meta.get('captured_at',m.now()),'headers_json':json.dumps(dict(headers)),'white':headers.get('White'),'black':headers.get('Black')};missing.remove(gid)
 ready=[];rejected=[]
 for key,raw in unique.items():
  p=positions.get(key);g=games.get(key[0])
  if not p or not g:continue
  if canon(p['fen_before']) in known or canon(p['fen_after']) in known:rejected.append({'key':key,'reason':'development_FEN_overlap'});continue
  mover=g['white'] if p['fen_before'].split()[1]=='w' else g['black']
  if mover.lower()!=account.lower():rejected.append({'key':key,'reason':'account_to_move'});continue
  x=dict(raw);x['gallery_board_pieces']=x.get('gallery_board_pieces') or x.get('pieces') or x.get('board_pieces') or []
  board=m.observed_board(x)
  if board and board!=p['fen_after'].split()[0]:rejected.append({'key':key,'reason':'gallery_board_mismatch'});continue
  headers=json.loads(g['headers_json']);ns=re.search(r'/(live|daily)/',headers.get('Link',''));kind=ns[1] if ns else raw.get('game_type','live')
  cats=x.get('categories') or ([x['sampling_category']] if x.get('sampling_category') in CATS[:4] else [])
  x.update(game_id=key[0],ply=key[1],account=account,source_type='gallery',label='!!',categories=cats,game_type=kind,expected_game_type=kind,source_link=f'https://www.chess.com/analysis/game/{kind}/{key[0]}/review?move={key[1]-1}',historical_gallery_source_link=raw.get('source_link'),sampling_category=x.get('sampling_category') or (cats[0] if cats else 'All Types'),captured_at=raw.get('captured_at') or raw.get('capture_timestamp'),gallery_capture_reused=True,selected=False,sample_role='positive_candidate')
  x.update({k:p[k] for k in ('san','uci','fen_before','fen_after')});ready.append(x)
 def rank(x,cat):return hashlib.sha256(('mute-improvement-validation-v1|'+account+'|'+cat+'|'+x['game_id']+'|'+str(x['ply'])).encode()).hexdigest()
 groups={cat:sorted([x for x in ready if cat in x['categories'] or (cat=='All Types' and not x['categories'])],key=lambda x:rank(x,cat)) for cat in CATS};chosen=[];reserve=[];localgames=set();localident=set()
 while any(groups.values()):
  for cat in CATS:
   while groups[cat]:
    x=dict(groups[cat].pop(0));ident=(canon(x['fen_before']),x['uci'])
    if x['game_id'] in localgames or ident in localident or x['game_id'] in usedgames or ident in usedident:continue
    x['sampling_category']=cat;localgames.add(x['game_id']);localident.add(ident)
    if len(chosen)<20:x.update(selected=True,selection_status='primary',selected_at=m.now());chosen.append(x);usedgames.add(x['game_id']);usedident.add(ident)
    else:x.update(selected=False,selection_status='reserve');reserve.append(x)
    break
 for x in chosen+reserve:
  g=games[x['game_id']];m.import_pgn(conn,g['pgn'],g['source_link'],g['captured_at'],{x['game_id']})
 save(ROOT/'evidence'/f'{account.lower()}-gallery-selected.json',chosen);m.import_evidence(conn,ROOT/'evidence'/f'{account.lower()}-gallery-selected.json')
 save(ROOT/f'{account.lower()}-candidate-pool.json',ready);save(ROOT/f'{account.lower()}-reserves.json',reserve)
 save(ROOT/f'{account.lower()}-ui-queue.json',{'account':account,'prepared_at':m.now(),'targets':chosen,'reserves':reserve,'controls':[],'label_status':'Historical gallery candidates only; all current labels UNKNOWN','split_policy':'validation','control_source':'PREPARING; do not collect until queue-ready notification'})
 summary[account]={'targets':len(chosen),'reserves':len(reserve),'eligible_moves':len(ready),'categories':dict(collections.Counter(x['sampling_category'] for x in chosen)),'missing_games':sorted(missing),'rejected':rejected};print(json.dumps({account:summary[account]}),flush=True)
save(ROOT/'preparation-summary.json',summary);m.export(conn);conn.close()
