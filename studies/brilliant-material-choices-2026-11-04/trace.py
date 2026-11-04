"""Replay diagnostic material ledgers; no classification, fitting, or new searches."""
import hashlib, io, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess, chess.pgn

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'brilliant-mating-mechanisms-2026-11-04/CASES.json'
VALUES = {chess.PAWN: 90, chess.KNIGHT: 300, chess.BISHOP: 300,
          chess.ROOK: 500, chess.QUEEN: 1000, chess.KING: 0}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def balance(board, color):
    return sum(value * (len(board.pieces(piece, color)) - len(board.pieces(piece, not color)))
               for piece, value in VALUES.items())

def ledger(before, moves, expected_fens=None):
    board = before.copy(stack=True)
    color = before.turn
    initial = balance(board, color)
    records = []
    for ply, uci in enumerate(moves, 1):
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves, (board.fen(), uci)
        san = board.san(move)
        victim = board.piece_at(move.to_square)
        if board.is_en_passant(move):
            victim = chess.Piece(chess.PAWN, not board.turn)
        actor = 'mover' if board.turn == color else 'opponent'
        board.push(move)
        if expected_fens is not None:
            assert board.fen() == expected_fens[ply - 1]
        value = balance(board, color)
        records.append(dict(ply=ply, san=san, uci=uci, actor=actor,
                            captured=victim.symbol() if victim else None,
                            promotion=chess.piece_symbol(move.promotion) if move.promotion else None,
                            balance=value, delta=value-initial,
                            checkmate=board.is_checkmate()))
    terminal = board.is_game_over(claim_draw=False)
    return dict(initial_balance=initial, plies=len(records),
                material_delta_at_ply={str(p): records[p-1]['delta'] if len(records)>=p else None
                                      for p in (1,2,3,4,6,12)},
                minimum_delta=min([0]+[r['delta'] for r in records]),
                end_delta=balance(board,color)-initial,
                terminal_result=board.result(claim_draw=False) if terminal else None,
                end_checkmate=board.is_checkmate(),
                end_is_nonterminal_truncation=not terminal,
                capture_promotion_events=[r for r in records if r['captured'] or r['promotion']],
                all_plies=records)

def main():
    source = json.loads(SOURCE.read_text())
    choices = json.loads((HERE/'CHOICES.json').read_text())
    assert choices['status'] == 'complete' and len(source) == len(choices['cases']) == 19
    out = dict(definitions={
        'purpose': 'Diagnostic comparison of known cases only; no proposed or tested classification rule.',
        'values': 'pawn90 knight300 bishop300 rook500 queen1000; these material units are not engine centipawns.',
        'baseline': 'Original pre-move material balance from mover perspective, including immediate capture credit.',
        'horizons': 'Root move is ply1. Report plies1,2,3,4,6,12 plus full saved PV; unavailable horizons are null.',
        'caveat': 'PV ledger is one predicted line, not forced material loss. Minima can be unreciprocated exchange steps. A nonterminal endpoint is truncated; terminal mate does not measure permanent material cost.',
        'acceptances': 'Previously saved conditional lines only; played move + acceptance + saved reply PV. Missing acceptance searches remain missing.',
        'comparison': 'Current and previous complete depth windows retained. Constrained/unrestricted searches have different contexts; do not treat small evaluation differences as exact opportunity costs.',
        'selection': 'All19 cases retained, including contradictions. No threshold, refit, global validation or rating analysis.'},
        input_sha256={str(SOURCE):sha(SOURCE),str(HERE/'CHOICES.json'):sha(HERE/'CHOICES.json')},
        script_sha256=sha(Path(__file__)), cases=[])
    count = 0
    for original, case in zip(source, choices['cases']):
        assert original['key'] == case['key']
        game = chess.pgn.read_game(io.StringIO(original['pgn']))
        assert not game.errors
        before = game.board()
        for move in list(game.mainline_moves())[:original['ply']-1]:
            before.push(move)
        assert before.fen() == original['fen_before']
        entry = dict(key=case['key'],group=case['group'],label=original['label'],
                     played_san=case['played_san'],initial_balance=balance(before,before.turn),
                     no_immediate_offer_roots=len(case['no_immediate_offer_roots']),
                     queries={},saved_acceptances=[],immediate_offer_accounts=[])
        after = before.copy(stack=True)
        played = chess.Move.from_uci(original['uci'])
        after.push(played)
        for uci, offer in original['offers'].items():
            capture = chess.Move.from_uci(uci)
            victim = after.piece_at(capture.to_square)
            account = dict(acceptance=after.san(capture),offered_piece=chess.piece_name(victim.piece_type),
                           offered_square=chess.square_name(capture.to_square),
                           offered_piece_is_moved_piece=capture.to_square==played.to_square,
                           static_exchange_net=offer['net'],
                           immediate_capture_credit=balance(after,before.turn)-balance(before,before.turn),
                           acceptance_ledger=ledger(before,[original['uci'],uci]),mate_witnesses=[])
            count += 1
            for reply in original['witnesses'].get(uci,{}).get('mate_replies',[]):
                witness=ledger(before,[original['uci'],uci,reply['uci']])
                assert witness['end_checkmate']
                account['mate_witnesses'].append(dict(reply=reply['san'],ledger=witness))
                count += 1
            entry['immediate_offer_accounts'].append(account)
        for name in ('unrestricted','no_immediate_offer_best','played_only'):
            query = case[name]
            entry['queries'][name] = dict(status=query['status'],windows={})
            for window in ('previous','current'):
                snap = query.get(window)
                if not snap:
                    continue
                lines=[]
                for line in snap['lines']:
                    count += 1
                    root=next(r for r in case['legal_roots'] if r['uci']==line['root_uci'])
                    lines.append(dict(root_san=line['root_san'],root_uci=line['root_uci'],
                                      is_played=line['root_uci']==case['played_uci'],
                                      score_mover=line['score_mover'],san=line['san'],
                                      qualifying_offers=root['qualifying_offers'],
                                      ledger=ledger(before,line['moves'],line['fen_after_each_ply'])))
                entry['queries'][name]['windows'][window]=dict(depth=snap['depth'],lines=lines)
        for acceptance in original['acceptances']:
            for window, lines in acceptance['windows'].items():
                for rank, line in enumerate(lines,1):
                    count += 1
                    entry['saved_acceptances'].append(dict(acceptance=acceptance['san'],window=window,rank=rank,
                        score_mover={k:line[k] for k in ('cp_mover','mate_mover') if k in line},
                        san=original['san']+' '+acceptance['san']+' '+line['san'],
                        ledger=ledger(before,[original['uci'],acceptance['uci']]+line['moves'])))
        out['cases'].append(entry)
    out['legally_replayed_lines']=count
    (HERE/'MATERIAL-LEDGERS.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(cases=len(out['cases']),legally_replayed_lines=count)))

if __name__ == '__main__':
    main()
