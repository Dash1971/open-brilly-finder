"""Bounded reuse of existing corpus/PGN procedures for future fixed-source assessment."""
import collections,hashlib,importlib.util,io,json,pathlib,re,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
IMPROVE=ROOT.parent
WORKSPACE=IMPROVE.parent.parent
def load(p):return json.loads(p.read_text())
def save(name,obj):(ROOT/name).write_text(json.dumps(obj,indent=2)+'\n')
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('future_corpus',ROOT/'corpus.py');chess=m.chess
old=module('existing_monthly_collector',WORKSPACE/'research/brilliants-600-2026-11-03/corpus.py')
excluded=set(load(ROOT/'exclude-games.json')['game_ids'])
sources=load(ROOT/'PROVENANCE.json')['sources']
source_dbs=[WORKSPACE/p for p in sources if p.endswith('/corpus.sqlite3')]
pool={};provenance=collections.defaultdict(set)
for a in m.ACCOUNTS:
    p=IMPROVE/'validation'/f'{a.lower()}-candidate-pool.json'
    for r in load(p):
        k=(str(r['game_id']),r['ply']);pool[k]=dict(r);provenance[k].add(str(p.relative_to(WORKSPACE)))
p=IMPROVE/'validation/cached-candidates-COLLECTOR-ONLY.json'
for r in load(p):
    k=(str(r['game_id']),r['ply']);pool.setdefault(k,dict(r));provenance[k].update(r.get('sources',[]));provenance[k].add(str(p.relative_to(WORKSPACE)))
for p in sorted(ROOT.glob('*-gallery-topup-raw.json')):
    for r in load(p):
        k=(str(r['game_id']),r['ply'])
        if k in pool:
            cats=set(pool[k].get('categories',[]))|set(r.get('categories',[]));pool[k].update(r);pool[k]['categories']=sorted(cats)
        else:pool[k]=dict(r)
        provenance[k].add(str(p.relative_to(WORKSPACE)))
pool={k:r for k,r in pool.items() if k[0] not in excluded}
for k,r in pool.items():
    r.update(game_id=k[0],ply=k[1],source_type='gallery',label='!!',current_label='unknown',selected=False,
        historical_gallery_sources=sorted(provenance[k]))
    if not r.get('captured_at'):r['captured_at']=r.get('capture_timestamp')
    if not r.get('captured_at'):
        # Resolve only the original visible gallery record; never invent a timestamp.
        for source in provenance[k]:
            path=WORKSPACE/source
            if not path.exists() or 'cached-candidates' in path.name:continue
            obj=load(path)
            rows=obj if isinstance(obj,list) else obj.get('observations',[])
            match=next((x for x in rows if str(x.get('game_id'))==k[0] and x.get('ply')==k[1]),None)
            if match and (match.get('captured_at') or match.get('capture_timestamp')):
                r['captured_at']=match.get('captured_at') or match.get('capture_timestamp');break
save('historical-pool-snapshot.json',{'created_at':m.now(),'scope':'Onlyhistoricalgallerynominations; no currentlabels or tested-policy predictions.','rows':list(pool.values()),'source_sha256':{str(p.relative_to(WORKSPACE)):m.sha(p.read_bytes()) for p in ROOT.glob('*-gallery-topup-raw.json')}})
conn=m.connect(ROOT/'corpus.sqlite3')
needed={k[0] for k in pool}
import sqlite3
for db in source_dbs:
    c=sqlite3.connect(f'file:{db}?mode=ro',uri=True);c.row_factory=sqlite3.Row
    for g in c.execute('select * from games'):
        if g['game_id'] not in needed:continue
        if conn.execute('select 1 from games where game_id=?',(g['game_id'],)).fetchone():continue
        m.import_pgn(conn,g['pgn'],g['source_link'],g['captured_at'],{g['game_id']})
    c.close()

def header_import(c,text,source,captured,only):
    stream=io.StringIO(text);found=set()
    while True:
        start=stream.tell();headers=chess.pgn.read_headers(stream);end=stream.tell()
        if headers is None:break
        gid=m.game_id_from(headers.get('Link')) or m.game_id_from(headers.get('Site'))
        if gid not in only:continue
        result=m.import_pgn(c,text[start:end],source,captured,{gid})
        found.update(result['games_imported_or_matched'])
    return {'games_imported_or_matched':sorted(found),'requested_not_found':sorted(only-found)}

cache=ROOT/'original-pgn';cache.mkdir(exist_ok=True)
monthly={}
for p in (WORKSPACE/'research').glob('brilliants*/original-pgn/*.pgn'):
    if p.parent.parent==ROOT:continue
    if p.name not in monthly or p.stat().st_mtime_ns>monthly[p.name].stat().st_mtime_ns:monthly[p.name]=p
reused=[]
for name,path in sorted(monthly.items()):
    meta_path=path.with_suffix('.response.json')
    if not meta_path.exists():continue
    meta=load(meta_path);dest=cache/name
    if not dest.exists():dest.symlink_to(path)
    safe={k:meta[k] for k in ['source_link','captured_at','sha256','bytes'] if k in meta}
    safe['reused_local_file']=str(path.relative_to(WORKSPACE));safe['original_response_manifest_sha256']=m.sha(meta_path.read_bytes())
    if not dest.with_suffix('.response.json').exists():dest.with_suffix('.response.json').write_text(json.dumps(safe,indent=2)+'\n')
    missing=needed-{r[0] for r in conn.execute('select game_id from games')}
    relevant={gid for (gid,_),r in pool.items() if gid in missing and name.startswith(str(r['account']).lower()+'-')}
    if relevant:
        result=header_import(conn,path.read_text(),safe['source_link'],safe['captured_at'],relevant)
        reused.append({**safe,'found':result['games_imported_or_matched']})
save('reused-local-months.json',reused)
known={r['canonical_first_four'] for r in load(ROOT/'known-regression-fens.json')['positions']}
def canonical(f):return ' '.join(chess.Board(f).fen().split()[:4])
ready=collections.defaultdict(set)
for (gid,ply),r in pool.items():
    p=conn.execute('select * from positions where game_id=? and ply=?',(gid,ply)).fetchone()
    if p and canonical(p['fen_before']) not in known and canonical(p['fen_after']) not in known:ready[r['account']].add(gid)
pending={}
for account in ('hansen','GothamChess','Hikaru'):
    # Data-availability-only snapshot: fill20 plus at most2PGN-ready positive reserves.
    gap=max(0,22-len(ready[account]))
    rows=[r for (gid,_),r in pool.items() if r['account'].lower()==account.lower() and not conn.execute('select 1 from games where game_id=?',(gid,)).fetchone()]
    rows.sort(key=lambda r:hashlib.sha256(f'mute-future-validation-v5-v1|{account}|{(r.get("categories") or ["All Types"])[0]}|{r["game_id"]}|{r["ply"]}'.encode()).hexdigest())
    chosen=[];ids=set()
    for r in rows:
        if r['game_id'] in ids:continue
        if len(ids)>=gap:break
        if not r.get('captured_at'):continue
        x=dict(r);x.update(selected=True,selection_status='selected_for_bounded_PGN_identity_resolution')
        chosen.append(x);ids.add(r['game_id'])
    path=ROOT/'evidence'/f'{account.lower()}-metadata-resolution-gallery.json';path.write_text(json.dumps(chosen,indent=2)+'\n')
    if chosen:m.import_evidence(conn,path)
    pending[account]=sorted(ids)
save('METADATA-RESOLUTION-SNAPSHOT.json',{'created_at':m.now(),'PGN_ready_unique_unreviewed_games_by_account':{a:len(ready[a]) for a in m.ACCOUNTS},
    'missing_game_ids_frozen_for_documented_public_archive_walk':pending,'max_months_per_account':13,'maximum_ready_target_plus_reserves':22,
    'no_current_labels':True,'no_month_guessing':True,'existing_cached_files_are_reused_not_refetched':True})
print(json.dumps({'PGN_ready':{a:len(ready[a]) for a in m.ACCOUNTS},'frozen_missing':pending}),flush=True)
old.ROOT=ROOT;old.import_pgn=header_import
results=old.fetch_selected(conn,[a for a,ids in pending.items() if ids])
save('PUBLIC-ARCHIVE-RESOLUTION.json',results)
print(json.dumps({'public_archive_resolution':results,'games':conn.execute('select count(*) from games').fetchone()[0]}),flush=True)
conn.close()
