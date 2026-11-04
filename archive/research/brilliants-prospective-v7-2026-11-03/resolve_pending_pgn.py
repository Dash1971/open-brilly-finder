"""Resolve only prelisted historical cards with the existing public monthly collector."""
import importlib.util
import io
import json
import pathlib
import re
import sqlite3
import sys

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent
W = ROOT.parent.parent
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
m = module('v7_corpus', ROOT / 'corpus.py')
old = module('approved_monthly_collector', W / 'research/brilliants-600-2026-11-03/corpus.py')
load = lambda p: json.loads(p.read_text())
pending = load(ROOT / 'ELIGIBLE-PGN-POOL.json')['pending']
pool = {(r['game_id'],r['ply']):r for r in load(ROOT / 'historical-pool-snapshot.json')['rows']}
conn = sqlite3.connect(ROOT / 'corpus.sqlite3')
conn.row_factory = sqlite3.Row
for account in m.ACCOUNTS:
    evidence = []
    for r in pending:
        if r['account'] != account:
            continue
        x = dict(pool[(r['game_id'], r['ply'])])
        x.update(selected=True, selection_status='metadata_resolution_only_not_primary', source_type='gallery', label='!!')
        evidence.append(x)
    if evidence:
        path = ROOT / 'evidence' / f'{account.lower()}-metadata-resolution-only.json'
        path.write_text(json.dumps(evidence,indent=2)+'\n')
        m.import_evidence(conn,path)

def header_import(c,text,source,captured,only):
    stream=io.StringIO(text); found=set()
    while True:
        start=stream.tell(); headers=m.chess.pgn.read_headers(stream);end=stream.tell()
        if headers is None:break
        gid=m.game_id_from(headers.get('Link')) or m.game_id_from(headers.get('Site'))
        if gid not in only:continue
        result=m.import_pgn(c,text[start:end],source,captured,{gid})
        found.update(result['games_imported_or_matched'])
    return {'games_imported_or_matched':sorted(found),'requested_not_found':sorted(only-found)}

old.import_pgn=header_import
# The current public month is mutable. Refresh it once in a NEW evidence folder;
# never replace any earlier monthly response or pretend cached bytes were current.
refresh=ROOT/'current-month-resolution'
refresh.mkdir(exist_ok=True)
refreshes=[]
for account in ['nelsi','GothamChess']:
    ids={r['game_id'] for r in pending if r['account']==account}
    if not ids:continue
    lists=sorted((W/'research').rglob(f'original-pgn/{account.lower()}-archive-list.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
    if not lists:raise RuntimeError('No documented published archive list cached for '+account)
    archives=load(lists[0])['archives']; latest=archives[-1]
    match=re.fullmatch(r'https://api\.chess\.com/pub/player/([^/]+)/games/(\d{4})/(\d{2})',latest)
    assert match and match[1].lower()==account.lower()
    old.ROOT=refresh
    result=old.fetch_month(conn,account,int(match[2]),int(match[3]),ids)
    refreshes.append({'account':account,'published_archive_list_source':str(lists[0].relative_to(W)),
        'archive_list_sha256':m.sha(lists[0].read_bytes()),'published_month':latest,'result':result})
    print(json.dumps(refreshes[-1]),flush=True)
old.ROOT=ROOT
remaining=[a for a in m.ACCOUNTS if conn.execute('SELECT 1 FROM observations o LEFT JOIN games g ON o.game_id=g.game_id WHERE LOWER(o.account)=LOWER(?) AND g.game_id IS NULL',(a,)).fetchone()]
results=old.fetch_selected(conn,remaining)
(ROOT/'PUBLIC-PGN-RESOLUTION.json').write_text(json.dumps({'current_month_refreshes_in_new_folder':refreshes,'bounded_published_month_walk':results,'no_current_review_labels':True},indent=2)+'\n')
print(json.dumps({'remaining':results}),flush=True)
conn.close()
