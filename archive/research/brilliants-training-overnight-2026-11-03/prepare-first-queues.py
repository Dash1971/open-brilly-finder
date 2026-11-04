from pathlib import Path
import json,hashlib,sqlite3,sys,io,re
from datetime import datetime,timezone
sys.path.insert(0,'/private/tmp/brilly-research-deps');import chess,chess.pgn
ROOT=Path(__file__).resolve().parent;W=ROOT.parents[1];OLD=W/'research/brilliants-prospective-v7-2026-11-03';now=datetime.now(timezone.utc).isoformat();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text());canon=lambda f:' '.join(chess.Board(f).fen().split()[:4])
exclude=set(map(str,load(OLD/'exclude-games.json')['game_ids']));known=set(load(OLD/'known-position-exclusions.json')['canonical_first_four']);sources=[OLD/'exclude-games.json',OLD/'known-position-exclusions.json']
for p in list((OLD/'evidence').glob('*-fresh-review.json'))+[OLD/'evidence/native-award-audit.json']:
 if not p.exists():continue
 sources.append(p)
 for x in load(p):
  if x.get('game_id'):exclude.add(str(x['game_id']))
  for f in ['fen_before','fen_after','observed_fen_before','observed_fen_after']:
   if x.get(f):known.add(canon(x[f]))
pool=load(OLD/'UNUSED-HISTORICAL-POOL.json');hist=load(OLD/'historical-pool-snapshot.json')['rows'];lookup={(str(x['game_id']),int(x['ply'])):x for x in hist};sources +=[OLD/'UNUSED-HISTORICAL-POOL.json',OLD/'historical-pool-snapshot.json'];groups={};rejected=[]
for x in pool:
 gid=str(x['game_id'])
 if gid in exclude:rejected.append({'game_id':gid,'reason':'previously_reviewed_game'});continue
 groups.setdefault(gid,[]).append(x)
cx=sqlite3.connect('file:'+str(OLD/'corpus.sqlite3')+'?mode=ro',uri=True);cx.row_factory=sqlite3.Row;ready=[]
for gid,noms in groups.items():
 raw=cx.execute('select * from games where game_id=?',(gid,)).fetchone()
 if not raw:rejected.append({'game_id':gid,'reason':'cached_PGN_not_in_prepared_database'});continue
 raw=dict(raw);g=chess.pgn.read_game(io.StringIO(raw['pgn']))
 if g is None or g.errors:rejected.append({'game_id':gid,'reason':'invalid_cached_PGN'});continue
 assert hashlib.sha256(raw['pgn'].encode()).hexdigest()==raw['pgn_sha256'];b=g.board();positions=[]
 for ply,node in enumerate(g.mainline(),1):
  before=b.fen();m=node.move;san=b.san(m);capture=b.is_capture(m);check=b.gives_check(m);b.push(m);after=b.fen();positions.append({'ply':ply,'san':san,'uci':m.uci(),'fen_before':before,'fen_after':after,'capture':capture,'check':check,'known_position_overlap':canon(before)in known or canon(after)in known,'current_label':'unknown'})
 valid=[]
 for nom in noms:
  p=positions[int(nom['ply'])-1]
  if any(nom.get(k)and nom[k]!=p[k]for k in ['san','uci','fen_before','fen_after']):rejected.append({'game_id':gid,'ply':nom['ply'],'reason':'nomination_PGN_mismatch'});continue
  h=lookup.get((gid,int(nom['ply'])),{});valid.append({**nom,**{k:p[k]for k in ['ply','san','uci','fen_before','fen_after']},'source_link':h.get('source_link'),'gallery_link':h.get('gallery_link'),'historical_gallery_label':'!!','current_label':'unknown','nomination_only_not_verified_current':True})
 if not valid:continue
 link=g.headers.get('Link',raw['source_link']);match=re.search(r'/(?:game/)?(live|daily)/(\d+)',link);ns=match.group(1)if match else'live';assert not match or match.group(2)==gid;split='assessment'if int(hashlib.sha256(('mute-overnight-2026-11-03-v1:'+gid).encode()).hexdigest(),16)%5==0 else'training';t=valid[0];url=f'https://www.chess.com/analysis/game/{ns}/{gid}/review?move={t["ply"]-1}'
 ready.append({'account':t['account'],'game_id':gid,'game_namespace':ns,'split':split,'split_assigned_at':now,'source_link':url,'review_url':url,'gallery_targets':valid,'primary_nomination_ply':t['ply'],'primary_nomination_san':t['san'],'pgn':raw['pgn'],'pgn_sha256':raw['pgn_sha256'],'pgn_source_link':raw['source_link'],'pgn_headers':dict(g.headers),'total_plies':len(positions),'positions':positions,'assessment_position_rule':'Known-overlap labeled positions are excluded from assessment; game split never changes after labels.','current_review_labels_observed':False})
cx.close();ready.sort(key=lambda x:hashlib.sha256(('mute-overnight-queue:'+x['game_id']).encode()).hexdigest());base={'prepared_at':now,'scope':'First cached gallery nomination wave. No new labels or classifier outputs used for selection. Public PGNs are identity/history evidence, not current labels.','split_rule':"sha256('mute-overnight-2026-11-03-v1:'+gameID) mod5==0 => assessment",'excluded_reviewed_games':len(exclude),'known_position_exclusions':len(known),'source_hashes':{str(p.relative_to(W)):sha(p)for p in sources},'rejections':rejected}
for suffix,accounts in [('A',{'nelsi','knvb'}),('B',{'hansen','gothamchess','hikaru'})]:
 games=[x for x in ready if x['account'].lower()in accounts];d={**base,'collector':'root'if suffix=='A'else'pilot_corpus','games':games,'counts':{'games':len(games),'nominees':sum(len(x['gallery_targets'])for x in games),'positions':sum(x['total_plies']for x in games),'training_games':sum(x['split']=='training'for x in games),'assessment_games':sum(x['split']=='assessment'for x in games)}};(ROOT/f'queue-{suffix}.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');print('queue-'+suffix,d['counts'])
(ROOT/'EXCLUSIONS-FIRST-WAVE.json').write_text(json.dumps({'created_at':now,'reviewed_game_ids':sorted(exclude),'known_canonical_before_after':sorted(known),'source_hashes':base['source_hashes']},indent=2)+'\n');(ROOT/'FIRST-QUEUE-MANIFEST.json').write_text(json.dumps({'created_at':now,'files':{n:sha(ROOT/n)for n in ['queue-A.json','queue-B.json','EXCLUSIONS-FIRST-WAVE.json']},'games':len(ready),'rejections':rejected},indent=2)+'\n')
