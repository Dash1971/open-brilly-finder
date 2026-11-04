import type { Chess } from 'chessops/chess';
import type { NormalMove } from 'chessops/types';
import { legalMoves, position } from '../../../root/frozen-v4/noSweatCore';

const limit = 512;
const value = (role: string) => (( { pawn: 90, knight: 300, bishop: 300, rook: 500, queen: 1000 } as Record<string, number>)[role] ?? 0);
const physical = (pos: Chess) => {
  let total = 0;
  for (const [, piece] of pos.board) total += value(piece.role) * (piece.color === pos.turn ? 1 : -1);
  return total;
};
function spend(budget: { used: number }): void {
  if (++budget.used > limit) throw new Error('private-offer-proof-budget');
}
function captured(pos: Chess, move: NormalMove): number {
  const victim = pos.board.get(move.to);
  if (victim && victim.color !== pos.turn) return value(victim.role);
  return pos.board.get(move.from)?.role === 'pawn' && move.to === pos.epSquare ? 90 : 0;
}
function exchange(pos: Chess, target: number, budget: { used: number }): number {
  spend(budget);
  let best = 0;
  for (const move of legalMoves(pos)) {
    if (move.to !== target || !captured(pos, move)) continue;
    const child = pos.clone(); child.play(move);
    best = Math.max(best, captured(pos, move) + (move.promotion ? value(move.promotion) - 90 : 0) - exchange(child, target, budget));
  }
  return best;
}
function exhausted(error: unknown): boolean {
  return error instanceof Error && error.message === 'private-offer-proof-budget';
}
const square = (name: string) => name.charCodeAt(0) - 97 + (Number(name[1]) - 1) * 8;
// Standard UCI is the existing caller contract. A castling rook also counts as moved.
function movedVictim(before: Chess, target: number, uci: string): boolean {
  const from = square(uci.slice(0, 2)), to = square(uci.slice(2, 4));
  if (target === to) return true;
  if (before.board.get(from)?.role !== 'king' || Math.abs(to - from) !== 2) return false;
  const rookFrom = (from & ~7) + (to > from ? 7 : 0);
  const rookTo = (from & ~7) + (to > from ? 5 : 3);
  return target === rookTo && before.board.get(rookFrom)?.role === 'rook';
}

// Same qualifying acceptance supplies the cost, attribution, and literal mate witness.
// An unmoved victim needs real aligned history. Old maximum raw exchange loss must
// be strictly below THIS acceptance's net loss, or THIS capture was not legal then.
export function hasAttributableMatingAcceptance(previousFen: string | undefined,
  beforeFen: string, afterFen: string, uci: string): boolean {
  const before = position(beforeFen), pos = position(afterFen);
  if (pos.isEnd()) return false;
  const old = previousFen ? position(previousFen) : undefined;
  const credit = Math.max(0, -physical(pos) - physical(before));
  const budget = { used: 0 };
  try {
    for (const capture of legalMoves(pos)) {
      const victim = pos.board.get(capture.to);
      if (!victim || victim.color === pos.turn || victim.role === 'pawn' || victim.role === 'king') continue;
      const child = pos.clone(); child.play(capture);
      const net = captured(pos, capture) + (capture.promotion ? value(capture.promotion) - 90 : 0) - exchange(child, capture.to, budget);
      if (net <= credit + 100) continue;
      if (!movedVictim(before, capture.to, uci)) {
        if (!old || old.turn !== pos.turn) continue;
        const priorVictim = old.board.get(capture.to);
        if (!priorVictim || priorVictim.color !== victim.color || priorVictim.role !== victim.role) continue;
        const priorGain = exchange(old, capture.to, budget);
        if (!(priorGain < net || !old.isLegal(capture))) continue;
      }
      for (const reply of legalMoves(child)) {
        spend(budget);
        const end = child.clone(); end.play(reply);
        if (end.isCheckmate()) return true;
      }
    }
  } catch (error) { if (!exhausted(error)) throw error; }
  return false;
}
function boundedHasOffer(before: Chess, after: Chess, budget: { used: number }): boolean {
  spend(budget);
  if (after.isEnd()) return false;
  const credit = Math.max(0, -physical(after) - physical(before));
  for (const [target, victim] of after.board)
    if (victim.color !== after.turn && victim.role !== 'pawn' && victim.role !== 'king' &&
      exchange(after, target, budget) > credit + 100) return true;
  return false;
}
// True is a complete no-escape proof; undefined is exhaustion, never a veto.
export function noNonOfferingEscape(beforeFen: string): boolean | undefined {
  const before = position(beforeFen), budget = { used: 0 };
  try {
    for (const move of legalMoves(before)) {
      const after = before.clone(); after.play(move);
      if (!boundedHasOffer(before, after, budget)) return false;
    }
    return true;
  } catch (error) { if (!exhausted(error)) throw error; }
  return undefined;
}
export function hasDirectStalemateAcceptance(beforeFen: string, afterFen: string): boolean {
  const before = position(beforeFen), pos = position(afterFen), budget = { used: 0 };
  if (pos.isEnd()) return false;
  const credit = Math.max(0, -physical(pos) - physical(before));
  try {
    for (const capture of legalMoves(pos)) {
      const victim = pos.board.get(capture.to);
      if (!victim || victim.color === pos.turn || victim.role === 'pawn' || victim.role === 'king') continue;
      const child = pos.clone(); child.play(capture);
      const net = captured(pos, capture) + (capture.promotion ? value(capture.promotion) - 90 : 0) - exchange(child, capture.to, budget);
      if (net > credit + 100 && !child.isCheck() && legalMoves(child).length === 0) return true;
    }
  } catch (error) { if (!exhausted(error)) throw error; }
  return false;
}

export interface AttributedOfferDecision {
  attributed: boolean;
  quietCorroboration: boolean;
  matingAcceptance: boolean;
  exhausted: boolean;
}
// A completed qualifying acceptance is the unit of evidence: attribution,
// quiet-investment value, and any mate witness all refer to its victim.
// Exhaustion retains completed existential proofs, never invents a missing one.
export function attributedOfferDecision(previousFen: string | undefined,
  beforeFen: string, afterFen: string, uci: string, ecCorroborated: boolean): AttributedOfferDecision {
  const result: AttributedOfferDecision = { attributed: false, quietCorroboration: false, matingAcceptance: false, exhausted: false };
  const before = position(beforeFen), pos = position(afterFen);
  if (pos.isEnd()) return result;
  const old = previousFen ? position(previousFen) : undefined;
  const from = square(uci.slice(0, 2)), to = square(uci.slice(2, 4));
  const moving = before.board.get(from);
  if (!moving) return result;
  const capturedPiece = before.board.get(to);
  const capture = (capturedPiece && capturedPiece.color !== before.turn) ||
    (moving.role === 'pawn' && to === before.epSquare);
  const quiet = !capture && uci.length === 4;
  const credit = Math.max(0, -physical(pos) - physical(before));
  const budget = { used: 0 };
  try {
    for (const acceptance of legalMoves(pos)) {
      const victim = pos.board.get(acceptance.to);
      if (!victim || victim.color === pos.turn || victim.role === 'pawn' || victim.role === 'king') continue;
      const child = pos.clone(); child.play(acceptance);
      const net = captured(pos, acceptance) + (acceptance.promotion ? value(acceptance.promotion) - 90 : 0) - exchange(child, acceptance.to, budget);
      if (net <= credit + 100) continue;
      const moved = movedVictim(before, acceptance.to, uci);
      if (!moved) {
        if (!old || old.turn !== pos.turn) continue;
        const prior = old.board.get(acceptance.to);
        if (!prior || prior.role !== victim.role || prior.color !== victim.color) continue;
        const priorGain = exchange(old, acceptance.to, budget);
        if (!(priorGain < net || !old.isLegal(acceptance))) continue;
      }
      result.attributed = true;
      result.quietCorroboration ||= quiet && (moved || value(victim.role) >= value(moving.role));
      // Further evidence cannot change this decision; avoid extra board work.
      if (ecCorroborated || result.quietCorroboration) return result;
      for (const reply of legalMoves(child)) {
        spend(budget);
        const end = child.clone(); end.play(reply);
        if (end.isCheckmate()) { result.matingAcceptance = true; return result; }
      }
    }
  } catch (error) {
    if (!exhausted(error)) throw error;
    result.exhausted = true;
  }
  return result;
}
