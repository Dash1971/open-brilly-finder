"""One-study deterministic matching on existing features, before new searches."""
import sys,json,gzip,hashlib,io,collections
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.pgn
HERE=Path(__file__).resolve().parent
WORK=HERE.parents[1]
STUDY=WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
sys.path.insert(0,str(WORK/'research/brilliants-training-overnight-2026-11-03/adapter'))
import importlib.util
spec=importlib.util.spec_from_file_location('saved_pv',WORK/'research/brilliants-training-overnight-2026-11-03/adapter/augment-pv.py')
pv=importlib.util.module_from_spec(spec);spec.loader.exec_module(pv)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
base=json.loads((STUDY/'data/training.json').read_text())
pred={c['key']:c for c in json.loads((WORK/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json').read_text())}
cases=[c for c in base['cases'] if c['cohort'].startswith('batch') and pred[c['key']]['eligible'] and not c['windows']['current']['features']['ec_sacrifice']]
pos=[c for c in cases if c['truth'] and not pred[c['key']]['outer_awards']['custom_fixed']]
neg=[c for c in cases if not c['truth'] and c['negative_bucket']=='hard_ordinary']
assert len(pos)==51 and len(neg)==149
numeric={'after_mapped_score':300,'physical_debt3_max':300,'physical_debt3_min':300,'offer_exchange_gain_max':300,
         'capture_promotion_credit':300,'prior_offer_gain_same_square_max':300,'phase':12,'best_second_gap_pp':20,'raw_material_before':600}
boolean=['move_check','move_in_check','converted_material_or_endgame','avoidability','checked_continuation']
def category(f):
    return (f['move_capture'],f['offered_piece_moved'],bool(f['offered_role_n'] or f['offered_role_b']),f['offered_role_r'],f['offered_role_q'])
def distance(a,b):
    a,b=a['windows']['current']['features'],b['windows']['current']['features']
    if category(a)!=category(b):return None
    ds=[]
    for k,s in numeric.items():
        ds.append(0 if a[k] is None and b[k] is None else 1 if a[k] is None or b[k] is None else min(1,abs(a[k]-b[k])/s))
    ds.extend(float(a[k]!=b[k]) for k in boolean)
    return sum(ds)/len(ds)
edges=[]
for a in pos:
    for b in neg:
        d=distance(a,b)
        if d is not None and a['group']!=b['group']:edges.append((d,a['key'],b['key'],a,b))
used=set();pairs=[]
for d,ak,bk,a,b in sorted(edges,key=lambda x:x[:3]):
    if a['group'] in used or b['group'] in used:continue
    used.update([a['group'],b['group']]);pairs.append({'pair':len(pairs)+1,'distance':d,'positive':ak,'ordinary':bk})
    if len(pairs)==24:break
selected={k for p in pairs for k in [p['positive'],p['ordinary']]}
assert len(pairs)==24 and len(selected)==48
bykey={c['key']:c for c in cases if c['key'] in selected}
snapshots={}
with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/after-snapshots.jsonl.gz','rt') as f:
    for line in f:
        r=json.loads(line)
        if r['key'] in selected:snapshots[r['key']]=r
pgnkeys={r['pgn_key'] for r in snapshots.values()};games={}
with gzip.open(STUDY/'pv-trajectory-experiment/source-pack/games.jsonl.gz','rt') as f:
    for line in f:
        r=json.loads(line)
        if r['pgn_key'] in pgnkeys:games[r['pgn_key']]=r
metadata={}
for cohort in {c['cohort'] for c in bykey.values()}:
    source=WORK/'research/brilliants-training-overnight-2026-11-03/engine-batches'/cohort/'analysis.json'
    bank=json.loads(source.read_text())
    for t in bank['targets']:
        k=str(t['game_id'])+':'+str(t['ply'])
        if k in selected:metadata[k]={'label':t['label'],'rating':t['actual_mover_rating'],'mover':t['actual_mover'],'source':str(source.relative_to(WORK)),'source_sha256':sha(source)}
    del bank
out=[]
for key in sorted(selected):
    c=bykey[key];s=snapshots[key];g=games[s['pgn_key']]
    assert hashlib.sha256(g['pgn'].encode()).hexdigest()==g['pgn_sha256']
    game=chess.pgn.read_game(io.StringIO(g['pgn']));assert game and not game.errors
    ply=int(key.rsplit(':',1)[1]);board=game.board();before=None;san=None;history=[]
    for i,m in enumerate(game.mainline_moves(),1):
        sm=board.san(m)
        if i==ply:before=board.copy(stack=True);san=sm
        board.push(m);history.append(sm)
        if i==ply:break
    assert before.fen()==c['fen_before'] and board.fen()==c['fen_after'] and board.peek().uci()==c['uci']
    offers,unknown,nodes=pv.qualify(before,board)
    assert not unknown
    captures=[]
    for u,o in sorted(offers.items()):
        m=chess.Move.from_uci(u)
        captures.append({'uci':u,'san':board.san(m),'victim':board.piece_at(m.to_square).symbol(),**o})
    assert 1<=len(captures)<=4
    if not c['truth']:assert metadata[key]['label'].lower() in ['great','best','excellent','good']
    else:assert metadata[key]['label'].lower()=='brilliant'
    current=c['windows']['current']['features'];ss=s['after_snapshot']['current']
    saved=pv.window_features(before,board,ss,offers,False)
    saved_lines=[]
    for line in ss['lines'][:2]:
        b=board.copy(stack=True);sans=[]
        for u in line['moves'][:12]:
            m=chess.Move.from_uci(u);assert m in b.legal_moves;sans.append(b.san(m));b.push(m)
        saved_lines.append({'cp_mover':line.get('cp')*(1 if before.turn else -1) if line.get('cp') is not None else None,
                            'mate_mover':line.get('mate')*(1 if before.turn else -1) if line.get('mate') is not None else None,
                            'uci':line['moves'][:12],'san':sans})
    out.append({'key':key,'truth':c['truth'],'group':c['group'],'san':san,'fen_before':c['fen_before'],'fen_after':c['fen_after'],
        'uci':c['uci'],'history_last_6':history[-7:-1],'current_features':current,'saved_pv_features':saved,'saved_lines':saved_lines,
        'offers':captures,'metadata':metadata[key],'pgn_key':s['pgn_key'],'pgn_sha256':g['pgn_sha256'],
        'oof_score':pred[key]['outer_scores']['custom']})
write('MATCHED-CASES.json',out)
write('MATCHED-GAMES.json',list(games.values()))
protocol={'scope':'Diagnostic matched case-control study; not classifier validation or representative prevalence. No fitting or app changes.',
 'input_sha256':sha(STUDY/'data/training.json'),'script_sha256':sha(Path(__file__)),
 'population':{'missed_fresh_eligible_ec_false_positives':51,'fresh_eligible_ec_false_hard_ordinary':149},
 'matching':{'exact':['move_capture','offered_piece_moved','offered minor/rook/queen types'],
             'scaled_numeric':numeric,'boolean':boolean,'distance':'Mean capped numeric absolute difference plus boolean disagreements; None mismatch=1',
             'selection':'Greedy nearest cross-label pairs, deterministic key ties, each whole-game/position group used once; first24pairs. No new search outcome used.'},
 'pairs':pairs,'cases_sha256':sha(HERE/'MATCHED-CASES.json'),'games_sha256':sha(HERE/'MATCHED-GAMES.json'),
 'new_search_plan':{'engine_sha256':'ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374',
   'question':'What happens if each qualifying offer is accepted, including branches absent from saved top2?',
   'positions':'After each accepting capture, full PGN history retained; same bounded SEE qualification as savedPV experiment.',
   'nodes_per_search':300000,'threads':1,'hash_mb':64,'multipv':2,'max_cases':48,'max_offers_per_case':4,'max_searches':192,'wall_seconds':300,
   'observations':['acceptance evaluation vs saved best defense (different searches; noisy)','compensation best/second response gap',
     'material trajectory through12plies including acceptance','material recovery ply','checks and promotions','mate/stalemate terminals'],
   'interpretation':'Exploratory evidence only; exact features may be summarized after review, with counterexamples. No rule fitting or award claims.'}}
write('PROTOCOL.json',protocol)
print(json.dumps({'pairs':len(pairs),'distance_min':min(p['distance'] for p in pairs),'distance_max':max(p['distance'] for p in pairs),
 'searches':sum(len(c['offers']) for c in out),'saved_acceptance_absent':collections.Counter(str(c['truth']) for c in out if not c['saved_pv_features']['pv_any_saved_accepts'])},indent=2))
