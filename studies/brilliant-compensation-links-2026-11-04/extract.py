"""Study-local, label-blind saved-evidence geometry. No engines, fits, or new labels."""
import collections, gzip, hashlib, json, resource, signal, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
HERE=Path(__file__).resolve().parent; WORK=HERE.parents[1]
TRAIN=WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
EVIDENCE=WORK/'research/brilliant-conditional-gap-2026-11-04/ENGINE-EVIDENCE.jsonl'
WINDOWS=['current','previous']; VALUES={1:90,2:300,3:300,4:500,5:1000,6:0}
START=time.monotonic(); CHECKS=collections.Counter()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v): (HERE/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def cap(*_): raise TimeoutError('600-second extraction limit; no automatic retry')
def guard():
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
    if time.monotonic()-START>=600 or rss>=512*1024*1024: raise RuntimeError('600-second/512-MB extraction cap')
def square(s): return chess.square_name(s)
def role(p): return chess.piece_name(p.piece_type) if p else None
def color(c): return 'white' if c else 'black'
def piece(b,s):
    p=b.piece_at(s)
    return None if p is None else {'role':role(p),'color':color(p.color),'square':square(s)}
def material(b,c): return sum(VALUES[p.piece_type]*(1 if p.color==c else -1) for p in b.piece_map().values())
def captured_square(b,m): return m.to_square+(-8 if b.turn else 8) if b.is_en_passant(m) else m.to_square

def push_identity(b,m,ids):
    """Stable initial-square IDs survive movement/promotion; standard castling and EP handled."""
    origin=m.from_square; dest=m.to_square; token=ids.pop(origin)
    if b.is_capture(m): ids.pop(captured_square(b,m),None)
    if b.is_castling(m):
        assert not b.chess960
        rank=chess.square_rank(origin); kingside=dest>origin
        rf=chess.square(7 if kingside else 0,rank); rt=chess.square(5 if kingside else 3,rank)
        ids[rt]=ids.pop(rf)
    ids[dest]=token; b.push(m)
    assert set(ids)==set(b.piece_map())

def target(b,s,ids,acceptor_id):
    return {**piece(b,s),'piece_id':ids[s],'is_acceptor':ids[s]==acceptor_id}
def targets(b,s,mover,ids,acceptor_id):
    return [target(b,t,ids,acceptor_id) for t in sorted(b.attacks(s)) if (p:=b.piece_at(t)) and p.color!=mover and p.piece_type!=chess.PAWN]
def attack_relations(b,mover):
    return {(s,t,p.piece_type,q.piece_type) for s,p in b.piece_map().items() if p.color==mover for t in b.attacks(s) if (q:=b.piece_at(t)) and q.color!=mover and q.piece_type!=chess.PAWN}
def slider_compatible(b,s,t):
    p=b.piece_at(s); df=abs(chess.square_file(s)-chess.square_file(t)); dr=abs(chess.square_rank(s)-chess.square_rank(t))
    return p is not None and (p.piece_type==chess.QUEEN and (df==dr or df==0 or dr==0) or p.piece_type==chess.BISHOP and df==dr or p.piece_type==chess.ROOK and (df==0 or dr==0))
def pins(b,mover,ids,acceptor_id):
    enemy=not mover; king=b.king(enemy); out={}
    if king is None: return out
    for s,p in b.piece_map().items():
        if p.color!=mover or p.piece_type not in [chess.BISHOP,chess.ROOK,chess.QUEEN] or not slider_compatible(b,s,king): continue
        occupied=chess.between(s,king)&b.occupied
        if chess.popcount(occupied)!=1: continue
        t=chess.lsb(occupied); q=b.piece_at(t)
        if q.color!=enemy or q.piece_type==chess.KING: continue
        assert b.is_pinned(enemy,t)
        key=(s,t,p.piece_type,q.piece_type,king)
        out[key]={'slider':piece(b,s),'pinned':target(b,t,ids,acceptor_id),'king':piece(b,king)}
    return out

def acceptance_geometry(after,a,m,mover,ids,acceptor_id):
    old=attack_relations(after,mover); links=[]
    for s,t,pr,qr in sorted(attack_relations(a,mover)-old):
        if pr not in [chess.BISHOP,chess.ROOK,chess.QUEEN]: continue
        blockers=[x for x in chess.scan_forward(chess.between(s,t)&after.occupied)]
        cleared=blockers==[m.from_square] and a.piece_at(m.from_square) is None
        dest=t==m.to_square and ids[t]==acceptor_id
        if not (cleared or dest): continue
        links.append({'slider':piece(a,s),'target':target(a,t,ids,acceptor_id),'acceptor_origin_cleared_only_blocker':cleared,
                      'new_enemy_target_at_acceptor_destination':dest,'destination_square_previously_attacked':t in after.attacks(s),
                      'acceptor_previously_attacked_at_origin':m.from_square in after.attacks(s),
                      'afterplayed_between_blockers':[square(x) for x in blockers]})
    return links

def line_trace(before,after,accepted,acceptance,line,mover,initial_ids,acceptor_id):
    b=accepted.copy(stack=False); ids=dict(initial_ids); moves=line.get('moves',[]); assert isinstance(moves,list)
    first=None; captures=[]; forks=[]; newpins=[]; recaptured=None; firstother=None; mate=None; gain6=None; special=[]; local_terminal=None
    for ply,u in enumerate(moves,1):
        m=chess.Move.from_uci(u); assert m in b.legal_moves,(ply,u,b.fen()); CHECKS['full_pv_legal_moves']+=1
        if ply<=6:
            priorpins=pins(b,mover,ids,acceptor_id); actor=b.turn; actorid=ids[m.from_square]; acting=b.piece_at(m.from_square)
            iscapture=b.is_capture(m); cs=captured_square(b,m) if iscapture else None; victim=b.piece_at(cs) if iscapture else None
            san=b.san(m); check=b.gives_check(m); isacceptorcapture=iscapture and ids.get(cs)==acceptor_id
            if ply==1:
                first={'uci':u,'san':san,'piece_role':role(acting),'type':'capture' if iscapture else 'castling' if b.is_castling(m) else 'quiet','check':check,
                       'directly_recaptures_acceptor':isacceptorcapture,'to_acceptor_destination':m.to_square==acceptance.to_square,
                       'destination_occupancy_afterplayed':piece(after,m.to_square),'destination_occupancy_accepted':piece(b,m.to_square)}
                if acting.piece_type in [chess.BISHOP,chess.ROOK,chess.QUEEN] and slider_compatible(b,m.from_square,m.to_square):
                    blocked=list(chess.scan_forward(chess.between(m.from_square,m.to_square)&after.occupied))
                    first['acceptance_cleared_slider_path']={'observed':blocked==[acceptance.from_square] and b.piece_at(acceptance.from_square) is None,
                        'from':square(m.from_square),'to':square(m.to_square),'afterplayed_between_blockers':[square(x) for x in blocked],
                        'acceptor_origin':square(acceptance.from_square),'offered_destination_ownership_before_acceptance':piece(after,acceptance.to_square),
                        'geometric_occupancy_only':True}
                else: first['acceptance_cleared_slider_path']={'observed':False,'geometric_occupancy_only':True}
            if iscapture:
                captures.append({'ply':ply,'role':role(victim),'value':VALUES[victim.piece_type],'square':square(cs),'actor':color(actor),'actor_role':role(acting),'actor_piece_id':actorid,'victim_piece_id':ids[cs],'is_acceptor':isacceptorcapture})
                if isacceptorcapture: recaptured=ply
                if actor==mover and cs!=acceptance.to_square and firstother is None: firstother=ply
            if b.is_castling(m): special.append({'ply':ply,'kind':'castling_identity_handled'})
            if b.is_en_passant(m): special.append({'ply':ply,'kind':'en_passant_identity_handled'})
            if m.promotion: special.append({'ply':ply,'kind':'promotion_identity_retained'})
            push_identity(b,m,ids)
            if actor==mover:
                ts=targets(b,m.to_square,mover,ids,acceptor_id)
                if len(ts)>=2: forks.append({'ply':ply,'piece':piece(b,m.to_square),'piece_id':ids[m.to_square],'fork_geometric_targets':ts})
                now=pins(b,mover,ids,acceptor_id)
                newpins.extend({'ply':ply,**v} for k,v in now.items() if k not in priorpins)
            if b.is_checkmate() and mate is None: mate={'response_ply':ply,'winner':color(not b.turn)}
            if local_terminal is None:
                terminal_kind='checkmate' if b.is_checkmate() else 'stalemate' if b.is_stalemate() else 'insufficient_material' if b.is_insufficient_material() else None
                if terminal_kind: local_terminal={'response_ply':ply,'kind':terminal_kind}
            if ply==6: gain6=material(b,mover)-material(before,mover)
        else: b.push(m)
    CHECKS['full_saved_pvs_legal']+=1
    n=min(6,len(moves)); complete=len(moves)>=6
    white={k:line[k] for k in ['cp','mate'] if line.get(k) is not None}; assert len(white)==1
    kind=next(iter(white)); score=white[kind]
    return {'score_white':{'kind':kind,'value':score},'score_mover':{'kind':kind,'value':score*(1 if mover else -1)},
            'full_pv_legal':True,'full_pv_plies':len(moves),'response_horizon_plies':n,'horizon6_complete':complete,'truncated_before6':not complete,
            'first_reply':first,'mate_within6':mate,'captures':captures,'material_delta6_cp':gain6,
            'acceptor_recaptured_response_ply':recaptured,'first_mover_capture_other_square_response_ply':firstother,
            'forks_geometric':forks,'new_absolute_pins_geometric':newpins,'special_identity_events':special,
            'identity_status':'known','absence_after_saved_pv_unknown':not complete,'local_terminal_within6':local_terminal,
            'nonterminal_truncated_before6':not complete and local_terminal is None,'prior_repetition_history':'unavailable_fen_only'}

METRICS=['direct_recapture','acceptor_recaptured_by6','mover_capture_other_square_by6','fork_geometric','fork_targets_acceptor','new_absolute_pin_geometric','new_pin_acceptor','mate_within6','cleared_first_reply_slider_path','first_reply_to_acceptor_destination','material_delta6_positive']
def summarize(offers,w):
    lines=[l for o in offers for l in o['windows'][w]['responses']]
    missing=any(o['windows'][w]['status']!='saved_complete_top2' for o in offers)
    out={'offers':len(offers),'saved_responses':len(lines),'window_missing':missing,'horizon6_truncated_responses':sum(not l['horizon6_complete'] for l in lines)}
    def observed(l,k):
        f=l['first_reply']
        return {'direct_recapture':bool(f and f['directly_recaptures_acceptor']),
                'acceptor_recaptured_by6':l['acceptor_recaptured_response_ply'] is not None,'mover_capture_other_square_by6':l['first_mover_capture_other_square_response_ply'] is not None,
                'fork_geometric':bool(l['forks_geometric']),'fork_targets_acceptor':any(t['is_acceptor'] for f in l['forks_geometric'] for t in f['fork_geometric_targets']),
                'new_absolute_pin_geometric':bool(l['new_absolute_pins_geometric']),'new_pin_acceptor':any(p['pinned']['is_acceptor'] for p in l['new_absolute_pins_geometric']),
                'mate_within6':l['mate_within6'] is not None,'cleared_first_reply_slider_path':bool(f and f['acceptance_cleared_slider_path']['observed']),
                'first_reply_to_acceptor_destination':bool(f and f['to_acceptor_destination']),
                'material_delta6_positive':l['material_delta6_cp'] is not None and l['material_delta6_cp']>0}[k]
    for k in METRICS:
        seen=sum(observed(l,k) for l in lines)
        unknown=missing or any((l['first_reply'] is None if k in ['direct_recapture','cleared_first_reply_slider_path','first_reply_to_acceptor_destination'] else not l['horizon6_complete']) for l in lines)
        out[k+'_count']=seen; out[k+'_any']=True if seen else None if unknown else False
    out['acceptance_geometry_any']=any(o['acceptance_geometry_links'] for o in offers)
    out['status']='candidate_roots_absent_no_offers' if not offers else 'saved_evidence'
    return out

def main():
    protocol=json.loads((HERE/'EXTRACTION-PROTOCOL.json').read_text())
    assert sha(__file__)==protocol['extract_script_sha256']
    for p,h in protocol['input_sha256'].items(): assert sha(p)==h,p
    for p,h in protocol['chess_dependency_sha256'].items(): assert sha(p)==h,p
    assert not (HERE/'RELATIONS.json').exists()
    cases=json.loads(TRAIN.read_text())['cases']; assert len(cases)==3724
    selected={c['key']:c for c in cases if c['confidence_sufficient'] and all(c['windows'][w]['eligible'] and not c['windows'][w]['features']['physical_unknown'] for w in WINDOWS)}
    assert len(selected)==1302
    evidence={e['key']:e for e in map(json.loads,EVIDENCE.read_text().splitlines())}; result={}; totals=collections.Counter()
    for key,c in sorted(selected.items()):
        guard(); e=evidence[key]; before=chess.Board(c['fen_before']); after=before.copy(stack=False); played=chess.Move.from_uci(c['uci']); assert played in after.legal_moves; after.push(played); assert after.fen()==c['fen_after']
        mover=before.turn; found=[]; mapping_unknown=any(e['features'][w]['reason']=='offer_mapping_unknown' for w in WINDOWS)
        for offer in e['offers']:
            a=after.copy(stack=False); m=chess.Move.from_uci(offer['uci']); assert m in a.legal_moves and a.is_capture(m)
            victim=piece(a,captured_square(a,m)); acceptor=piece(a,m.from_square); ids={s:color(p.color)+':'+square(s) for s,p in a.piece_map().items()}; acceptor_id=ids[m.from_square]
            assert victim['color']==color(mover) and victim['role'] not in ['pawn','king']
            push_identity(a,m,ids); assert a.fen()==offer['accepted_fen']; CHECKS['accepted_positions']+=1
            row={'acceptance_uci':m.uci(),'victim':victim,'victim_is_played_piece':m.to_square==played.to_square,'acceptor':{**acceptor,'from':square(m.from_square),'to':square(m.to_square),'piece_id':acceptor_id},
                 'capture_credit_cp':max(0,material(after,mover)-material(before,mover)), 'accepted_fen':a.fen(),
                 'acceptance_geometry_links':acceptance_geometry(after,a,m,mover,ids,acceptor_id),'windows':{}}
            legalcount=a.legal_moves.count()
            for w in WINDOWS:
                snap=offer['snapshot'].get(w); lines=[] if not snap else snap.get('lines',[]); roots=[l['moves'][0] for l in lines if l.get('moves')]; assert len(roots)==len(set(roots)); assert len(lines)<=2
                status='missing_window' if not snap else 'saved_complete_top2' if len(roots)>=min(2,legalcount) else 'missing_response_roots'
                row['windows'][w]={'status':status,'depth':None if not snap else snap['depth'],'legal_response_count':legalcount,'saved_root_count':len(roots),
                                    'responses':[line_trace(before,after,a,m,l,mover,ids,acceptor_id) for l in lines]}
                totals[w+':'+status]+=1
            found.append(row)
        r={'mover':color(mover),'played_uci':c['uci'],'fen_before':before.fen(),'fen_afterplayed':after.fen(),'offer_mapping_status':'unknown_node_cap' if mapping_unknown else 'known',
           'candidate_roots_status':'unknown_node_cap' if mapping_unknown else 'saved_offers' if found else 'absent_no_qualifying_offers','offers':found,'summary':{w:summarize(found,w) for w in WINDOWS}}
        if mapping_unknown:
            for w in WINDOWS:
                r['summary'][w]['status']='unknown_node_cap'
                for k in METRICS: r['summary'][w][k+'_any']=None; r['summary'][w][k+'_count']=None
                r['summary'][w]['acceptance_geometry_any']=None
        result[key]=r; CHECKS['cases']+=1; totals['offers']+=len(found)
        totals['candidate_roots:'+r['candidate_roots_status']]+=1
    guard(); write('RELATIONS.json',{'scope':'training3724 all-guards intersection; no labels read','cases':result})
    output={'status':'complete','cases':len(result),'protocol_sha256':sha(HERE/'EXTRACTION-PROTOCOL.json'),'relations_sha256':sha(HERE/'RELATIONS.json'),'checks':dict(CHECKS),'coverage':dict(totals),
            'elapsed_seconds':time.monotonic()-START,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
            'limits':{'runtime_seconds':600,'memory_bytes':512*1024*1024,'response_horizon_plies':6,'new_engine_searches':0},
            'definitions':protocol['definitions']}
    write('EXTRACTION.json',output); print(json.dumps(output))
if __name__=='__main__':
    signal.signal(signal.SIGALRM,cap); signal.alarm(600)
    try: main()
    except Exception as e:
        write('EXTRACTION.json',{'status':'incomplete','reason':repr(e),'checks':dict(CHECKS),'elapsed_seconds':time.monotonic()-START,'no_automatic_retry':True}); raise
    finally: signal.alarm(0)
