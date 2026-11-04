"""Legally replay existing lines for the fixed twelve-pair descriptive panel."""
import json,gzip,io,sys,hashlib
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.pgn
H=Path(__file__).resolve().parent;W=H.parents[1]
PACK=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/pv-trajectory-experiment/source-pack'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lines(board,snapshot):
    result={}
    for window in ('current','previous'):
        snap=snapshot.get(window);out=[]
        if not snap:result[window]=None;continue
        for l in snap['lines']:
            b=board.copy(stack=True);sans=[];events=[]
            for ply,u in enumerate(l['moves'],1):
                move=chess.Move.from_uci(u);assert move in b.legal_moves
                san=b.san(move);v=b.piece_at(move.to_square)
                if b.is_en_passant(move):v=chess.Piece(chess.PAWN,not b.turn)
                sans.append(san)
                if v:events.append(dict(ply=ply,san=san,victim=v.symbol()))
                b.push(move)
            out.append(dict(cp_white=l.get('cp'),mate_white=l.get('mate'),san=' '.join(sans),moves=l['moves'],captures=events,
                            terminal=b.is_game_over(claim_draw=False),checkmate=b.is_checkmate(),end_fen=b.fen()))
        result[window]=dict(depth=snap['depth'],lines=out)
    return result
def main():
    panel=json.loads((H/'PANEL.json').read_text());keys={p[role]['key'] for p in panel for role in ('miss','ordinary')}
    sources={}
    with gzip.open(PACK/'after-snapshots.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line)
            if r['key'] in keys:sources[r['key']]=r
    games={};wanted={r['pgn_key'] for r in sources.values()}
    with gzip.open(PACK/'games.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line)
            if r['pgn_key'] in wanted:games[r['pgn_key']]=r
    accepted={}
    path=W/'research/brilliant-conditional-gap-2026-11-04/ENGINE-EVIDENCE.jsonl'
    with path.open() as f:
        for line in f:
            r=json.loads(line)
            if r['key'] in keys:accepted[r['key']]=r
    assert len(sources)==len(keys)==24
    out=[];count=0
    for i,p in enumerate(panel,1):
        pair=dict(number=i,match=p['pair'])
        for role in ('miss','ordinary'):
            c=p[role];s=sources[c['key']];g=games[s['pgn_key']]
            assert hashlib.sha256(g['pgn'].encode()).hexdigest()==g['pgn_sha256']
            game=chess.pgn.read_game(io.StringIO(g['pgn']));assert not game.errors
            b=game.board();ply=int(c['key'].rsplit(':',1)[1])
            for move in list(game.mainline_moves())[:ply-1]:b.push(move)
            assert b.fen()==c['fen_before'];move=chess.Move.from_uci(c['uci']);san=b.san(move)
            a=b.copy(stack=True);a.push(move);assert a.fen()==c['fen_after']
            record=dict(key=c['key'],san=san,mover='white' if b.turn else 'black',pgn=g['pgn'],pgn_sha256=g['pgn_sha256'],
                fen_before=b.fen(),fen_after=a.fen(),features=c['windows'],
                piece_inventory={color:{chess.piece_name(t):len(b.pieces(t,chess.WHITE if color=='white' else chess.BLACK)) for t in range(1,6)} for color in ('white','black')},
                after_lines=lines(a,s['after_snapshot']),acceptances=[])
            count+=sum(len(v['lines']) for v in record['after_lines'].values() if v)
            ev=accepted.get(c['key'])
            if ev:
                assert ev['pgn_sha256']==g['pgn_sha256']
                for o in ev['offers']:
                    ac=a.copy(stack=True);cap=chess.Move.from_uci(o['uci']);victim=ac.piece_at(cap.to_square);cap_san=ac.san(cap);ac.push(cap)
                    assert ac.fen()==o['accepted_fen']
                    response=lines(ac,o['snapshot']);count+=sum(len(v['lines']) for v in response.values() if v)
                    record['acceptances'].append(dict(uci=o['uci'],san=cap_san,victim=victim.symbol() if victim else None,
                                                      moved_piece_offered=cap.to_square==move.to_square,lines=response))
            record['acceptance_evidence_present']=ev is not None
            pair[role]=record
        out.append(pair)
    result=dict(scope='Fixed descriptive panel, saved evidence only; scores white-oriented; no new engine searches or rule.',
                input_sha256={str(p):sha(p) for p in [H/'PANEL.json',PACK/'after-snapshots.jsonl.gz',PACK/'games.jsonl.gz',path]},
                script_sha256=sha(Path(__file__)),legally_replayed_lines=count,pairs=out)
    (H/'PANEL-EVIDENCE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=24,pairs=12,legally_replayed_lines=count)))
if __name__=='__main__':main()
