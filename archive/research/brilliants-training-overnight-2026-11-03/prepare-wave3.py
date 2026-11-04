"""Study-local offline PGN resolution for existing unused gallery nominations."""
from pathlib import Path
import json,sqlite3,hashlib,sys,io,re
from datetime import datetime,timezone
sys.path.insert(0,'/private/tmp/brilly-research-deps');import chess,chess.pgn
ROOT=Path(__file__).resolve().parent;W=ROOT.parents[1];load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();canon=lambda f:' '.join(chess.Board(f).fen().split()[:4]);now=datetime.now(timezone.utc).isoformat()
rows=load(ROOT/'FRESH-METADATA-NOMINATIONS-03.json')['rows'];wanted={x['game_id']for x in rows};pgns={};receipts=[];old=ROOT.parent/'brilliants-prospective-v7-2026-11-03';known=set(load(ROOT/'ASSESSMENT-POSITION-EXCLUSIONS.json')['canonical_first_four'])
for path in list((W/'research').rglob('corpus.sqlite3'))+[old/'workingassessment.db']:
 if path.parent==ROOT:continue
 cx=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);cx.row_factory=sqlite3.Row;hits=0
 for gid in wanted-set(pgns):
  row=cx.execute('select * from games where game_id=?',(gid,)).fetchone()
  if row:pgns[gid]={**dict(row),'cached_source':str(path.relative_to(W))};hits+=1
 cx.close()
 if hits:receipts.append({'source':str(path.relative_to(W)),'sha256':sha(path),'PGNs_reused':hits})
 if set(pgns)==wanted:break
# Read public monthly cache only, no network or private response metadata copied.
for path in (W/'research').rglob('*.json'):
 if set(pgns)==wanted:break
 if 'original-pgn'not in path.parts or not re.search(r'20\d\d-\d\d',path.name):continue
 try:d=load(path)
 except Exception:continue
 stack=[d];hits=0
 while stack:
  x=stack.pop()
  if isinstance(x,dict):
   if isinstance(x.get('pgn'),str):
    pgn=x['pgn'];match=re.search(r'\[Link "[^\"]*/(?:live|daily)/(\d+)"\]',pgn)or re.search(r'/(?:live|daily)/(\d+)',x.get('url',''))
    if match and match.group(1)in wanted-set(pgns):
     gid=match.group(1);pgns[gid]={'game_id':gid,'pgn':pgn,'pgn_sha256':hashlib.sha256(pgn.encode()).hexdigest(),'source_link':x.get('url',str(path.relative_to(W))),'cached_source':str(path.relative_to(W))};hits+=1
   for val in x.values():
    if isinstance(val,(dict,list)):stack.append(val)
    elif isinstance(val,str)and val.startswith('{'):
     try:stack.append(json.loads(val))
     except ValueError:pass
  elif isinstance(x,list):stack.extend(x)
 if hits:receipts.append({'source':str(path.relative_to(W)),'sha256':sha(path),'PGNs_reused':hits})
# Public monthly PGN text caches preserve complete games outside older selected databases.
for path in (W/'research').rglob('*.pgn'):
 if set(pgns)==wanted:break
 if 'original-pgn'not in path.parts:continue
 text=path.read_text();hits=0
 for block in re.split(r'(?=\[Event ")',text):
  m=re.search(r'\[Link "[^"]*/(?:live|daily)/(\d+)"\]',block)
  if m and m.group(1)in wanted-set(pgns):
   gid=m.group(1);pgn=block.strip()+'\n';pgns[gid]={'game_id':gid,'pgn':pgn,'pgn_sha256':hashlib.sha256(pgn.encode()).hexdigest(),'source_link':str(path.relative_to(W)),'cached_source':str(path.relative_to(W))};hits+=1
 if hits:receipts.append({'source':str(path.relative_to(W)),'sha256':sha(path),'PGNs_reused':hits})
bygame={}
for row in rows:bygame.setdefault(row['game_id'],[]).append(row)
games=[];rejected=[]
for gid,noms in bygame.items():
 if gid not in pgns:rejected.append({'game_id':gid,'reason':'not_in_existing_cached_PGNs'});continue
 raw=pgns[gid];g=chess.pgn.read_game(io.StringIO(raw['pgn']))
 if g is None or g.errors:rejected.append({'game_id':gid,'reason':'invalid_PGN'});continue
 assert hashlib.sha256(raw['pgn'].encode()).hexdigest()==raw['pgn_sha256'];b=g.board();positions=[]
 for ply,node in enumerate(g.mainline(),1):
  before=b.fen();m=node.move;san=b.san(m);capture=b.is_capture(m);check=b.gives_check(m);b.push(m);after=b.fen();positions.append({'ply':ply,'san':san,'uci':m.uci(),'fen_before':before,'fen_after':after,'capture':capture,'check':check,'known_position_overlap':canon(before)in known or canon(after)in known,'current_label':'unknown'})
 valid=[]
 for nom in noms:
  if not 0<int(nom['ply'])<=len(positions):continue
  p=positions[nom['ply']-1]
  if any(nom.get(k)and nom[k]!=p[k]for k in ['san','uci','fen_before','fen_after']):rejected.append({'game_id':gid,'ply':nom['ply'],'reason':'nomination_identity_mismatch'});continue
  valid.append({**nom,**{k:p[k]for k in ['ply','san','uci','fen_before','fen_after']},'historical_gallery_label':'!!','current_label':'unknown','nomination_only_not_verified_current':True})
 if not valid:continue
 link=g.headers.get('Link',raw['source_link']);match=re.search(r'/(live|daily)/(\d+)',link);ns=match.group(1)if match else'live';assert not match or match.group(2)==gid;nom=valid[0];url=f'https://www.chess.com/analysis/game/{ns}/{gid}/review?move={nom["ply"]-1}';split='assessment'if int(hashlib.sha256(('mute-overnight-2026-11-03-v1:'+gid).encode()).hexdigest(),16)%5==0 else'training'
 games.append({'account':nom['account'],'game_id':gid,'game_namespace':ns,'split':split,'split_assigned_at':now,'source_link':url,'review_url':url,'gallery_targets':valid,'primary_nomination_ply':nom['ply'],'primary_nomination_san':nom['san'],'pgn':raw['pgn'],'pgn_sha256':raw['pgn_sha256'],'pgn_source_link':raw['source_link'],'cached_source':raw['cached_source'],'pgn_headers':dict(g.headers),'total_plies':len(positions),'positions':positions,'assessment_position_rule':'ASSESSMENT-POSITION-EXCLUSIONS.json governs all assessment labels; game split never changes after labels.','current_review_labels_observed':False})
for suffix,accounts in [('A',{'nelsi','knvb'}),('B',{'hansen','gothamchess','hikaru'})]:
 selected=[x for x in games if x['account'].lower()in accounts];selected.sort(key=lambda x:hashlib.sha256(('mute-overnight-queue:'+x['game_id']).encode()).hexdigest());d={'prepared_at':now,'wave':3,'scope':'New visible gallery nominations resolved against existing official PGN caches. No current review labels or model outputs used.','collector':'root'if suffix=='A'else'pilot_corpus','split_rule':"sha256('mute-overnight-2026-11-03-v1:'+gameID) mod5==0 assessment",'assessment_position_exclusions':'ASSESSMENT-POSITION-EXCLUSIONS.json','source_receipts':receipts,'rejections':rejected,'games':selected,'counts':{'games':len(selected),'nominees':sum(len(x['gallery_targets'])for x in selected),'positions':sum(x['total_plies']for x in selected),'training_games':sum(x['split']=='training'for x in selected),'assessment_games':sum(x['split']=='assessment'for x in selected)}};(ROOT/f'queue-{suffix}-wave3.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');print(suffix,d['counts'])
(ROOT/'WAVE3-MANIFEST.json').write_text(json.dumps({'prepared_at':now,'files':{name:sha(ROOT/name)for name in ['queue-A-wave3.json','queue-B-wave3.json','ASSESSMENT-POSITION-EXCLUSIONS.json']},'games':len(games),'rejections':rejected,'missing_PGNs':sorted(wanted-set(pgns))},indent=2)+'\n');print('missing',sorted(wanted-set(pgns)))
