// Maia3 encoding/vocabulary: CSSLab 1e13597c and Mobile Maia; see provenance.
import { Chess } from 'chessops/chess';
import { makeFen, parseFen } from 'chessops/fen';
import { makeSan } from 'chessops/san';
import type { Move, NormalMove } from 'chessops/types';
import { makeUci, parseUci } from 'chessops/util';
import { normalizeMove } from 'chessops/variant';

export const position = (fen: string): Chess => Chess.fromSetup(parseFen(fen).unwrap()).unwrap();
export function legalMoves(pos: Chess): NormalMove[] {
  const moves: NormalMove[] = [];
  const ctx = pos.ctx();
  for (const [from, tos] of pos.allDests(ctx))
    for (const to of tos) {
      const promotions =
        pos.board.get(from)?.role === 'pawn' && (to < 8 || to >= 56)
          ? (['queen', 'rook', 'bishop', 'knight'] as const)
          : [undefined];
      for (const promotion of promotions) moves.push({ from, to, promotion });
    }
  return moves;
}
export function standardUci(pos: Chess, move: Move): string {
  // Chessops represents castling as king-to-rook; Maia and standard UCI use c/g.
  if (
    'from' in move &&
    pos.board.get(move.from)?.role === 'king' &&
    pos.board.get(move.to)?.color === pos.turn
  ) {
    return makeUci({ ...move, to: move.from + (move.to > move.from ? 2 : -2) });
  }
  return makeUci(move);
}
export const legalUcis = (fen: string): string[] => {
  const pos = position(fen);
  return legalMoves(pos).map(m => standardUci(pos, m));
};
export const san = (fen: string, uci: string): string => {
  const pos = position(fen);
  const move = parseUci(uci);
  return move && pos.isLegal(move) ? makeSan(pos, move) : uci;
};
export function after(fen: string, uci: string): string {
  const pos = position(fen);
  const parsed = parseUci(uci);
  if (!parsed || !pos.isLegal(parsed)) throw new Error('Illegal candidate');
  pos.play(normalizeMove(pos, parsed));
  return makeFen(pos.toSetup());
}
export function policyIndex(uci: string, black: boolean): number {
  if (black) uci = uci[0] + (9 - Number(uci[1])) + uci[2] + (9 - Number(uci[3])) + uci.slice(4);
  const square = (f: string, rank: string) => f.charCodeAt(0) - 97 + (Number(rank) - 1) * 8;
  if (uci.length === 5)
    return 4096 + (uci.charCodeAt(0) - 97) * 32 + (uci.charCodeAt(2) - 97) * 4 + 'qrbn'.indexOf(uci[4]);
  return square(uci[0], uci[1]) * 64 + square(uci[2], uci[3]);
}
export interface Candidate {
  uci: string;
  probability: number;
}
export function policy(fen: string, logits: Float32Array): Candidate[] {
  if (logits.length !== 4352 || !logits.every(Number.isFinite)) throw new Error('Invalid Maia policy');
  const black = position(fen).turn === 'black';
  const moves = legalUcis(fen);
  const values = moves.map(m => logits[policyIndex(m, black)]);
  const max = Math.max(...values);
  const weights = values.map(x => Math.exp(x - max));
  const sum = weights.reduce((a, b) => a + b, 0);
  return moves
    .map((uci, i) => ({ uci, probability: weights[i] / sum }))
    .sort((a, b) => b.probability - a.probability);
}
export function encodeHistory(history: string[], enabled: boolean): Float32Array {
  const frames = enabled ? history.slice(-8) : history.slice(-1);
  if (!frames.length) throw new Error('Missing position history');
  while (frames.length < 8) frames.unshift(frames[0]);
  const tokens = new Float32Array(64 * 97);
  frames.forEach((fen, frame) => {
    const pos = position(fen);
    const black = pos.turn === 'black';
    for (const [square, piece] of pos.board) {
      const target = black ? square ^ 56 : square;
      const role = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king'].indexOf(piece.role);
      tokens[target * 97 + frame * 12 + role + (piece.color === pos.turn ? 0 : 6)] = 1;
    }
  });
  return tokens;
}
export function scoreText(score?: EvalScore): string {
  if (!score) return 'Unavailable';
  if (score.mate !== undefined) return score.mate === 0 ? 'Checkmate' : `#${score.mate}`;
  return score.cp === undefined ? 'Unavailable' : `${score.cp >= 0 ? '+' : ''}${(score.cp / 100).toFixed(2)}`;
}
export const terminalScore = (fen: string): EvalScore | undefined => {
  const pos = position(fen);
  if (!pos.isEnd()) return undefined;
  return pos.isCheckmate() ? { mate: pos.turn === 'white' ? -1 : 1 } : { cp: 0 };
};
