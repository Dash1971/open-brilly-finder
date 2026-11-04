"""One capped counterfactual-acceptance probe on frozen matched cases."""
import ast,hashlib,io,json,signal,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1]
START=time.monotonic();SEARCH_SPENT=0.;ACTIVE_SEARCH=None
VALUES={1:90,2:300,3:300,4:500,5:1000,6:0}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def guard():
    if time.monotonic()-START>=300:raise TimeoutError('300-second study cap; no automatic retry')
def timed_out(*_):raise TimeoutError('300-second study cap; no automatic retry')
def material(b,color):return sum(VALUES[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
def terminal(b):return b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material()
def score(line,color):
    sign=1 if color else -1
    return {'cp':sign*line['cp'] if line.get('cp') is not None else None,
            'mate':sign*line['mate'] if line.get('mate') is not None else None}
def trace(before,after,accept,line):
    b=after.copy(stack=True);base=material(before,before.turn);steps=[];recoup=None
    for ply,u in enumerate([accept]+line.get('moves',[])[:11],1):
        m=chess.Move.from_uci(u);assert m in b.legal_moves
        own=b.turn==before.turn;previous_debt=base-material(b,before.turn)
        detail={'ply':ply,'uci':u,'san':b.san(m),'own_move':own,'capture':b.is_capture(m),'check':b.gives_check(m),'promotion':bool(m.promotion)}
        b.push(m);debt=base-material(b,before.turn)
        if own and previous_debt>0 and debt<=0 and recoup is None:recoup=ply
        detail['material_debt']=debt;steps.append(detail)
        if terminal(b):break
    return {'steps':steps,'first_recoup_ply':recoup,'terminal':terminal(b),'checkmate':b.is_checkmate(),
            'stalemate':b.is_stalemate(),'debt6':steps[min(6,len(steps))-1]['material_debt'] if len(steps)>=6 or terminal(b) else None,
            'debt12':steps[-1]['material_debt'] if len(steps)>=12 or terminal(b) else None,
            'own_checks_first6':sum(s['own_move'] and s['check'] for s in steps[:6]),
            'first_reply_quiet':not any(steps[1][k] for k in ['capture','check','promotion']) if len(steps)>1 else None}

def main():
    protocol=json.loads((HERE/'PROTOCOL.json').read_text());plan=protocol['new_search_plan']
    assert sha(HERE/'MATCHED-CASES.json')==protocol['cases_sha256'] and sha(HERE/'MATCHED-GAMES.json')==protocol['games_sha256']
    engine_path=Path('/opt/homebrew/bin/stockfish');assert sha(engine_path)==plan['engine_sha256']
    assert not (HERE/'PROBES.json').exists()
    # Reuse the exact complete-same-depth MultiPV collector, without running its
    # historical job/approval wrapper or mutating any previous study files.
    source=WORK/'research/brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
    parsed=ast.parse(source.read_text())
    funcs=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in ['packed','search']]
    assert len(funcs)==2
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(source),'exec'),globals())
    cases=json.loads((HERE/'MATCHED-CASES.json').read_text());games={g['pgn_key']:g for g in json.loads((HERE/'MATCHED-GAMES.json').read_text())}
    assert len(cases)==48 and sum(len(c['offers']) for c in cases)==62
    result={'status':'running','scope':'Exploratory conditional lines; not a trained classifier or validation set',
            'protocol_sha256':sha(HERE/'PROTOCOL.json'),'script_sha256':sha(Path(__file__)),
            'collector_sha256':sha(source),'engine_sha256':sha(engine_path),'searches':0,'cases':[]}
    write('PROBES.json',result)
    engine=chess.engine.SimpleEngine.popen_uci(str(engine_path),timeout=10)
    engine.configure({'Threads':1,'Hash':64});result['engine_id']=engine.id
    try:
        for c in cases:
            guard();g=games[c['pgn_key']]
            assert hashlib.sha256(g['pgn'].encode()).hexdigest()==c['pgn_sha256']
            game=chess.pgn.read_game(io.StringIO(g['pgn']));assert game and not game.errors
            after=game.board();before=None;target=int(c['key'].rsplit(':',1)[1])
            for ply,m in enumerate(game.mainline_moves(),1):
                if ply==target:before=after.copy(stack=True)
                after.push(m)
                if ply==target:break
            assert before.fen()==c['fen_before'] and after.fen()==c['fen_after']
            offers=[]
            for o in c['offers']:
                guard();accepted=after.copy(stack=True);accepted.push_uci(o['uci'])
                engine.configure({'Clear Hash':None})
                snapshot=search(engine,accepted,300000,object());result['searches']+=1
                lines=snapshot['current']['lines'];best=score(lines[0],before.turn)
                alt=score(lines[1],before.turn) if len(lines)>1 else {'cp':None,'mate':None}
                saved=c['current_features']['after_cp']
                offers.append({'offer':o,'accepted_fen':accepted.fen(),'snapshot':snapshot,'value_mover':best,
                  'gain_vs_saved_best_defense_cp':best['cp']-saved if best['cp'] is not None and saved is not None else None,
                  'best_second_response_gap_cp':best['cp']-alt['cp'] if best['cp'] is not None and alt['cp'] is not None else None,
                  'best_trace':trace(before,after,o['uci'],lines[0]),
                  'second_trace':trace(before,after,o['uci'],lines[1]) if len(lines)>1 else None,
                  'was_in_saved_top2':any(l['uci'] and l['uci'][0]==o['uci'] for l in c['saved_lines'])})
            result['cases'].append({'key':c['key'],'truth':c['truth'],'san':c['san'],'offers':offers})
            write('PROBES.json',result)
            if len(result['cases'])%8==0:print(json.dumps({'cases':len(result['cases']),'searches':result['searches'],'elapsed_seconds':round(time.monotonic()-START,1)}),flush=True)
        result['status']='complete'
    except Exception as e:
        result.update(status='incomplete',reason=repr(e),no_automatic_retry=True)
        raise
    finally:
        signal.alarm(0)
        engine.quit()
        result.update(elapsed_seconds=time.monotonic()-START,recorded_search_seconds=SEARCH_SPENT)
        write('PROBES.json',result)
    print(json.dumps({'status':result['status'],'cases':len(result['cases']),'searches':result['searches'],'elapsed_seconds':result['elapsed_seconds']}),flush=True)

if __name__=='__main__':
    signal.signal(signal.SIGALRM,timed_out);signal.alarm(300)
    main()
