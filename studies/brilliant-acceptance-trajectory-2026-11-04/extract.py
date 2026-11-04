"""Saved-line-only trajectory extraction; no engine, ratings, or label use."""
import collections,gzip,hashlib,io,json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.pgn
HERE=Path(__file__).resolve().parent; WORK=HERE.parents[1]
STUDY=WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
GAP=WORK/'research/brilliant-conditional-gap-2026-11-04'
PILOT=WORK/'research/brilliant-matched-sacrifices-2026-11-04'
NAMES=['material_debt6_cp','material_debt12_cp','recovered_by12','first_recovery_ply','acceptance_mate_outcome','terminal_draw_by12','initial_debt_cp']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def empty():return dict.fromkeys(NAMES)
def rank(line,sign):
    if line.get('mate') is not None:
        m=sign*line['mate'];return (0,abs(m)) if m<=0 else (2,-m)
    return (1,sign*line['cp'])
def material(b,mover):
    return sum(v*(len(b.pieces(p,mover))-len(b.pieces(p,not mover))) for p,v in [(1,90),(2,300),(3,300),(4,500),(5,1000)])
def trajectory(before,after,offer,which):
    snap=offer['snapshot'][which];line=snap['lines'][0];mover=before.turn;baseline=material(before,mover)
    b=after.copy(stack=True);steps=[];terminal=None
    moves=[offer['uci']]+line['moves']
    for ply,u in enumerate(moves,1):
        # Full saved PV is legality checked even after the extraction horizon.
        move=chess.Move.from_uci(u);assert move in b.legal_moves,(ply,u,b.fen())
        own=b.turn==mover;san=b.san(move);b.push(move)
        outcome=b.outcome(claim_draw=False)
        if ply<=12 and terminal is None:
            steps.append({'ply':ply,'uci':u,'san':san,'own_move':own,'material_debt':baseline-material(b,mover),'fen':b.fen(),'history_sha256':digest(' '.join(m.uci() for m in b.move_stack))})
            if outcome:terminal={'ply':ply,'termination':outcome.termination.name,'winner':None if outcome.winner is None else ('white' if outcome.winner else 'black')}
    debts={s['ply']:s['material_debt'] for s in steps};initial=debts[1]
    full=12 in debts or terminal is not None
    def debt(n):return debts.get(n,steps[-1]['material_debt'] if terminal and terminal['ply']<=n else None)
    recovery=next((s['ply'] for s in steps if s['own_move'] and s['material_debt']<=0),None) if initial>0 else None
    mate=line.get('mate');mate_outcome=(1 if (1 if mover else -1)*mate>0 else -1) if mate is not None else (0 if line.get('cp') is not None else None)
    draw=(int(terminal['winner'] is None) if terminal else (0 if 12 in debts else None))
    f=dict(zip(NAMES,[debt(6),debt(12),int(recovery is not None) if initial>0 and (recovery is not None or full) else None,recovery,mate_outcome,draw,initial]))
    d={'reason':'known','selected_acceptance':offer['uci'],'depth':snap['depth'],'saved_pv_plies':len(line['moves']),'observed_plies':len(steps),'terminal':terminal,'recovery_reason':'initial_debt_nonpositive' if initial<=0 else ('recovered' if recovery else ('no_recovery_through_horizon_or_terminal' if full else 'truncated_before12')),'steps':steps,'score':{k:line[k] for k in ['cp','mate'] if k in line}}
    return f,d

def main():
    started=time.monotonic();protocol=json.loads((HERE/'FEATURE-PROTOCOL.json').read_text())
    assert sha(HERE/'extract.py')==protocol['extract_script_sha256']
    for p,h in protocol['source_sha256'].items():assert sha(WORK/p)==h,p
    assert not (HERE/'TRAJECTORY-FEATURES.json').exists()
    cases=json.loads((STUDY/'data/training.json').read_text())['cases'];assert len(cases)==3724
    case_by={c['key']:c for c in cases};evidence={e['key']:e for e in map(json.loads,(GAP/'ENGINE-EVIDENCE.jsonl').read_text().splitlines())};assert len(evidence)==1320
    gap=json.loads((GAP/'GAP-FEATURES.json').read_text());assert set(gap)==set(case_by)
    source={}
    with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/after-snapshots.jsonl.gz','rt') as f:
        for l in f:
            c=json.loads(l)
            if c['key'] in evidence:source[c['key']]={k:c[k] for k in ['pgn_key','fen_before','fen_after','uci']}
    wanted={c['pgn_key'] for c in source.values()};games={}
    with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/games.jsonl.gz','rt') as f:
        for l in f:
            g=json.loads(l)
            if g['pgn_key'] in wanted:games[g['pgn_key']]=g
    bygame=collections.defaultdict(list)
    for key,c in source.items():bygame[c['pgn_key']].append(key)
    features={k:{w:empty() for w in ['current','previous']} for k in case_by}
    diagnostics={k:{w:{'reason':'ineligible_both_windows_not_requested'} for w in ['current','previous']} for k in case_by}
    assertions=collections.Counter();pilot_checks=[]
    probes=json.loads((PILOT/'PROBES.json').read_text());assert len(probes['cases'])==48
    pilot={c['key']:c for c in probes['cases']}
    for pg,keys in sorted(bygame.items()):
        g=games[pg];assert digest(g['pgn'])==g['pgn_sha256'];game=chess.pgn.read_game(io.StringIO(g['pgn']));assert game and not game.errors
        positions={int(k.rsplit(':',1)[1])+d for k in keys for d in [-1,0]};b=game.board();boards={0:b.copy(stack=True)}
        for ply,m in enumerate(game.mainline_moves(),1):
            assert m in b.legal_moves;b.push(m)
            if ply in positions:boards[ply]=b.copy(stack=True)
        for key in sorted(keys):
            c=case_by[key];e=evidence[key];ply=int(key.rsplit(':',1)[1]);before,after=boards[ply-1],boards[ply]
            assert e['pgn_sha256']==g['pgn_sha256'];assert before.fen()==c['fen_before']==source[key]['fen_before'];assert after.fen()==c['fen_after']==source[key]['fen_after'];assert after.peek().uci()==c['uci']==source[key]['uci'];assertions['source_positions']+=1
            for w in ['current','previous']:
                old=gap[key][w];offers=e['offers']
                if not offers or any(not o['snapshot'].get(w) for o in offers):
                    reason=old['reason'];assert reason in ['no_qualifying_offer','offer_mapping_unknown','missing_complete_window'];diagnostics[key][w]={'reason':reason};continue
                selected=min(offers,key=lambda o:(rank(o['snapshot'][w]['lines'][0],1 if before.turn else -1),o['uci']))
                assert selected['uci']==old['selected_acceptance'];assert selected['snapshot'][w]['depth']==old['depth'];assertions['exact_gap_selection']+=1
                accepted=after.copy(stack=True);accepted.push_uci(selected['uci']);assert accepted.fen()==selected['accepted_fen']
                f,d=trajectory(before,after,selected,w);features[key][w]=f;diagnostics[key][w]=d;assertions['legal_full_saved_pv']+=1
                if key in pilot and w=='current':
                    po=next(o for o in pilot[key]['offers'] if o['offer']['uci']==selected['uci']);assert po['snapshot']==selected['snapshot']
                    oldsteps=po['best_trace']['steps'];newsteps=d['steps'];compared=min(len(oldsteps),len(newsteps))
                    for a,z in zip(oldsteps,newsteps):
                        for field in ['ply','uci','san','own_move','material_debt']:assert a[field]==z[field],(key,field)
                    pilot_checks.append({'key':key,'selected_acceptance':selected['uci'],'compared_plies':compared,'prior_debt6':po['best_trace']['debt6'],'new_debt6':f['material_debt6_cp'],'prior_debt12':po['best_trace']['debt12'],'new_debt12':f['material_debt12_cp']})
    write('TRAJECTORY-FEATURES.json',features)
    coverage={w:{n:sum(features[k][w][n] is not None for k in features) for n in NAMES} for w in ['current','previous']}
    checks={'status':'passed','assertions':dict(assertions),'pilot_cases':len(pilot),'pilot_selected_current_comparisons':pilot_checks,'missingness_examples':{},'terminal_examples':{}}
    for w in ['current','previous']:
        for k,ds in diagnostics.items():
            d=ds[w];f=features[k][w]
            for reason in [d['reason'],d.get('recovery_reason')]:
                if reason and reason not in checks['missingness_examples']:checks['missingness_examples'][reason]={'key':k,'window':w,'features':f,'observed_plies':d.get('observed_plies')}
            if d.get('terminal'):
                term=d['terminal']['termination'];checks['terminal_examples'].setdefault(term,{'key':k,'window':w,'terminal':d['terminal'],'features':f})
    write('FEATURE-CHECKS.json',checks)
    write('EXTRACTION.json',{'status':'complete','scope':'saved acceptance lines only; no searches; ratings and labels unused','protocol_sha256':sha(HERE/'FEATURE-PROTOCOL.json'),'feature_sha256':sha(HERE/'TRAJECTORY-FEATURES.json'),'checks_sha256':sha(HERE/'FEATURE-CHECKS.json'),'cases':len(cases),'evidence_cases':len(evidence),'offers':sum(len(e['offers']) for e in evidence.values()),'coverage':coverage,'window_reasons':{w:dict(collections.Counter(d[w]['reason'] for d in diagnostics.values())) for w in ['current','previous']},'terminal_counts':{w:dict(collections.Counter(d[w]['terminal']['termination'] for d in diagnostics.values() if d[w].get('terminal'))) for w in ['current','previous']},'elapsed_seconds':time.monotonic()-started,'diagnostics':diagnostics})
    print(json.dumps({'status':'complete','coverage':coverage,'checks':dict(assertions),'pilot_comparisons':len(pilot_checks)}))
if __name__=='__main__':main()
