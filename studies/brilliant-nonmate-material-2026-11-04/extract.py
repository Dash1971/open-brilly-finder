"""Frozen saved-PV-only material alternative extraction; no engines or labels."""
import collections, datetime, gzip, hashlib, io, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess, chess.pgn
HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
STUDY = WORK / 'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
GAP = WORK / 'research/brilliant-conditional-gap-2026-11-04/ENGINE-EVIDENCE.jsonl'
WINDOWS = ['current', 'previous']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def write(name, value): (HERE/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
def material(b, mover):
    return sum(v*(len(b.pieces(p,mover))-len(b.pieces(p,not mover))) for p,v in [(1,90),(2,300),(3,300),(4,500),(5,1000)])
def line_trace(accepted, line, mover, baseline):
    b=accepted.copy(stack=True); steps=[]; terminal=None; checkmate=False
    for ply,u in enumerate(line.get('moves',[]),2):
        m=chess.Move.from_uci(u); assert m in b.legal_moves, (ply,u,b.fen())
        san=b.san(m); b.push(m); outcome=b.outcome(claim_draw=False)
        if outcome and terminal is None: terminal={'ply':ply,'termination':outcome.termination.name,'winner':outcome.winner}
        checkmate = checkmate or b.is_checkmate()
        if ply<=12: steps.append({'ply':ply,'uci':u,'san':san,'gain_cp':material(b,mover)-baseline,'fen':b.fen(),'history_sha256':digest(' '.join(m.uci() for m in b.move_stack))})
    favorable = line.get('mate') is None and isinstance(line.get('cp'),(int,float)) and (1 if mover else -1)*line['cp']>0
    gain12=next((s['gain_cp'] for s in steps if s['ply']==12),None)
    if not favorable: state=0; reason='not_finite_favorable'
    elif checkmate: state=0; reason='observed_checkmate_excluded'
    elif terminal and terminal['winner'] is None: state=0; reason='automatic_terminal_draw'
    elif gain12 is None: state=None; reason='finite_favorable_truncated_before12'
    else: state=int(gain12>=300); reason='material_win_at12' if state else 'no_material_win_at12'
    return {'state':state,'reason':reason,'score':{k:line[k] for k in ['cp','mate'] if k in line},'saved_pv_plies':len(line.get('moves',[])),'gain12_cp':gain12,'terminal':terminal,'steps':steps}
def extract_case(before, after, offers, checks=None):
    checks = checks if checks is not None else collections.Counter()
    mover=before.turn
    mating=[]
    for offer in offers:
        a=after.copy(stack=True); m=chess.Move.from_uci(offer['uci']); assert m in a.legal_moves and a.is_capture(m); a.push(m); assert a.fen()==offer['accepted_fen']
        witnesses=[]
        for response in list(a.legal_moves):
            a.push(response)
            if a.is_checkmate(): witnesses.append(response.uci())
            a.pop()
        if witnesses: mating.append((offer,a,witnesses))
    result={}; details={}
    for w in WINDOWS:
        d={'reason':'not_applicable','captures':[]}; states=[]
        for offer,a,witnesses in mating:
            snap=offer['snapshot'].get(w); legalcount=a.legal_moves.count(); cd={'acceptance':offer['uci'],'mate_in_one_witnesses':witnesses,'legal_response_count':legalcount,'lines':[]}
            if not snap: cd['reason']='missing_complete_window'; states.append(None)
            else:
                roots=[line['moves'][0] for line in snap['lines'] if line.get('moves')]; assert len(roots)==len(set(roots))
                if len(roots)<min(2,legalcount): cd['reason']='missing_complete_window'; states.append(None)
                else: cd['reason']='saved_multipv_complete'; cd['depth']=snap['depth']
                for line in snap['lines']:
                    trace=line_trace(a,line,mover,material(before,mover)); cd['lines'].append(trace); states.append(trace['state']); checks['legal_full_saved_pvs']+=1
            d['captures'].append(cd)
        value=1 if 1 in states else (None if None in states or not mating else 0)
        d['reason']='not_applicable' if not mating else ('material_win_witness' if value==1 else ('unknown_coverage' if value is None else 'no_saved_material_win_witness'))
        result[w]={'nonmate_material_win':value}; details[w]=d
    return result,details

def main():
    protocol=json.loads((HERE/'FEATURE-PROTOCOL.json').read_text())
    assert sha(HERE/'extract.py')==protocol['extract_script_sha256']
    for p,h in protocol['source_sha256'].items(): assert sha(WORK/p)==h,p
    assert not (HERE/'FEATURES.json').exists()
    # Only case identifiers and source positions are accessed; label fields are never accessed.
    cases=json.loads((STUDY/'data/training.json').read_text())['cases']; assert len(cases)==3724
    keys={c['key'] for c in cases}; evidence={e['key']:e for e in map(json.loads,GAP.read_text().splitlines())}
    source={}
    with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/after-snapshots.jsonl.gz','rt') as f:
        for line in f:
            s=json.loads(line)
            if s['key'] in evidence: source[s['key']]={k:s[k] for k in ['pgn_key','fen_before','fen_after','uci']}
    wanted={s['pgn_key'] for s in source.values()}; games={}
    with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/games.jsonl.gz','rt') as f:
        for line in f:
            g=json.loads(line)
            if g['pgn_key'] in wanted: games[g['pgn_key']]=g
    bygame=collections.defaultdict(list)
    for k,s in source.items(): bygame[s['pgn_key']].append(k)
    features={k:{w:{'nonmate_material_win':None} for w in WINDOWS} for k in keys}
    diagnostics={k:{w:{'reason':'no_saved_offer_evidence','captures':[]} for w in WINDOWS} for k in keys}
    checks=collections.Counter()
    for pg,ks in sorted(bygame.items()):
        g=games[pg]; assert digest(g['pgn'])==g['pgn_sha256']
        game=chess.pgn.read_game(io.StringIO(g['pgn'])); assert game and not game.errors
        wantedply={int(k.rsplit(':',1)[1])+d for k in ks for d in [-1,0]}; b=game.board(); boards={0:b.copy(stack=True)}
        for ply,m in enumerate(game.mainline_moves(),1):
            assert m in b.legal_moves; b.push(m)
            if ply in wantedply: boards[ply]=b.copy(stack=True)
        for k in sorted(ks):
            p=int(k.rsplit(':',1)[1]); before,after=boards[p-1],boards[p]; s=source[k]; e=evidence[k]; mover=before.turn
            assert before.fen()==s['fen_before'] and after.fen()==s['fen_after'] and after.peek().uci()==s['uci']; assert e['pgn_sha256']==g['pgn_sha256']; checks['source_positions']+=1
            result,details=extract_case(before,after,e['offers'],checks)
            features[k]=result; diagnostics[k]=details
    coverage={w:dict(collections.Counter(str(features[k][w]['nonmate_material_win']) for k in keys)) for w in WINDOWS}
    reasons={w:dict(collections.Counter(d[w]['reason'] for d in diagnostics.values())) for w in WINDOWS}
    write('FEATURES.json',features)
    write('CHECKS.json',{'status':'passed','assertions':dict(checks),'coverage':coverage,'reasons':reasons,'scope':'No labels, ratings, prediction files, or model outcomes accessed. Full saved PV legality checked; actual original PGN history retained.'})
    hitkeys=['172291845278:66','184710314858:52','185214494356:53','169962611516:55','171270665964:60','185741429132:55','173266974169:84','167735024286:72','184069349690:45']
    write('HIT-TRACES.json',{k:{'features':features[k],'traces':diagnostics[k]} for k in hitkeys})
    write('EXTRACTION.json',{'status':'complete','protocol_sha256':sha(HERE/'FEATURE-PROTOCOL.json'),'feature_sha256':sha(HERE/'FEATURES.json'),'checks_sha256':sha(HERE/'CHECKS.json'),'hit_traces_sha256':sha(HERE/'HIT-TRACES.json'),'cases':len(keys),'evidence_cases':len(evidence),'coverage':coverage,'reasons':reasons,'diagnostics':diagnostics})
    print(json.dumps({'status':'complete','coverage':coverage,'reasons':reasons,'checks':dict(checks)}))
if __name__=='__main__': main()
