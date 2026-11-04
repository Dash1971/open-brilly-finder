"""Existing independent200 PGN/control method, applied only to this bounded future pool."""
import collections,hashlib,importlib.util,io,json,pathlib,re,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
IMPROVE=ROOT.parent
WORKSPACE=IMPROVE.parent.parent
spec=importlib.util.spec_from_file_location('future_corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);chess=m.chess
def load(p):return json.loads(p.read_text())
def save(name,data):(ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
conn=m.connect(ROOT/'corpus.sqlite3')
pool=load(ROOT/'historical-pool-snapshot.json')['rows']
needed={r['game_id'] for r in pool}-{r[0] for r in conn.execute('select game_id from games')}
extra=[]
# Reuse additional selected games present in the already-authorized four new
# monthly responses. This makes no further service call and imports no broad archive.
for path in sorted((ROOT/'original-pgn').glob('*.pgn')):
    if not needed:break
    meta=load(path.with_suffix('.response.json'));text=path.read_text();stream=io.StringIO(text)
    while True:
        start=stream.tell();head=chess.pgn.read_headers(stream);end=stream.tell()
        if head is None:break
        gid=m.game_id_from(head.get('Link')) or m.game_id_from(head.get('Site'))
        if gid not in needed:continue
        m.import_pgn(conn,text[start:end],meta['source_link'],meta['captured_at'],{gid});needed.remove(gid);extra.append(gid)
known={r['canonical_first_four'] for r in load(ROOT/'known-regression-fens.json')['positions']}
def canon(f):return ' '.join(chess.Board(f).fen().split()[:4])
ready=[];unavailable=[];rejected=[]
for raw in pool:
    gid,ply=raw['game_id'],raw['ply'];p=conn.execute('select * from positions where game_id=? and ply=?',(gid,ply)).fetchone();g=conn.execute('select * from games where game_id=?',(gid,)).fetchone()
    if not p or not g:unavailable.append({'game_id':gid,'ply':ply,'account':raw['account'],'reason':'PGNnotresolvedinboundedcache/monthwalk;originalcardretained'});continue
    if canon(p['fen_before']) in known or canon(p['fen_after']) in known:rejected.append({'game_id':gid,'ply':ply,'reason':'knownbefore/afterposition'});continue
    x=dict(raw);x['gallery_board_pieces']=raw.get('gallery_board_pieces') or raw.get('pieces') or raw.get('board_piece_classes') or []
    board=m.observed_board(x)
    if board and board!=p['fen_after'].split()[0]:rejected.append({'game_id':gid,'ply':ply,'reason':'capturedgalleryboardmismatch'});continue
    if raw.get('san') and raw['san']!=p['san'] or raw.get('uci') and raw['uci']!=p['uci']:rejected.append({'game_id':gid,'ply':ply,'reason':'cachedSAN/UCImismatch'});continue
    account=next(a for a in m.ACCOUNTS if a.lower()==raw['account'].lower())
    mover=g['white'] if p['fen_before'].split()[1]=='w' else g['black']
    if mover.lower()!=account.lower():rejected.append({'game_id':gid,'ply':ply,'reason':'accountnotmover'});continue
    h=json.loads(g['headers_json']);match=re.search(r'/(live|daily)/',h.get('Link','')+' '+h.get('Site',''))
    if not match:rejected.append({'game_id':gid,'ply':ply,'reason':'namespaceunknown'});continue
    if raw.get('game_type') and raw['game_type']!=match[1]:rejected.append({'game_id':gid,'ply':ply,'reason':'namespaceconflict'});continue
    if not raw.get('captured_at'):rejected.append({'game_id':gid,'ply':ply,'reason':'originalcapturetimestampmissing'});continue
    x.update({k:p[k] for k in ['san','uci','fen_before','fen_after']});x.update(account=account,game_type=match[1],expected_game_type=match[1],
        source_link=f'https://www.chess.com/analysis/game/{match[1]}/{gid}/review?move={ply-1}',
        historical_gallery_source_link=raw.get('source_link'),source_type='gallery',label='!!',current_label='unknown',selected=False,sample_role='positive_candidate',
        categories=raw.get('categories') or [],pgn_sha256=g['pgn_sha256'],pgn_date=g['date'],board_identity_captured=bool(board),board_missing=not bool(board))
    ready.append(x)
save('ELIGIBLE-PGN-POOL.json',{'created_at':m.now(),'ready':ready,'unavailable':unavailable,'rejected':rejected,'additional_games_from_already_downloaded_months':extra})

prior={}
for folder in [IMPROVE/'validation',WORKSPACE/'research/brilliants-600-2026-11-03',WORKSPACE/'research/brilliants-additional-300-2026-11-03']:
    for path in folder.glob('control-candidates-v2-*.json'):
        for r in load(path).get('rows',[]):prior.setdefault((r['game_id'],r['ply']),r)
gallery={(r['game_id'],r['ply']) for r in pool}
values={1:90,2:300,3:300,4:500,5:1000,6:0}
def material(b,color):return sum(values[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
out=[]
for account in m.ACCOUNTS:
    for gid in sorted({r['game_id'] for r in ready if r['account']==account}):
        g=conn.execute('select * from games where game_id=?',(gid,)).fetchone();color=g['white'].lower()==account.lower()
        link=json.loads(g['headers_json']).get('Link','');namespace=re.search(r'/(live|daily)/',link)[1]
        rows={p['ply']:p for p in conn.execute('select * from positions where game_id=? order by ply',(gid,))}
        for ply,p in rows.items():
            before=chess.Board(p['fen_before']);after=chess.Board(p['fen_after'])
            if before.turn!=color or (gid,ply) in gallery or canon(p['fen_before']) in known or canon(p['fen_after']) in known or after.is_game_over():continue
            move=chess.Move.from_uci(p['uci']);piece=before.piece_at(move.from_square);capture=before.is_capture(move);prev=rows.get(ply-1)
            recapture=bool(capture and prev and prev['uci'][2:4]==p['uci'][2:4] and chess.Board(prev['fen_before']).is_capture(chess.Move.from_uci(prev['uci'])))
            x={k:p[k] for k in ['game_id','ply','san','uci','fen_before','fen_after']}|{'account':account,'game_type':namespace,'expected_game_type':namespace,
                'source_link':f'https://www.chess.com/analysis/game/{namespace}/{gid}/review?move={ply-1}','capture':capture,'recapture_same_square':recapture,
                'moved_piece':piece.symbol(),'raw_material_before_mover':material(before,color),'raw_material_after_mover':material(after,color),
                'immediate_material_gain':material(after,color)-material(before,color),'moved_piece_attacked':after.is_attacked_by(not color,move.to_square),
                'moved_piece_defended':after.is_attacked_by(color,move.to_square),'selected':False,'label':'unknown'}
            old=prior.get((gid,ply))
            if old and all(old[k]==x[k] for k in ['fen_before','fen_after']):
                x['current_v2_legal_piece_offer']=old['current_v2_legal_piece_offer'];x['offer_source']='reusedexactpinnedraw-v2descriptor'
            out.append(x)
assert len(out)<=20000
save('control-preparation-input.json',out)
print(json.dumps({'ready_games':{a:len({r['game_id'] for r in ready if r['account']==a}) for a in m.ACCOUNTS},'rejected':rejected,'unavailable':len(unavailable),
    'ownturncontrolpositions':len(out),'need_pinned_raw_predicate':sum('current_v2_legal_piece_offer' not in r for r in out)}),flush=True)
conn.close()
