"""One frozen 96-search diagnostic; no ratings, fitting, or application changes."""
import ast,hashlib,io,json,math,signal,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OLD=ROOT/'research/brilliant-matched-sacrifices-2026-11-04'
START=time.monotonic();SEARCH_SPENT=0.;ACTIVE_SEARCH=None
ENGINE=Path('/opt/homebrew/bin/stockfish')
COLLECTOR=ROOT/'research/brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def guard():
    if time.monotonic()-START>=600:raise TimeoutError('600-second wall cap; no automatic retry')
def timeout(*_):raise TimeoutError('600-second wall cap; no automatic retry')
def val(line,color):
    s=1 if color else -1
    cp=line.get('cp');mate=line.get('mate');mapped=max(-1000,min(1000,s*cp)) if cp is not None else (1000 if s*mate>0 else -1000)
    return {'cp':s*cp if cp is not None else None,'mate':s*mate if mate is not None else None,'mapped':mapped,'winprob':100/(1+math.exp(-.00368208*mapped))}
def main():
    assert not (HERE/'DEPTH-RESULTS.json').exists(),'No retry/overwrite'
    cases=json.loads((OLD/'MATCHED-CASES.json').read_text());games={g['pgn_key']:g for g in json.loads((OLD/'MATCHED-GAMES.json').read_text())};pairs=json.loads((OLD/'PROTOCOL.json').read_text())['pairs']
    assert len(cases)==48 and len({c['key'] for c in cases})==48
    assert sha(ENGINE)=='ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
    # Validate full-history boards before launching any search. Metadata is not consumed.
    boards={}
    for c in cases:
        g=games[c['pgn_key']];assert hashlib.sha256(g['pgn'].encode()).hexdigest()==c['pgn_sha256']
        game=chess.pgn.read_game(io.StringIO(g['pgn']));assert game and not game.errors
        b=game.board();target=int(c['key'].rsplit(':',1)[1]);before=None
        for ply,m in enumerate(game.mainline_moves(),1):
            if ply==target:before=b.copy(stack=True);assert m.uci()==c['uci']
            b.push(m)
            if ply==target:break
        assert before.fen()==c['fen_before'] and b.fen()==c['fen_after'] and before.turn!=b.turn
        boards[c['key']]=(before,b)
    protocol={'scope':'Fixed matched48 diagnostic. No ratings consumed, classifier dependence or fitting, application changes, training or deployment. Local SF18 is not Chess.com review.',
      'cases_sha256':sha(OLD/'MATCHED-CASES.json'),'games_sha256':sha(OLD/'MATCHED-GAMES.json'),'collector_sha256':sha(COLLECTOR),'script_sha256':sha(__file__),'engine_sha256':sha(ENGINE),
      'nodes_per_search':3000000,'searches':96,'positions':'Full PGN history BEFORE and AFTER each target; cases in original fixed order. Clear Hash each search; fresh game object.',
      'threads':1,'hash_mb':64,'multipv':2,'wall_seconds':600,'auto_retry':False,'collection':'Exact packed/search AST functions; last complete same-depth top2, current and previous retained.',
      'score':'White raw scores normalized to target mover; mapped clamp cp +-1000, mate sign to +-1000; winprob=100/(1+exp(-0.00368208*mapped)).',
      'alternate':'Best BEFORE root excluding played; if played absent from top2, top1; unavailable with no distinct root. This is not a newly verified safe/material-preserving alternative.',
      'summaries':'Raw cp shifts >50, >100; mapped loss before-to-after and same-search root; rank and alternate; pair contrasts. Diagnostic quality flags loss>5pp and <-5pp cross-search; stable matched = both after shifts <=50cp, loss <=5pp and pair after gap<=100cp. Thresholds descriptive, not award rules.',
      'pairs':pairs,'validation':{'coverage48':True,'fen_and_history':True,'engine_hash':True,'mover_sign':True}}
    write('DEPTH-PROTOCOL.json',protocol)
    funcs=[n for n in ast.parse(COLLECTOR.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('packed','search')];assert len(funcs)==2
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(COLLECTOR),'exec'),globals())
    result={'status':'running','protocol_sha256':sha(HERE/'DEPTH-PROTOCOL.json'),'searches':0,'cases':[]}
    write('DEPTH-RESULTS.json',result);engine=chess.engine.SimpleEngine.popen_uci(str(ENGINE),timeout=10);engine.configure({'Threads':1,'Hash':64});result['engine_id']=engine.id
    try:
        for c in cases:
            guard();before,after=boards[c['key']];snap={}
            for name,board in [('before',before),('after',after)]:
                engine.configure({'Clear Hash':None});snap[name]=search(engine,board,3000000,object());result['searches']+=1
            lines=snap['before']['current']['lines'];a=val(snap['after']['current']['lines'][0],before.turn);b=val(lines[0],before.turn)
            rank=next((i for i,l in enumerate(lines,1) if l['moves'] and l['moves'][0]==c['uci']),None)
            alt=next((l for l in lines if l['moves'] and l['moves'][0]!=c['uci']),None)
            altv=val(alt,before.turn) if alt else None
            old=c['current_features'];summary={'before':b,'after':a,'played_rank_top2':rank,'rank_saved':old['same_root_rank'],'alternate':altv,'alternate_uci':alt['moves'][0] if alt else None,
              'loss_pp':b['winprob']-a['winprob'],'saved_loss_pp':old['mapped_loss_pp'],
              'same_root_loss_pp':b['winprob']-val(lines[rank-1],before.turn)['winprob'] if rank else None,
              'before_shift_cp':b['cp']-old['best_cp'] if b['cp'] is not None and old['best_cp'] is not None else None,
              'after_shift_cp':a['cp']-old['after_cp'] if a['cp'] is not None and old['after_cp'] is not None else None,
              'saved_after_cp':old['after_cp'],'saved_before_cp':old['best_cp'],
              'alternate_gap_pp':b['winprob']-altv['winprob'] if altv else None,
              'before_depth':snap['before']['current']['depth'],'after_depth':snap['after']['current']['depth']}
            summary['quality_flags']=[name for name,yes in [('loss_gt5pp',summary['loss_pp']>5),('cross_search_increase_gt5pp',summary['loss_pp']< -5),('played_not_top2',rank is None),('mate_transition',any(x['mate'] is not None for x in (a,b))) ] if yes]
            result['cases'].append({'key':c['key'],'truth':c['truth'],'san':c['san'],'uci':c['uci'],'mover':'white' if before.turn else 'black','snapshots':snap,'summary':summary});write('DEPTH-RESULTS.json',result)
            if len(result['cases'])%4==0:print(json.dumps({'cases':len(result['cases']),'searches':result['searches'],'elapsed_seconds':round(time.monotonic()-START,1)}),flush=True)
        result['status']='complete'
    except Exception as e:
        result.update(status='incomplete',reason=repr(e),no_automatic_retry=True)
        raise
    finally:
        signal.alarm(0);engine.quit();result.update(elapsed_seconds=time.monotonic()-START,search_seconds=SEARCH_SPENT);write('DEPTH-RESULTS.json',result)
    summaries={c['key']:c['summary'] for c in result['cases']};contrasts=[]
    for p in pairs:
        pos=summaries[p['positive']];neg=summaries[p['ordinary']]
        gap=pos['after']['cp']-neg['after']['cp'] if pos['after']['cp'] is not None and neg['after']['cp'] is not None else None
        stable=all(s['after_shift_cp'] is not None and abs(s['after_shift_cp'])<=50 and s['loss_pp']<=5 for s in (pos,neg)) and gap is not None and abs(gap)<=100
        contrasts.append({**p,'after_cp_gap_positive_minus_ordinary':gap,'loss_pp_positive_minus_ordinary':pos['loss_pp']-neg['loss_pp'],'positive_rank':pos['played_rank_top2'],'ordinary_rank':neg['played_rank_top2'],'stable_matched_descriptive':stable})
    result['pair_contrasts']=contrasts;result['counts']={}
    for label,subset in [('all',result['cases']),('Brilliant',[c for c in result['cases'] if c['truth']]),('ordinary',[c for c in result['cases'] if not c['truth']])]:
        result['counts'][label]={'n':len(subset),**{f'{stage}_shift_gt{threshold}cp':sum(c['summary'][f'{stage}_shift_cp'] is not None and abs(c['summary'][f'{stage}_shift_cp'])>threshold for c in subset) for stage in ('before','after') for threshold in (50,100)},'loss_gt5pp':sum(c['summary']['loss_pp']>5 for c in subset),'cross_search_increase_gt5pp':sum(c['summary']['loss_pp']< -5 for c in subset),'played_not_top2':sum(c['summary']['played_rank_top2'] is None for c in subset),'played_top1':sum(c['summary']['played_rank_top2']==1 for c in subset),'played_top2':sum(c['summary']['played_rank_top2']==2 for c in subset)}
    write('DEPTH-RESULTS.json',result)
    report=['Completed frozen96searches:48cases, before/after at3Mnodes; one thread, Hash64, MultiPV2, full history, fresh hash.',f'Elapsed {result["elapsed_seconds"]:.1f}s; no retries.','Local Stockfish18 diagnostic; not Chess.com review settings or a reproduction of its awards. No ratings or classifiers used.','Raw snapshots retained. Cp shifts compare saved300k searches to new3M search; search noise and deeper horizons both contribute.','Counts:',json.dumps(result['counts'],indent=2),'Stable matched under frozen descriptive criterion: '+str([p['pair'] for p in contrasts if p['stable_matched_descriptive']]),'Pair contrasts:',json.dumps(contrasts,indent=2),'Quality notes: cross-position loss can be negative due to independently searched positions. Same-search root loss and top2 rank help distinguish this; absence from top2 gives no exact played-root evaluation. Alternate is best other root, not a verified safe alternative. No award/classification threshold is inferred.']
    (HERE/'DEPTH-REPORT.txt').write_text('\n'.join(report)+'\n');print(json.dumps({'status':result['status'],'counts':result['counts'],'stable_pairs':[p['pair'] for p in contrasts if p['stable_matched_descriptive']],'elapsed_seconds':result['elapsed_seconds']}),flush=True)
if __name__=='__main__':
    signal.signal(signal.SIGALRM,timeout);signal.alarm(600);main()
