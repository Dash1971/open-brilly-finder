"""One bounded saved-identity acceptance experiment; no label-driven scoring."""
import hashlib
import io
import json
import pathlib
import sqlite3
import sys
import time
from datetime import datetime, timezone
sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess
import chess.engine
import chess.pgn

ROOT = pathlib.Path(__file__).resolve().parent
FINAL = ROOT.parents[2] / 'brilliants-final-2026-11-03'
ENGINE = pathlib.Path('/opt/homebrew/bin/stockfish')
EXPECTED_ENGINE = 'ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
VALUES = {chess.PAWN:90,chess.KNIGHT:300,chess.BISHOP:300,chess.ROOK:500,chess.QUEEN:1000,chess.KING:0}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def raw(board,mover):return sum(VALUES[p.piece_type]*(1 if p.color==mover else -1) for p in board.piece_map().values())
def save(result):
    tmp=ROOT/'acceptance-results.json.tmp'
    tmp.write_text(json.dumps(result,indent=2)+'\n')
    tmp.replace(ROOT/'acceptance-results.json')
def physical_line(board,ucis,mover,initial,accepted_square=None):
    b=board.copy(stack=True)
    path=[raw(b,mover)]
    events=[]
    for uci in ucis[:20]:
        move=chess.Move.from_uci(uci)
        assert move in b.legal_moves
        victim=b.piece_at(move.to_square)
        if b.is_en_passant(move):victim=chess.Piece(chess.PAWN,not b.turn)
        moving=b.piece_at(move.from_square)
        event={'uci':uci,'san':b.san(move),'mover':'white' if b.turn else 'black',
            'moving_role':chess.piece_name(moving.piece_type),'capture_role':chess.piece_name(victim.piece_type) if victim else None,
            'queen_capture':bool(victim and victim.piece_type==chess.QUEEN),
            'promotion':chess.piece_name(move.promotion) if move.promotion else None,
            'promotion_material_credit':VALUES[move.promotion]-90 if move.promotion else 0,
            'material_before':raw(b,mover),
            'cross_square_mover_capture':bool(victim and b.turn==mover and accepted_square is not None and move.to_square!=accepted_square)}
        b.push(move)
        event.update(material_after=raw(b,mover),fen_after=b.fen(),checkmate=b.is_checkmate(),stalemate=b.is_stalemate())
        event['restores_pre_original_material']=event['mover']==('white' if mover else 'black') and event['material_after']>=initial
        path.append(event['material_after']);events.append(event)
    return {'raw_material_path':path,'events':events,'any_queen_capture':any(x['queen_capture'] for x in events),
        'any_promotion':any(x['promotion'] for x in events),
        'any_cross_square_mover_capture':any(x['cross_square_mover_capture'] for x in events),
        'mover_restores_pre_original_material_on_PV':any(x['restores_pre_original_material'] for x in events)}
def score_fields(line,mover):
    sign=1 if mover else -1
    cp=line.get('cp');mate=line.get('mate')
    relative=cp*sign if mate is None else None
    relative_mate=mate*sign if mate is not None else None
    normalized=max(-1000,min(1000,relative)) if relative is not None else (1000 if relative_mate>0 else -1000 if relative_mate<0 else 0)
    return {'cp_white':cp,'mate_white':mate,'cp_mover':relative,'mate_mover':relative_mate,'normalized_mover':normalized}
def pack_line(info):
    score=info['score'].white()
    return {('mate' if score.is_mate() else 'cp'):score.mate() if score.is_mate() else score.score(),
        'moves':[m.uci() for m in info['pv'][:20]]}
def search(engine,board,session,root_moves,remaining):
    begin=time.monotonic()
    if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material():
        value={'mate':-1 if board.turn else 1} if board.is_checkmate() else {'cp':0}
        return {'current':{'depth':99,'lines':[{**value,'moves':[]}]},'terminal':True,'elapsed_seconds':0.0,'nodes_requested':0}
    count=1 if root_moves is not None else min(2,board.legal_moves.count())
    pending=[];complete=[]
    limit=chess.engine.Limit(nodes=300000,time=remaining)
    with engine.analysis(board,limit,multipv=count,game=session,root_moves=root_moves) as stream:
        for info in stream:
            if not all(k in info for k in ['score','pv','depth']) or not info['pv'] or info.get('upperbound') or info.get('lowerbound'):continue
            rank=info.get('multipv',1)
            if rank!=len(pending)+1:pending=[]
            if rank!=len(pending)+1:continue
            assert info['pv'][0] in board.legal_moves
            if root_moves is not None:assert info['pv'][0] in root_moves
            pending.append(info)
            if rank==count:
                if len({x['depth'] for x in pending})==1 and len({x['pv'][0] for x in pending})==count:
                    snapshot={'depth':pending[0]['depth'],'lines':[pack_line(x) for x in pending],'reported_nodes':pending[-1].get('nodes')}
                    if not complete or snapshot['depth']>complete[-1]['depth']:complete.append(snapshot);complete=complete[-2:]
                    else:complete[-1]=snapshot
                pending=[]
    elapsed=time.monotonic()-begin
    return {'current':complete[-1] if complete else None,'previous':complete[-2] if len(complete)>1 else None,
        'terminal':False,'elapsed_seconds':elapsed,'nodes_requested':300000,'root_moves_uci':[m.uci() for m in root_moves] if root_moves is not None else None,
        'complete_same_depth_snapshot':bool(complete),'time_limit_seconds':remaining}
def attach_lines(snapshot,board,case,accepted_square=None):
    if not snapshot:return None
    return {**snapshot,'lines':[{**line,'moves':line['moves'][:20],**score_fields(line,case['mover']=='white'),
        'physical_PV':physical_line(board,line['moves'],case['mover']=='white',case['raw_material_before'],accepted_square)} for line in snapshot['lines']]}

assert digest(ENGINE)==EXPECTED_ENGINE
prepared=json.loads((ROOT/'branch-input.json').read_text())
assert len(prepared['cases'])==20
assert not (ROOT/'acceptance-results.json').exists(), 'No automatic retry or overwrite authorized'
result={'scope':'Matched20 development diagnostic; labels never passed to branch scoring. Conditional engine lines are not forced-acceptance or exhaustive-game proofs.',
    'started_at':now(),'status':'running','input_sha256':digest(ROOT/'branch-input.json'),'script_sha256':digest(pathlib.Path(__file__)),
    'preparation_script_sha256':digest(ROOT/'prepare.mts'),'engine_path':str(ENGINE),'engine_sha256':EXPECTED_ENGINE,
    'options':{'Threads':1,'Hash':64,'requested_nodes':300000,'accepted_MultiPV':2,'restricted_before_MultiPV':1,'PV_export_max_plies':20},
    'limits':{'maximum_engine_positions':80,'maximum_recorded_search_seconds':60,'maximum_acceptances_per_case':3},
    'session_policy':'Full standard PGN move stack, including original target and acceptance; Clear Hash once per case. All branch searches share that case session; cases use distinct sessions.',
    'baseline_cache':'Saved300knode before/after snapshots, not new searches; separate session/search history. No numeric score mixing inside an eligibility window.',
    'engine_positions':0,'recorded_search_seconds':0.0,'cases':[]}
conn=sqlite3.connect(f'file:{FINAL / "corpus.sqlite3"}?mode=ro',uri=True)
engine=chess.engine.SimpleEngine.popen_uci(str(ENGINE))
engine.configure({'Threads':1,'Hash':64})
result['engine_id']=engine.id
save(result)
try:
    for case in prepared['cases']:
        required=len(case['selected_acceptances'])+bool(case['nonoffering_legal_roots'])
        if result['engine_positions']+required>80 or result['recorded_search_seconds']>=60:
            result['status']='bounded_stop_before_case';result['unstarted_case']=case['key'];break
        pgn,pgn_hash=conn.execute('select pgn,pgn_sha256 from games where game_id=?',(case['game_id'],)).fetchone()
        assert hashlib.sha256(pgn.encode()).hexdigest()==pgn_hash==case['pgn_sha256']
        game=chess.pgn.read_game(io.StringIO(pgn));assert game and not game.errors
        board=game.board();before=None
        for ply,move in enumerate(game.mainline_moves(),1):
            if ply==case['ply']:
                before=board.copy(stack=True);assert before.fen()==case['fen_before'] and before.san(move)==case['san'] and move.uci()==case['uci']
            board.push(move)
            if ply==case['ply']:break
        assert before is not None and board.fen()==case['fen_after']
        entry={k:v for k,v in case.items() if k not in ['baseline_before','baseline_after']}
        entry['full_history_before']={'starting_fen':game.board().fen(),'uci':[m.uci() for m in before.move_stack],'pgn_sha256':pgn_hash}
        entry['baseline_before']={k:attach_lines(case['baseline_before'].get(k),before,case) for k in ['current','previous']}
        entry['baseline_after']={k:attach_lines(case['baseline_after'].get(k),board,case) for k in ['current','previous']}
        entry['accepted_branches']=[]
        engine.configure({'Clear Hash':None});session=object()
        for acceptance in case['selected_acceptances']:
            if result['recorded_search_seconds']>=60:break
            move=chess.Move.from_uci(acceptance['uci']);assert move in board.legal_moves
            child=board.copy(stack=True);san=child.san(move);child.push(move);assert child.fen()==acceptance['fen']
            evidence=search(engine,child,session,None,60-result['recorded_search_seconds'])
            result['recorded_search_seconds']+=evidence['elapsed_seconds'];result['engine_positions']+=1
            acceptance_data={**acceptance,'san':san,'full_history_uci':[m.uci() for m in child.move_stack],
                'evidence':{**evidence,'current':attach_lines(evidence.get('current'),child,case,move.to_square),'previous':attach_lines(evidence.get('previous'),child,case,move.to_square)}}
            entry['accepted_branches'].append(acceptance_data)
        entry['acceptance_search_coverage_complete']=len(entry['accepted_branches'])==case['qualifying_acceptances_total']
        if case['nonoffering_legal_roots'] and result['recorded_search_seconds']<60:
            roots=[chess.Move.from_uci(u) for u in case['nonoffering_legal_roots']];assert all(m in before.legal_moves for m in roots)
            evidence=search(engine,before,session,roots,60-result['recorded_search_seconds'])
            result['recorded_search_seconds']+=evidence['elapsed_seconds'];result['engine_positions']+=1
            entry['best_nonoffering_escape']={**evidence,'current':attach_lines(evidence.get('current'),before,case),'previous':attach_lines(evidence.get('previous'),before,case)}
        else:
            entry['best_nonoffering_escape']={'status':'no_nonoffering_legal_root' if not case['nonoffering_legal_roots'] else 'unknown_search_time_cap'}
        result['cases'].append(entry);save(result)
    else:result['status']='complete'
except Exception as error:
    result['status']='failed_no_retry';result['error']=str(error);raise
finally:
    engine.quit();conn.close();result['completed_at']=now();save(result)
print(json.dumps({'status':result['status'],'cases':len(result['cases']),'engine_positions':result['engine_positions'],'recorded_search_seconds':result['recorded_search_seconds'],'output':str(ROOT/'acceptance-results.json')}))
