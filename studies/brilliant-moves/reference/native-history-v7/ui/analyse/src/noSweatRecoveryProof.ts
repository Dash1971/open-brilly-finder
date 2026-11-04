// Frozen existing-offer recovery guard, ported with Codex assistance.
// This is a bounded local material certificate, not a full tactical search.
import type { Chess } from 'chessops/chess';
import { makeSan } from 'chessops/san';
import type { Color, NormalMove } from 'chessops/types';
import { opposite, parseUci } from 'chessops/util';

import { legalMoves, position, standardUci } from './noSweatCore';
import type { Snapshot } from './noSweatSnapshots';

const values: Record<string, number> = {
  pawn: 90,
  knight: 300,
  bishop: 300,
  rook: 500,
  queen: 1000,
  king: 0,
};
class Exhausted extends Error {}
class Budget {
  nodes = 0;
  start = performance.now();
  tick(): void {
    if (++this.nodes > 100000 || performance.now() - this.start > 1000) throw new Exhausted();
  }
}
const physical = (p: Chess, color: Color): number => {
  let n = 0;
  for (const [, piece] of p.board) n += values[piece.role] * (piece.color === color ? 1 : -1);
  return n;
};
const captured = (p: Chess, m: NormalMove): number => {
  const victim = p.board.get(m.to);
  return victim && victim.color !== p.turn
    ? values[victim.role]
    : p.board.get(m.from)?.role === 'pawn' && m.to === p.epSquare
      ? 90
      : 0;
};
const gain = (p: Chess, m: NormalMove): number =>
  captured(p, m) + (m.promotion ? values[m.promotion] - 90 : 0);
const child = (p: Chess, m: NormalMove): Chess => {
  const q = p.clone();
  q.play(m);
  return q;
};

// Match the frozen Python probe's traversal locally; native legality is unchanged.
function probeMoves(p: Chess): NormalMove[] {
  const check = p.isCheck();
  const rank = (m: NormalMove): number[] => {
    const role = p.board.get(m.from)?.role;
    const ep = role === 'pawn' && m.to === p.epSquare && !p.board.has(m.to);
    const castle = role === 'king' && p.board.get(m.to)?.color === p.turn;
    const promotion = ['queen', 'rook', 'bishop', 'knight'].indexOf(m.promotion ?? '');
    if (ep) return [6, -m.from, -m.to, promotion];
    if (check && role === 'king') return [0, -m.from, -m.to, promotion];
    if (castle) return [2, -m.to, 0, promotion];
    if (role !== 'pawn') return [1, -m.from, -m.to, promotion];
    if (captured(p, m)) return [3, -m.from, -m.to, promotion];
    return [Math.abs(m.to - m.from) === 16 ? 5 : 4, -m.to, -m.from, promotion];
  };
  return legalMoves(p).sort((a, b) => {
    const x = rank(a),
      y = rank(b);
    for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] - y[i];
    return 0;
  });
}
function see(p: Chess, square: number, budget: Budget): number {
  budget.tick();
  let best = 0;
  for (const m of probeMoves(p))
    if (m.to === square && captured(p, m))
      best = Math.max(best, gain(p, m) - see(child(p, m), square, budget));
  return best;
}
function recovered(p: Chess, color: Color, baseline: number, budget: Budget): string[] | undefined {
  budget.tick();
  if (p.isEnd()) return;
  for (const m of probeMoves(p)) {
    if (!captured(p, m)) continue;
    const q = child(p, m);
    if (q.isEnd() || q.isCheck()) continue;
    if (physical(q, color) - see(q, m.to, budget) >= baseline - 100) return [makeSan(p, m)];
  }
  return undefined;
}
interface Response {
  quiet: string;
  all_legal_replies: number;
  witnesses: { reply: string; recoup: string[] }[];
}
function response(p: Chess, color: Color, baseline: number, budget: Budget): Response | undefined {
  const choices = probeMoves(p).filter(m => !captured(p, m) && !m.promotion);
  choices.sort((a, b) => {
    const check = Number(child(p, b).isCheck()) - Number(child(p, a).isCheck());
    const au = standardUci(p, a),
      bu = standardUci(p, b);
    return check || (au < bu ? -1 : au > bu ? 1 : 0);
  });
  for (const m of choices) {
    budget.tick();
    const q = child(p, m),
      replies = probeMoves(q);
    if (!replies.length) continue;
    const witnesses: Response['witnesses'] = [];
    for (const reply of replies) {
      budget.tick();
      const recoup = recovered(child(q, reply), color, baseline, budget);
      if (!recoup) break;
      witnesses.push({ reply: makeSan(q, reply), recoup });
    }
    if (witnesses.length === replies.length)
      return { quiet: makeSan(p, m), all_legal_replies: replies.length, witnesses };
  }
  return undefined;
}
interface Acceptance {
  acceptance: string;
  cost: number;
  response: Response | null;
}
export interface RecoveryProof {
  veto: boolean;
  status: string;
  nodes?: number;
  acceptances?: Acceptance[];
  roots?: string[];
  best_reply_roots?: string[];
  existing_acceptances?: string[];
}
export function existingOfferRecovery(
  beforeFen: string,
  afterFen: string,
  uci: string,
  currentAfter?: Snapshot,
  previousAfter?: Snapshot,
): RecoveryProof {
  const before = position(beforeFen),
    played = parseUci(uci);
  if (!played || !('from' in played) || !before.isLegal(played)) return { veto: false, status: 'ineligible' };
  if (before.isCheck() || !captured(before, played) || played.promotion || child(before, played).isCheck())
    return { veto: false, status: 'ineligible' };
  if (!currentAfter || !previousAfter) return { veto: false, status: 'missing-window' };
  const roots = [currentAfter, previousAfter].map(s => s.lines[0]?.moves[0]);
  if (roots.some(r => !r || !parseUci(r))) return { veto: false, status: 'missing-root' };
  const after = position(afterFen),
    color = before.turn,
    baseline = physical(before, color);
  const credit = Math.max(0, physical(after, color) - baseline),
    budget = new Budget();
  const staticBefore = before.clone();
  staticBefore.turn = opposite(color);
  staticBefore.epSquare = undefined;
  const accepted: string[] = [];
  try {
    for (const m of probeMoves(after)) {
      const piece = after.board.get(m.to);
      if (!captured(after, m) || !piece || piece.role === 'pawn' || piece.role === 'king') continue;
      const cost = gain(after, m) - see(child(after, m), m.to, budget);
      if (cost <= credit + 100) continue;
      if (m.to === played.to) return { veto: false, status: 'new-moved-offer' };
      const attacker = staticBefore.board.get(m.from),
        actualAttacker = after.board.get(m.from);
      const victim = staticBefore.board.get(m.to);
      if (
        !staticBefore.isLegal(m) ||
        attacker?.role !== actualAttacker?.role ||
        attacker?.color !== actualAttacker?.color ||
        victim?.role !== piece.role ||
        victim?.color !== piece.color
      )
        return { veto: false, status: 'new-capture-lane' };
      const oldCost = gain(staticBefore, m) - see(child(staticBefore, m), m.to, budget);
      if (oldCost !== cost) return { veto: false, status: 'changed-exchange-liability' };
      accepted.push(standardUci(after, m));
    }
    if (!accepted.length || roots.some(r => !accepted.includes(r)))
      return { veto: false, status: 'best-defense-declines-offer', roots };
    const acceptances: Acceptance[] = [];
    for (const m of probeMoves(after)) {
      const piece = after.board.get(m.to);
      if (!captured(after, m) || !piece || piece.role === 'pawn' || piece.role === 'king') continue;
      const q = child(after, m),
        cost = gain(after, m) - see(q, m.to, budget);
      if (cost <= credit + 100) continue;
      acceptances.push({
        acceptance: makeSan(after, m),
        cost,
        response: response(q, color, baseline, budget) ?? null,
      });
    }
    return {
      veto: !!acceptances.length && acceptances.every(a => a.response !== null),
      status: acceptances.length ? 'complete' : 'no-offer',
      nodes: budget.nodes,
      acceptances,
      best_reply_roots: roots,
      existing_acceptances: accepted,
    };
  } catch (e) {
    if (!(e instanceof Exhausted)) throw e;
    return { veto: false, status: 'unknown', nodes: budget.nodes };
  }
}
