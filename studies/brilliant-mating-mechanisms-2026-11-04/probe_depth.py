"""Frozen bounded diagnostic; no classifier edits or validation claim."""
import ast,hashlib,io,json,math,signal,sys,time
from pathlib import Path
from datetime import datetime,timezone
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
H=Path(__file__).resolve().parent
SOURCE=H/'CASES.json'
METHOD=H.parent/'brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
ENGINE='/opt/homebrew/bin/stockfish'
SHA='ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
KEYS=['148103018608:20','168956462236:46','165547173668:60']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
def guard():
 if time.monotonic()-START>=120:raise TimeoutError('Frozen120 second total cap; no retry')
def alarm(*args):raise TimeoutError('Frozen120 second total cap; no retry')
def line_detail(board,line,mover):
 b=board.copy(stack=True);sans=[]
 for u in line['moves']:
  m=chess.Move.from_uci(u);sans.append(b.san(m));b.push(m)
 typ='mate' if 'mate' in line else 'cp';v=line[typ];mv=v*(1 if mover else -1)
 mapped=(1000 if mv>0 else -1000) if typ=='mate' else max(-1000,min(1000,mv))
 return {**line,'score_orientation':'white','mover_score_type':typ,'mover_score':mv,'mover_mapped_cp':mapped,'mover_win_percent':100/(1+math.exp(-.00368208*mapped)),'san':' '.join(sans)}
def details(b,s,mover):
 for w in ['current','previous']:
  if s.get(w):s[w]['lines']=[line_detail(b,l,mover) for l in s[w]['lines']]
 return s
if __name__=='__main__':
 if (H/'DEPTH.json').exists() or (H/'DEPTH-PROTOCOL.json').exists():raise ValueError('Refuse overwrite/retry')
 tree=ast.parse(METHOD.read_text());funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['packed','search']]
 namespace={'chess':chess,'time':time,'guard':guard,'SEARCH_SPENT':0.,'ACTIVE_SEARCH':None}
 exec(compile(ast.Module(body=funcs,type_ignores=[]),str(METHOD),'exec'),namespace)
 protocol={'frozen_at':now(),'purpose':'Diagnostic only, selected known misses; not fresh validation. No reclassification, training, or threshold changes.','keys':KEYS,'engine':ENGINE,'engine_sha256':SHA,'threads':1,'hash_mb':64,'nodes_per_query':3000000,'maximum_queries':9,'total_wall_cap_seconds':120,'retry_policy':'none; no outcome tuning','order':['before MultiPV2','after MultiPV2','before played-only singlePV'],'history':'Full original PGN move stack, fresh game session and Clear Hash per query','unrestricted_method':'AST-extracted packed/search from frozen collector, same-depth current/previous','forced_method':'engine.analyse before, root_moves=[played], MultiPV1, 3M nodes','mapping':'Scores white-oriented; mover sign; cp clamped +/-1000, mate sign mapped +/-1000; 100/(1+exp(-0.00368208*mapped_cp)); loss is before best minus after best in percentage points, signed and clipped shown','caveat':'Forced played-only search has separate search context and is not guaranteed a fair comparison with unrestricted MultiPV or after-position search. Larger node budget can change principal variations without resolving classifier gates.','source_sha256':sha(SOURCE),'method_sha256':sha(METHOD),'script_sha256':sha(__file__),'base_rule_sha256':sha(H.parent/'brilliant-mating-prospective-2026-11-04/base_rule.py'),'python_chess_sha256':sha(chess.__file__)}
 if sha(ENGINE)!=SHA:raise ValueError('Engine hash mismatch')
 cases={c['key']:c for c in json.loads(SOURCE.read_text())}
 write(H/'DEPTH-PROTOCOL.json',protocol)
 START=time.monotonic();signal.signal(signal.SIGALRM,alarm);signal.alarm(120)
 result={'status':'running','started_at':now(),'protocol_sha256':sha(H/'DEPTH-PROTOCOL.json'),'queries_completed':0,'cases':[]}
 write(H/'DEPTH.json',result)
 engine=None
 try:
  engine=chess.engine.SimpleEngine.popen_uci(ENGINE);engine.configure({'Threads':1,'Hash':64});result['engine_id']=engine.id
  for key in KEYS:
   c=cases[key];game=chess.pgn.read_game(io.StringIO(c['pgn']));assert game and not game.errors
   b=game.board();ply=int(c['ply'])
   for i,m in enumerate(game.mainline_moves(),1):
    if i==ply:before=b.copy(stack=True);played=m;b.push(m);after=b.copy(stack=True);break
    b.push(m)
   assert before.fen()==c['fen_before'] and after.fen()==c['fen_after'] and played.uci()==c['uci']
   mover=before.turn;row={'key':key,'san':c['san'],'mover':c['mover'],'pgn_sha256':hashlib.sha256(c['pgn'].encode()).hexdigest(),'before_history_plies':len(before.move_stack),'after_history_plies':len(after.move_stack),'original_300k':{k:c[k] for k in ['roots','base_rule_failures','features']}}
   result['cases'].append(row)
   for name,board in [('before',before),('after',after)]:
    guard();engine.configure({'Clear Hash':None});s=namespace['search'](engine,board,3000000,object());row[name]=details(board,s,mover);result['queries_completed']+=1;write(H/'DEPTH.json',result)
   guard();engine.configure({'Clear Hash':None});t=time.monotonic();info=engine.analyse(before,chess.engine.Limit(nodes=3000000),root_moves=[played],game=object());row['forced_played']={'depth':info.get('depth'),'reported_nodes':info.get('nodes'),'elapsed_seconds':time.monotonic()-t,'line':line_detail(before,namespace['packed'](info),mover),'context_caveat':protocol['caveat']};result['queries_completed']+=1
   def wc(l):
    if 'mover_win_percent' in l:return l['mover_win_percent']
    typ='mate' if 'mate' in l else 'cp';v=l[typ]*(1 if mover else -1);v=(1000 if v>0 else -1000) if typ=='mate' else max(-1000,min(1000,v));return 100/(1+math.exp(-.00368208*v))
   row['comparison']={}
   for w in ['current','previous']:
    oldb=c['roots']['before'][w];olda=c['roots']['after'][w];nb=row['before'].get(w);na=row['after'].get(w)
    d={'original_before_after_loss_pp_signed':wc(oldb[0])-wc(olda[0]),'original_best_san':oldb[0]['san'].split()[0],'original_played_rank_in_top2':next((i+1 for i,l in enumerate(oldb) if l['moves'][0]==played.uci()),None)}
    if nb and na:
     loss=wc(nb['lines'][0])-wc(na['lines'][0]);d.update(before_after_loss_pp_signed=loss,before_after_loss_pp_clipped=max(0,loss),best_san=nb['lines'][0]['san'].split()[0],played_rank_in_top2=next((i+1 for i,l in enumerate(nb['lines']) if l['moves'][0]==played.uci()),None),before_best_vs_forced_loss_pp_signed=wc(nb['lines'][0])-wc(row['forced_played']['line']))
    row['comparison'][w]=d
   write(H/'DEPTH.json',result)
  result['status']='complete'
 except Exception as e:result.update(status='incomplete',reason=repr(e))
 finally:
  signal.alarm(0)
  if engine:
   engine.close()
  result.update(completed_at=now(),wall_seconds=time.monotonic()-START);write(H/'DEPTH.json',result)
 print(json.dumps({k:result[k] for k in ['status','queries_completed','wall_seconds']}))
