"""Bounded, label-independent conditional gap extraction for one study."""
import ast,collections,gzip,hashlib,importlib.util,io,json,signal,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1]
STUDY=WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
PILOT=WORK/'research/brilliant-matched-sacrifices-2026-11-04'
START=time.monotonic();SEARCH_SPENT=0.;ACTIVE_SEARCH=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def guard():
    if time.monotonic()-START>=900:raise TimeoutError('900-second extraction cap; no automatic retry')
def timeout(*_):raise TimeoutError('900-second extraction cap; no automatic retry')
def rank(line,sign):
    if line.get('mate') is not None:
        m=sign*line['mate']
        return (0,abs(m)) if m<=0 else (2,-m)
    return (1,sign*line['cp'])
def gap_for_window(offers,which,sign):
    if not offers:return {'gap_cp':None,'reason':'no_qualifying_offer'}
    if any(not o['snapshot'].get(which) for o in offers):return {'gap_cp':None,'reason':'missing_complete_window'}
    selected=min(offers,key=lambda o:(rank(o['snapshot'][which]['lines'][0],sign),o['uci']))
    snap=selected['snapshot'][which];lines=snap['lines']
    result={'selected_acceptance':selected['uci'],'depth':snap['depth']}
    if len(lines)<2:return {**result,'gap_cp':None,'reason':'fewer_than_two_responses'}
    if any(l.get('cp') is None for l in lines[:2]):return {**result,'gap_cp':None,'reason':'mate_score'}
    gap=sign*(lines[0]['cp']-lines[1]['cp'])
    assert gap>=0
    return {**result,'gap_cp':gap,'reason':'known'}

def main():
    protocol=json.loads((HERE/'PROTOCOL.json').read_text())
    assert not (HERE/'EXTRACTION.json').exists() and not (HERE/'GAP-FEATURES.json').exists()
    assert sha(HERE/'extract.py')==protocol['extract_script_sha256']
    for path,h in protocol['source_sha256'].items():assert sha(WORK/path)==h
    engine_path=Path('/opt/homebrew/bin/stockfish');assert sha(engine_path)==protocol['engine_sha256']
    data=json.loads((STUDY/'data/training.json').read_text());cases=data['cases']
    requested={c['key']:c for c in cases if any(w['eligible'] for w in c['windows'].values())}
    assert len(requested)==1320
    features={c['key']:{w:{'gap_cp':None,'reason':'ineligible_both_windows_not_requested'} for w in ['current','previous']} for c in cases}
    source=WORK/'research/brilliants-training-overnight-2026-11-03/adapter/augment-pv.py'
    spec=importlib.util.spec_from_file_location('saved_pv',source);pv=importlib.util.module_from_spec(spec);spec.loader.exec_module(pv)
    collector=WORK/'research/brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
    nodes=[n for n in ast.parse(collector.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['packed','search']]
    assert len(nodes)==2
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(collector),'exec'),globals())
    source_cases={}
    with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/after-snapshots.jsonl.gz','rt') as f:
        for line in f:
            c=json.loads(line)
            if c['key'] in requested:source_cases[c['key']]={k:c[k] for k in ['pgn_key','fen_before','fen_after','uci']}
    games={};wanted={c['pgn_key'] for c in source_cases.values()}
    with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/games.jsonl.gz','rt') as f:
        for line in f:
            g=json.loads(line)
            if g['pgn_key'] in wanted:games[g['pgn_key']]=g
    pilot_cases={c['key']:c for c in json.loads((PILOT/'MATCHED-CASES.json').read_text())}
    pilot_probes=json.loads((PILOT/'PROBES.json').read_text());assert pilot_probes['status']=='complete'
    cache={c['key']:c for c in pilot_probes['cases']}
    assert pilot_probes['engine_sha256']==protocol['engine_sha256']
    bygame=collections.defaultdict(list)
    for key,c in requested.items():bygame[source_cases[key]['pgn_key']].append(c)
    result={'status':'running','protocol_sha256':sha(HERE/'PROTOCOL.json'),'input_sha256':sha(STUDY/'data/training.json'),
       'engine_sha256':protocol['engine_sha256'],'requested_cases':len(requested),'completed_cases':0,'new_searches':0,'cached_searches':0,
       'offer_mapping_unknown':0,'coverage':{},'raw_evidence':'ENGINE-EVIDENCE.jsonl'}
    write('EXTRACTION.json',result)
    engine=chess.engine.SimpleEngine.popen_uci(str(engine_path),timeout=15);engine.configure({'Threads':1,'Hash':64})
    result['engine_id']=engine.id
    evidence=(HERE/'ENGINE-EVIDENCE.jsonl').open('x')
    try:
        for pgnkey,cc in sorted(bygame.items()):
            guard();g=games[pgnkey];assert hashlib.sha256(g['pgn'].encode()).hexdigest()==g['pgn_sha256']
            game=chess.pgn.read_game(io.StringIO(g['pgn']));assert game and not game.errors
            positions={n for c in cc for n in [int(c['key'].rsplit(':',1)[1])-1,int(c['key'].rsplit(':',1)[1])]}
            b=game.board();boards={0:b.copy(stack=True)}
            for ply,m in enumerate(game.mainline_moves(),1):
                b.push(m)
                if ply in positions:boards[ply]=b.copy(stack=True)
            for c in sorted(cc,key=lambda c:int(c['key'].rsplit(':',1)[1])):
                guard();key=c['key'];ply=int(key.rsplit(':',1)[1]);before,after=boards[ply-1],boards[ply]
                assert before.fen()==c['fen_before'] and after.fen()==c['fen_after'] and after.peek().uci()==c['uci']
                offers,unknown,nodes=pv.qualify(before,after)
                assert len(offers)<=4
                result['offer_mapping_unknown']+=int(unknown)
                found=[]
                if not unknown:
                    for u,offer in sorted(offers.items()):
                        accepted=after.copy(stack=True);accepted.push_uci(u)
                        if key in cache:
                            pc=pilot_cases[key];assert pc['pgn_sha256']==g['pgn_sha256'] and pc['fen_after']==after.fen()
                            cached=next(o for o in cache[key]['offers'] if o['offer']['uci']==u)
                            assert cached['accepted_fen']==accepted.fen()
                            snapshot=cached['snapshot'];result['cached_searches']+=1;origin='pilot_cache'
                        else:
                            engine.configure({'Clear Hash':None})
                            snapshot=search(engine,accepted,300000,object());result['new_searches']+=1;origin='new'
                        # Verify complete roots and full continuation legality before
                        # the branch can supply a training feature.
                        for which in ['current','previous']:
                            snap=snapshot.get(which)
                            if not snap:continue
                            roots=[]
                            for line in snap['lines']:
                                a=accepted.copy(stack=True)
                                for v in line['moves']:a.push_uci(v)
                                if line['moves']:roots.append(line['moves'][0])
                            assert len(roots)==len(set(roots))
                        found.append({'uci':u,'accepted_fen':accepted.fen(),'snapshot':snapshot,'source':origin})
                sign=1 if before.turn else -1
                features[key]={w:({'gap_cp':None,'reason':'offer_mapping_unknown'} if unknown else gap_for_window(found,w,sign)) for w in ['current','previous']}
                evidence.write(json.dumps({'key':key,'pgn_sha256':g['pgn_sha256'],'offers':found,'features':features[key]},allow_nan=False)+'\n')
                result['completed_cases']+=1
                if result['completed_cases']%100==0:
                    evidence.flush();result['elapsed_seconds']=time.monotonic()-START;write('EXTRACTION.json',result)
                    print(json.dumps({k:result[k] for k in ['completed_cases','new_searches','cached_searches','elapsed_seconds']}),flush=True)
        assert result['completed_cases']==1320 and result['new_searches']+result['cached_searches']==1481
        assert result['cached_searches']==62
        write('GAP-FEATURES.json',features)
        result.update(status='complete',feature_sha256=sha(HERE/'GAP-FEATURES.json'))
    except Exception as e:
        result.update(status='incomplete',reason=repr(e),no_automatic_retry=True)
        raise
    finally:
        signal.alarm(0);evidence.close();engine.quit()
        result['coverage']={w:dict(collections.Counter(features[k][w]['reason'] for k in requested)) for w in ['current','previous']}
        result.update(elapsed_seconds=time.monotonic()-START,recorded_new_search_seconds=SEARCH_SPENT,evidence_sha256=sha(HERE/'ENGINE-EVIDENCE.jsonl'))
        write('EXTRACTION.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    signal.signal(signal.SIGALRM,timeout);signal.alarm(900)
    main()
