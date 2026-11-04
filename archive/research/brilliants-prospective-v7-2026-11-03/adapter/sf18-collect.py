#!/usr/bin/env python3
"""Bounded prospective SF18 collection. No labels choose searches; root GO required."""
import argparse,hashlib,io,json,sqlite3,sys,time
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
ROOT=Path(__file__).resolve().parents[1]
ENGINE='/opt/homebrew/bin/stockfish'
ENGINE_SHA='ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
SEARCH_SPENT=0.;ACTIVE_SEARCH=None;START=time.monotonic()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def write(p,d):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
def guard():
 active=time.monotonic()-ACTIVE_SEARCH if ACTIVE_SEARCH is not None else 0
 if (ROOT/'STOP').exists():raise TimeoutError('Parent STOP')
 if SEARCH_SPENT+active>=600 or time.monotonic()-START>=600:raise TimeoutError('Fixed600-second stream cap; no retry')
def packed(info):
    value = info['score'].white()
    return {('mate' if value.is_mate() else 'cp'):
            value.mate() if value.is_mate() else value.score(),
            'moves': [move.uci() for move in info['pv']]}


def search(engine, board, budget, session):
    global SEARCH_SPENT, ACTIVE_SEARCH
    guard()
    if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material():
        value = {'mate': -1 if board.turn else 1} if board.is_checkmate() else {'cp': 0}
        return {'current': {'depth': 99, 'lines': [{**value, 'moves': []}]},
                'terminal': True, 'quality': f'frozen-test-sf18-{budget}'}
    count = min(2, board.legal_moves.count())
    pending, completed = [], []
    start = time.monotonic()
    ACTIVE_SEARCH = start
    try:
        with engine.analysis(board, chess.engine.Limit(nodes=budget), multipv=count, game=session) as stream:
            for info in stream:
                guard()
                if not all(key in info for key in ('score', 'pv', 'depth')):
                    continue
                if not info['pv'] or info.get('upperbound') or info.get('lowerbound'):
                    continue
                rank = info.get('multipv', 1)
                if rank != len(pending) + 1:
                    pending = []
                if rank != len(pending) + 1:
                    continue
                if info['pv'][0] not in board.legal_moves:
                    continue
                pending.append(info)
                if rank == count:
                    if (len({line['depth'] for line in pending}) == 1 and
                            len({line['pv'][0] for line in pending}) == count):
                        snap = {'depth': pending[0]['depth'], 'lines': [packed(line) for line in pending],
                                'reported_nodes': pending[-1].get('nodes')}
                        if not completed or snap['depth'] > completed[-1]['depth']:
                            completed.append(snap)
                            completed = completed[-2:]
                        else:
                            completed[-1] = snap
                    pending = []
    finally:
        SEARCH_SPENT += time.monotonic() - start
        ACTIVE_SEARCH = None
    if not completed:
        raise ValueError('No exact complete same-depth comparison at ' + board.fen())
    return {'current': completed[-1], 'previous': completed[-2] if len(completed) > 1 else None,
            'terminal': False, 'quality': f'frozen-test-sf18-{budget}',
            'elapsed_seconds': round(time.monotonic() - start, 6)}



def main():
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['core','supplement','panel']);parser.add_argument('source',type=Path);parser.add_argument('queue',type=Path);parser.add_argument('output',type=Path);a=parser.parse_args()
 go=json.loads((ROOT/'SF18-GO.json').read_text());job=go['streams'][a.stage]
 if not go.get('browsers_closed') or not job.get('authorized') or job['source_sha256']!=sha(a.source) or job['queue_sha256']!=sha(a.queue) or job['collector_sha256']!=sha(__file__):raise ValueError('Root stream GO/hash binding absent')
 if sha(ENGINE)!=ENGINE_SHA:raise ValueError('PinnedSF18 changed')
 if a.output.exists():raise ValueError('Refuse existing output; no automatic retry/resume')
 frozen=json.loads(a.queue.read_text());targets=frozen if isinstance(frozen,list) else frozen.get('targets',[])
 if a.stage=='core' and (len(targets)!=200 or len({(str(t['game_id']),int(t['ply'])) for t in targets})!=200):raise ValueError('Primary requires200 identities')
 if a.stage=='panel' and len(targets)>300:raise ValueError('Panel candidate cap')
 if a.stage=='supplement':wanted={(str(x['game_id']),int(x['ply'])) for x in frozen['positions']}
 else:wanted={(str(t['game_id']),p) for t in targets for p in range(max(0,int(t['ply'])-2),int(t['ply'])+1)}
 cap={'core':600,'supplement':1200,'panel':900}[a.stage]
 if len(wanted)>cap:raise ValueError('Frozen position cap exceeded')
 if a.stage=='supplement':
  core=json.loads(Path(frozen['core_path']).read_text())
  if sha(frozen['core_path'])!=frozen['core_sha256']:raise ValueError('Core changed')
  if any(f'{g}:{p}' in core['snapshots'] for g,p in wanted):raise ValueError('Supplement would replace core')
 if a.stage=='panel':pool=json.loads(a.source.read_text());games={str(g['game_id']):g['pgn'] for g in pool['games']}
 else:
  conn=sqlite3.connect('file:'+str(a.source.resolve())+'?mode=ro',uri=True);games={str(g):pgn for g,pgn in conn.execute('select game_id,pgn from games')};conn.close()
 result={'status':'running','stage':a.stage,'started_at':now(),'engine_sha256':ENGINE_SHA,'nodes_per_position':300000,'threads':1,'hash_mb':64,'source_sha256':sha(a.source),'queue_sha256':sha(a.queue),'script_sha256':sha(__file__),'targets':[],'snapshots':{},'expected_snapshots':len(wanted),'search_cap_seconds':600,'wall_cap_seconds':600,'session_policy':'Fresh stream process; clear hash/new game pergame; chronological requested full-PGN positions; no core warmups or substitution.'};write(a.output,result)
 if not wanted:result.update(status='complete',completed_at=now());write(a.output,result);return
 engine=chess.engine.SimpleEngine.popen_uci(ENGINE);engine.configure({'Threads':1,'Hash':64});result['engine_id']=engine.id;result['engine_option_defaults']={k:{'default':v.default,'type':v.type} for k,v in engine.options.items()}
 try:
  for gid in sorted({g for g,p in wanted}):
   guard();pgn=games[gid];game=chess.pgn.read_game(io.StringIO(pgn))
   if game is None or game.errors:raise ValueError('Invalid frozen PGN:'+gid)
   positions={p for g,p in wanted if g==gid};board=game.board();boards={0:board.copy(stack=True)};moves={}
   for ply,move in enumerate(game.mainline_moves(),1):
    san=board.san(move);before=board.fen();board.push(move);moves[ply]={'san':san,'uci':move.uci(),'fen_before':before,'fen_after':board.fen()}
    if ply in positions:boards[ply]=board.copy(stack=True)
   if any(p not in boards for p in positions):raise ValueError('Missing requested PGN position')
   engine.configure({'Clear Hash':None});session=object();pgnsha=hashlib.sha256(pgn.encode()).hexdigest()
   for ply in sorted(positions):
    snap=search(engine,boards[ply],300000,session);snap.update(game_id=gid,position_ply=ply,fen=boards[ply].fen(),pgn_sha256=pgnsha);result['snapshots'][f'{gid}:{ply}']=snap;result['recorded_search_seconds']=SEARCH_SPENT;write(a.output,result)
   for t in targets:
    if str(t['game_id'])!=gid:continue
    ply=int(t['ply']);d=moves[ply]
    if t.get('pgn_sha256') and t['pgn_sha256']!=pgnsha:raise ValueError('Frozen PGN digest mismatch')
    for field in ['uci','san','fen_before','fen_after']:
     if t.get(field) is not None and t[field]!=d[field]:raise ValueError('Frozen target identity mismatch:'+gid+':'+str(ply)+':'+field)
    result['targets'].append({'game_id':gid,'ply':ply,**d,'pgn_sha256':pgnsha,'snapshot_ids':[f'{gid}:{p}' for p in range(max(0,ply-2),ply+1)]})
  result.update(status='complete',completed_at=now())
 except Exception as e:result.update(status='incomplete',reason=str(e),completed_at=now())
 finally:engine.quit();result['recorded_search_seconds']=SEARCH_SPENT;result['wall_seconds']=time.monotonic()-START;write(a.output,result)
 print(json.dumps({'stage':a.stage,'status':result['status'],'snapshots':len(result['snapshots']),'recorded_search_seconds':SEARCH_SPENT}))
if __name__=='__main__':main()
