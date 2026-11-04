"""Two prespecified first-response features from saved acceptance lines only."""
import hashlib,json,math,sys,time
from pathlib import Path
from collections import Counter
sys.dont_write_bytecode=True;sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
H=Path(__file__).resolve().parent;W=H.parents[1]
TRAIN=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
EVIDENCE=W/'research/brilliant-conditional-gap-2026-11-04/ENGINE-EVIDENCE.jsonl'
PRIOR=W/'research/brilliant-compensation-links-2026-11-04/COMPARISON.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):(H/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def rank(score):
    if score['kind']=='mate':return (0,abs(score['value'])) if score['value']<=0 else (2,-score['value'])
    return (1,score['value'])
def main():
    start=time.monotonic();p=json.loads((H/'EXTRACTION-PROTOCOL.json').read_text())
    assert not (H/'FEATURES.json').exists() and not (H/'EXTRACTION.json').exists()
    assert sha(Path(__file__))==p['script_sha256']
    assert all(sha(k)==v for k,v in p['input_sha256'].items())
    assert all(sha(k)==v for k,v in p['dependency_sha256'].items())
    cs=json.loads(TRAIN.read_text())['cases'];case={c['key']:c for c in cs}
    ev={}
    with EVIDENCE.open() as f:
        for line in f:
            e=json.loads(line);assert e['key'] not in ev;ev[e['key']]=e
    wanted={c['key'] for c in cs if any(w['eligible'] for w in c['windows'].values())}
    assert set(ev)==wanted and len(wanted)==1320
    features={};diagnostics={};counts=Counter();branches=0
    for c in cs:
        if time.monotonic()-start>180:raise TimeoutError('180second bound, no outcome-driven retries')
        k=c['key'];color=chess.Board(c['fen_before']).turn;sign=1 if color else -1
        features[k]={};diagnostics[k]={}
        for window in ('current','previous'):
            missing=dict(acceptor_fork=None,reply_check=None)
            if k not in ev:
                features[k][window]=missing;diagnostics[k][window]={'reason':'not_requested_both_windows_ineligible'};counts['not_requested_windows']+=1;continue
            e=ev[k];choices=[];unknown=None
            if not e['offers']:unknown='no_saved_qualifying_offer'
            for o in e['offers']:
                snap=o['snapshot'].get(window)
                if not snap or not snap.get('lines'):unknown='missing_complete_window';break
                l=snap['lines'][0]
                if not l.get('moves'):unknown='missing_first_reply';break
                raw={n:l[n] for n in ('cp','mate') if l.get(n) is not None}
                if len(raw)!=1 or not math.isfinite(next(iter(raw.values()))):unknown='missing_score';break
                kind=next(iter(raw));score={'kind':kind,'value':sign*raw[kind]}
                choices.append((rank(score),o['uci'],o,l,score))
            if unknown:
                features[k][window]=missing;diagnostics[k][window]={'reason':unknown};counts['unknown_windows']+=1;continue
            _,uci,o,l,score=min(choices,key=lambda x:(x[0],x[1]))
            after=chess.Board(c['fen_after']);acceptance=chess.Move.from_uci(uci)
            assert acceptance in after.legal_moves and after.is_capture(acceptance)
            victim=after.piece_at(acceptance.to_square);assert victim and victim.color==color and victim.piece_type not in (chess.PAWN,chess.KING)
            acceptor=after.piece_at(acceptance.from_square);assert acceptor and acceptor.color!=color
            after.push(acceptance);assert after.fen()==o['accepted_fen'] and after.turn==color
            reply=chess.Move.from_uci(l['moves'][0]);assert reply in after.legal_moves
            san=after.san(reply);check=after.gives_check(reply);after.push(reply)
            # Immediate reply: a surviving acceptor must still be on its acceptance square.
            targets=[]
            for square in sorted(after.attacks(reply.to_square)):
                piece=after.piece_at(square)
                if piece and piece.color!=color and piece.piece_type!=chess.PAWN:
                    targets.append(dict(square=chess.square_name(square),role=chess.piece_name(piece.piece_type),
                                        is_acceptor=square==acceptance.to_square))
            fork=len(targets)>=2 and any(t['is_acceptor'] for t in targets)
            features[k][window]=dict(acceptor_fork=bool(fork),reply_check=bool(check))
            diagnostics[k][window]=dict(reason='known',acceptance=uci,reply=reply.uci(),reply_san=san,score_mover=score,
                targets=targets,reply_piece_pinned=after.is_pinned(color,reply.to_square),
                semantics='Geometric attacks including kings and pinned attackers; not proof of winning both targets.')
            counts['known_windows']+=1;counts['fork_true_windows']+=bool(fork);counts['check_true_windows']+=bool(check);branches+=1
    # Exact parity with the earlier diagnostic definitions on every fully eligible case.
    prior=json.loads(PRIOR.read_text())['rows'];checks=0
    for k,windows in prior.items():
        for window,r in windows.items():
            assert r is not None
            assert diagnostics[k][window]['acceptance']==r['acceptance']
            assert features[k][window]['acceptor_fork']==r['descriptors']['immediate_fork_targets_acceptor']
            assert features[k][window]['reply_check']==r['descriptors']['first_reply_check']
            checks+=1
    assert len(features)==3724 and checks==2604
    assert all(set(w)=={'acceptor_fork','reply_check'} for c in features.values() for w in c.values())
    write('FEATURES.json',features);write('FEATURE-EVIDENCE.json',diagnostics)
    receipt=dict(status='complete',input_sha256=sha(TRAIN),feature_sha256=sha(H/'FEATURES.json'),
        protocol_sha256=sha(H/'EXTRACTION-PROTOCOL.json'),script_sha256=sha(Path(__file__)),
        evidence_sha256=sha(H/'FEATURE-EVIDENCE.json'),counts=dict(counts),cases=3724,requested_cases=1320,
        original_diagnostic_case_window_parity=checks,legal_acceptance_reply_pairs_checked=branches,
        elapsed_seconds=time.monotonic()-start,new_engine_queries=0,
        semantics='Original75 features unchanged. Two new booleans from opponent-best saved accepting branch and its best first reply; all branches scored before choosing; mate order preserved; missing remains null. No truth or classifier score used.')
    write('EXTRACTION.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
