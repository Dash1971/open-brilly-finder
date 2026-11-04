// En Croissant v0.15.0 / Mobile Maia port. GPL-3.0; see analysis/PROVENANCE.md.
import type { Chess } from 'chessops/chess';
import type { NormalMove } from 'chessops/types';

import { after as afterMove, legalMoves, position } from './noSweatCore';
import type { Review } from './noSweatFish';
import type { Snapshot } from './noSweatSnapshots';

export type Annotation = '' | '??' | '?' | '?!' | '!!' | '!' | '!?';
export const winChance = (cp: number): number => 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * cp)) - 1);
export const normalized = (score: EvalScore, color: Color): number =>
  Math.max(
    -1000,
    Math.min(
      1000,
      (score.mate === undefined ? (score.cp ?? 0) : 1000 * Math.sign(score.mate)) *
        (color === 'white' ? 1 : -1),
    ),
  );
export const accuracy = (before: EvalScore, after: EvalScore, color: Color): number =>
  Math.max(
    0,
    Math.min(
      100,
      103.1668 *
        Math.exp(-0.04354 * (winChance(normalized(before, color)) - winChance(normalized(after, color)))) -
        3.1669 +
        1,
    ),
  );
export function annotation(
  previous: EvalScore | undefined,
  before: Snapshot,
  after: EvalScore,
  color: Color,
  move: string,
  sacrifice: boolean,
  beforeScore: EvalScore = before.lines[0],
): Annotation {
  const prev = normalized(beforeScore, color);
  const next = normalized(after, color);
  const loss = winChance(prev) - winChance(next);
  if (loss > 20) return '??';
  if (loss > 10) return '?';
  if (loss > 5) return '?!';
  if (before.lines.length > 1) {
    const best = normalized(before.lines[0], color);
    const second = normalized(before.lines[1], color);
    if (winChance(best) - winChance(second) > 10 && move === before.lines[0].moves[0]) {
      if (sacrifice) return '!!';
      if (winChance(best) - winChance(previous ? normalized(previous, color) : 0) > 5) return '!';
    } else if (sacrifice && next > -200) return '!?';
  }
  return '';
}
const pieceValue = (role: string): number =>
  (({ pawn: 90, knight: 300, bishop: 300, rook: 500, queen: 1000 }) as Record<string, number>)[role] ?? 0;
function material(pos: Chess): number {
  if (pos.isCheckmate()) return -10000;
  let score = 0;
  for (const [, piece] of pos.board) score += pieceValue(piece.role) * (piece.color === pos.turn ? 1 : -1);
  return score;
}
const capturedValue = (pos: Chess, move: NormalMove): number => {
  const piece = pos.board.get(move.to);
  if (piece && piece.color !== pos.turn) return pieceValue(piece.role);
  return pos.board.get(move.from)?.role === 'pawn' && move.to === pos.epSquare ? 90 : 0;
};
function qsearch(pos: Chess, alpha: number, beta: number): number {
  const stand = material(pos);
  if (stand >= beta) return beta;
  alpha = Math.max(alpha, stand);
  const captures = legalMoves(pos)
    .filter(m => capturedValue(pos, m) > 0)
    .sort((a, b) => capturedValue(pos, b) - capturedValue(pos, a));
  for (const move of captures) {
    const child = pos.clone();
    child.play(move);
    const score = -qsearch(child, -beta, -alpha);
    if (score >= beta) return beta;
    alpha = Math.max(alpha, score);
  }
  return alpha;
}
export function naiveMaterial(fen: string): number {
  const pos = position(fen);
  const moves = legalMoves(pos);
  if (!moves.length) return pos.isCheckmate() ? -10000 : 0;
  let best = -10000;
  for (const move of moves) {
    const child = pos.clone();
    child.play(move);
    best = Math.max(best, -qsearch(child, -10000, 10000));
  }
  return best || 0;
}
export const isSacrifice = (before: string, after: string, evaluateMaterial = naiveMaterial): boolean =>
  !position(after).isEnd() && evaluateMaterial(before) > -evaluateMaterial(after) + 100;

// Mute-only experiment. Keep annotation()/isSacrifice() above as the EC oracle.
export const muteBrilliantSource = 'mute-chess-brilliant-v3';
export const muteBrilliantRules = {
  maxLoss: 5,
  minimumCp: -100,
  routineWinCp: 600,
  minimumMaterialLoss: 100,
} as const;

// Static exchange on one square, with legal captures and either side free to
// stop. Quiet tactical compensation is deliberately left to Stockfish.
function exchangeGain(pos: Chess, target: number): number {
  let best = 0;
  for (const move of legalMoves(pos)) {
    if (move.to !== target || !capturedValue(pos, move)) continue;
    const gain = capturedValue(pos, move) + (move.promotion ? pieceValue(move.promotion) - 90 : 0);
    const child = pos.clone();
    child.play(move);
    best = Math.max(best, gain - exchangeGain(child, target));
  }
  return best;
}

export function hasPieceOffer(before: string, after: string): boolean {
  const pos = position(after);
  if (pos.isEnd()) return false;
  // Credit material already gained on this move, including promotion. Taking
  // a free rook while leaving a less valuable piece attacked is not a sacrifice.
  const credit = Math.max(0, -material(pos) - material(position(before)));
  for (const [square, piece] of pos.board)
    if (
      piece.color !== pos.turn &&
      piece.role !== 'pawn' &&
      piece.role !== 'king' &&
      exchangeGain(pos, square) > credit + muteBrilliantRules.minimumMaterialLoss
    )
      return true;
  return false;
}

// Mute awards require a concrete legal piece offer. The independent EC
// material probe can mistake foregone gains and quiet tactics for sacrifices.
export const isMuteSacrifice = hasPieceOffer;

export function muteAnnotation(
  previous: EvalScore | undefined,
  before: Snapshot,
  after: EvalScore,
  color: Color,
  move: string,
  ecSacrifice: boolean,
  sacrificeForMove: (uci: string) => boolean,
): Annotation {
  const original = annotation(previous, before, after, color, move, ecSacrifice);
  if (original === '??' || original === '?' || original === '?!') return original;
  const sacrifice = sacrificeForMove(move);
  // Both EC labels depend on a sacrifice. Do not retain an Interesting badge
  // when the same foregone-gain false positive has just failed the Mute test.
  if ((original === '!!' || original === '!?') && !sacrifice) return '';
  const next = normalized(after, color);
  const loss = winChance(normalized(before.lines[0], color)) - winChance(next);
  // A local offer can be an ordinary combination that recovers material on
  // another square. Require the existing broader material check as well.
  // Its mate sentinel is not physical material: a searched winning mate may
  // corroborate the offer instead. The whole-window check repeats this test.
  const corroborated = ecSacrifice || (after.mate !== undefined && next > 0);
  if (
    before.lines.length > 1 &&
    loss <= muteBrilliantRules.maxLoss &&
    next >= muteBrilliantRules.minimumCp &&
    sacrifice &&
    corroborated &&
    !before.lines.some(
      line =>
        line.moves[0] !== move &&
        normalized(line, color) >= muteBrilliantRules.routineWinCp &&
        normalized(before.lines[0], color) - normalized(line, color) <= 50 &&
        !sacrificeForMove(line.moves[0]),
    )
  )
    return '!!';
  // The soundness/relevance gates apply to old EC brilliants as well. All other
  // original labels retain their semantics; an EC sacrifice may stay Interesting.
  return original === '!!' ? (ecSacrifice && next > -200 ? '!?' : '') : original;
}

export interface ClassificationInput {
  positions: string[];
  reviews: Review[];
  move: string;
  confirmation?: Review[];
  policy?: 'en-croissant' | 'mute-brilliant-v3';
}
export interface ClassificationResult {
  symbol: Annotation;
  provisional?: Annotation;
  accuracy: number;
  cpLoss: number;
  withheld: boolean;
  version: string;
}
export function classify(input: ClassificationInput, evaluateMaterial = naiveMaterial): ClassificationResult {
  const { positions, reviews, move } = input;
  const n = reviews.length;
  if (n < 2 || positions.length !== n) throw new Error('Incomplete decision window');
  const before = reviews[n - 2];
  const after = reviews[n - 1];
  const previous = n > 2 ? reviews[n - 3] : undefined;
  const color = position(positions[n - 2]).turn;
  const sacrifice = isSacrifice(positions[n - 2], positions[n - 1], evaluateMaterial);
  const mute = input.policy === 'mute-brilliant-v3';
  const offers = new Map<string, boolean>();
  const sacrificeForMove = (uci: string): boolean => {
    if (!offers.has(uci))
      offers.set(
        uci,
        isMuteSacrifice(positions[n - 2], uci === move ? positions[n - 1] : afterMove(positions[n - 2], uci)),
      );
    return offers.get(uci)!;
  };
  const predicate = (b: Snapshot, a: Snapshot, p?: Snapshot): Annotation =>
    mute
      ? muteAnnotation(p?.lines[0], b, a.lines[0], color, move, sacrifice, sacrificeForMove)
      : annotation(p?.lines[0], b, a.lines[0], color, move, sacrifice);
  let symbol = predicate(before.current, after.current, previous?.current);
  const provisional = symbol;
  let withheld = false;
  if (symbol === '!!' || symbol === '!') {
    const needsPrevious = symbol === '!' && n > 2;
    const checked = input.confirmation;
    const previousBefore = checked ? checked[checked.length - 2]?.current : before.previous;
    const previousAfter = checked
      ? checked[checked.length - 1]?.current
      : after.terminal
        ? after.current
        : after.previous;
    const previousPrevious = checked ? checked[checked.length - 3]?.current : previous?.previous;
    const sufficient =
      before.quality === after.quality &&
      (!needsPrevious || previous?.quality === before.quality) &&
      (!checked ||
        checked.every((r, i) => {
          const original = reviews[reviews.length - checked.length + i];
          return (
            original &&
            r.quality === original.quality &&
            r.current.depth >= original.current.depth &&
            (!original.terminal ||
              JSON.stringify(r.current.lines[0]) === JSON.stringify(original.current.lines[0]))
          );
        }));
    if (
      !sufficient ||
      !previousBefore ||
      !previousAfter ||
      (needsPrevious && !previousPrevious) ||
      predicate(previousBefore, previousAfter, previousPrevious) !== symbol
    ) {
      symbol = '';
      withheld = true;
    }
  }

  return {
    symbol,
    provisional,
    withheld,
    accuracy: accuracy(before.current.lines[0], after.current.lines[0], color),
    cpLoss: Math.max(
      0,
      normalized(before.current.lines[0], color) - normalized(after.current.lines[0], color),
    ),
    version: mute ? muteBrilliantSource : 'ec015-mobilemaia-window-v2',
  };
}
