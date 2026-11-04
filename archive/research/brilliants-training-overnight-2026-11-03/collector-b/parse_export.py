"""Study-only legal replay of the visible UI export; no engine or label inference."""
import hashlib
import io
import json
import pathlib
import re
import sys

sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
import chess.pgn

root=pathlib.Path(__file__).resolve().parent.parent
game_id=sys.argv[1]
queue_path=root/sys.argv[2]
queue_document=json.loads(queue_path.read_text())
entry=next(g for g in queue_document['games'] if g['game_id']==game_id)
export_path=root/'collector-b'/f'{game_id}.review-export.pgn'
text=export_path.read_text()
game=chess.pgn.read_game(io.StringIO(text))
assert game and not game.errors
link=re.search(r'/(?:live|daily)/(\d+)',game.headers.get('Link','')+' '+game.headers.get('Site',''))
assert link and link[1]==game_id
expected={p['ply']:p for p in entry['positions']}
board=game.board();positions=[]
mapping={1:'great',2:'mistake',3:'brilliant',4:'blunder',6:'inaccuracy',9:'miss'}
for ply,node in enumerate(game.mainline(),1):
    move=node.move
    assert move in board.legal_moves
    san=board.san(move);before=board.fen();capture=board.is_capture(move)
    victim=board.piece_type_at(move.to_square)
    previous=positions[-1] if positions else None
    recapture=bool(capture and previous and previous['capture'] and previous['uci'][2:4]==move.uci()[2:4])
    board.push(move)
    assert (san,move.uci(),before,board.fen())==tuple(expected[ply][k] for k in ['san','uci','fen_before','fen_after'])
    nags=sorted(node.nags);known=[mapping[n] for n in nags if n in mapping]
    assert len(set(known))<=1,('multiple explicit labels',game_id,ply,nags)
    positions.append({'game_id':game_id,'ply':ply,'san':san,'uci':move.uci(),'fen_before':before,'fen_after':board.fen(),
        'nags':nags,'explicit_export_label':known[0] if known else None,'label_status':'explicit_review_export_NAG' if known else 'unknown',
        'capture':capture,'captured_role':chess.piece_name(victim) if victim else None,'recapture':recapture,
        'known_position_overlap':expected[ply].get('known_position_overlap'),'split':entry['split']})
assert len(positions)==len(expected)
positives=[p for p in positions if p['explicit_export_label']=='brilliant']
samples=[]
# Verify one deterministic representative per present non3 export category.
for label in ['great','mistake','blunder','inaccuracy','miss']:
    candidates=[p for p in positions if p['explicit_export_label']==label]
    if candidates:
        candidates.sort(key=lambda p:hashlib.sha256(f'mute-overnight-export-check-v1:{game_id}:{label}:{p["ply"]}'.encode()).hexdigest())
        samples.append(candidates[0])
unknown=[p for p in positions if not p['nags']]
unknown.sort(key=lambda p:(not p['recapture'],not p['capture'],hashlib.sha256(f'mute-overnight-hard-control-v1:{game_id}:{p["ply"]}'.encode()).hexdigest()))
controls=unknown[:2]
selection_version='v2_all_unannotated_capture_recapture_then_hash_no_opening_cutoff'
sidecar_metadata=None
wave=re.search(r'wave(\d+)',queue_path.stem)
if queue_document.get('control_sampling_version')=='static_offer_v3' or (wave and int(wave[1])>=4):
    sidecar_path=root/('control-offers-'+queue_path.stem.replace('queue-','')+'.json')
    sidecar=json.loads(sidecar_path.read_text())
    assert sidecar['queue_sha256']==hashlib.sha256(queue_path.read_bytes()).hexdigest()
    described=next(g for g in sidecar['games'] if g['game_id']==game_id)
    offer_by_ply={p['ply']:p.get('raw_legal_offer') for p in described['positions']}
    nomination=entry['primary_nomination_ply']
    offers=[p for p in unknown if offer_by_ply.get(p['ply']) is True]
    offers.sort(key=lambda p:(abs(p['ply']-nomination),not p['capture'],p['ply'],p['uci']))
    controls=offers[:4]
    for candidate in unknown:
        if len(controls)>=2:break
        if all(candidate['ply']!=p['ply'] for p in controls):controls.append(candidate)
    selection_version='static_offer_v3'
    sidecar_metadata={'artifact':sidecar_path.name,'sha256':hashlib.sha256(sidecar_path.read_bytes()).hexdigest(),
        'source_helper_sha256':sidecar['source_helper_sha256'],'created_at_utc':sidecar['created_at_utc']}
    for p in controls:p.update(raw_legal_offer=offer_by_ply.get(p['ply']),control_selection_version=selection_version,control_sidecar=sidecar_metadata)
checks=[]
for role,rows in [('all_export_brilliant',positives),('deterministic_export_nonbrilliant',samples),('unannotated_explicit_UI_control',controls)]:
    for row in rows:checks.append(dict(row,verification_role=role))
already={p['ply'] for p in checks}
for target in entry.get('gallery_targets',[]):
    if target['ply'] not in already:
        checks.append(dict(positions[target['ply']-1],verification_role='historical_nomination_current_UI_audit'))
        already.add(target['ply'])
# Operational order only: identical selected checks, less move-list scrolling.
checks.sort(key=lambda row:row['ply'])
for row in checks:row['game_total_plies']=len(positions)
out={'game_id':game_id,'split':entry['split'],'account':entry['account'],'queue_artifact':sys.argv[2],
    'original_public_pgn_sha256':entry['pgn_sha256'],'UI_export_sha256':hashlib.sha256(text.encode()).hexdigest(),
    'positions':positions,'verification_queue':checks,'verification_order':'chronological; selected set unchanged',
    'explicit_export_label_count':sum(p['explicit_export_label'] is not None for p in positions),
    'explicit_export_brilliants':len(positives),'unannotated_remain_unknown_without_UI':True,'whole_game_legal_replay_matches_queued_history':True,
    'unannotated_control_target':2,'unannotated_control_candidates_available':len(unknown),
    'control_selection_version':selection_version,'control_sidecar':sidecar_metadata,
    'historical_nomination_export_comparison':[{'ply':t['ply'],'historical_label':'brilliant',
        'explicit_export_label':positions[t['ply']-1]['explicit_export_label'],
        'status':'unknown' if positions[t['ply']-1]['explicit_export_label'] is None else
        'matches' if positions[t['ply']-1]['explicit_export_label']=='brilliant' else 'disagrees'} for t in entry.get('gallery_targets',[])]}
path=root/'collector-b'/f'{game_id}.parsed.json';path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['positions','verification_queue']}))
