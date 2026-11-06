// Fixed research forest adapter. AI-assisted with Codex; native SF19 remains unvalidated.
// No runtime dependency on Classify: original rule helpers are injected by its caller.
import type { Chess } from 'chessops/chess';
import type { Color, NormalMove, Role } from 'chessops/types';
import { parseUci } from 'chessops/util';

import modelData from './noSweatBrilliantForestModel.json';
import { after as afterMove, legalMoves, position, standardUci } from './noSweatCore';
import type { Snapshot, ReviewLine } from './noSweatSnapshots';

type Value = number | boolean | null;
export type BrilliantForestFeatures = Record<string, Value>;
export interface BrilliantForestHelpers {
  rawOffer(before: string, after: string): boolean;
  ecMaterial(fen: string): number;
  isSacrifice(before: string, after: string): boolean;
  matingAcceptance(before: string, after: string): boolean;
  checkedContinuation(previous: string | undefined, before: string, after: string, move: string): boolean;
  phaseRelevant(before: string): boolean;
  normalized(score: ReviewLine, color: Color): number;
  winChance(cp: number): number;
}
export interface BrilliantForestReview {
  current?: Snapshot;
  previous?: Snapshot;
  terminal?: boolean;
  quality?: string;
}
export interface BrilliantForestInput {
  positions: readonly string[];
  reviews: readonly BrilliantForestReview[];
  move: string;
  confirmation?: readonly BrilliantForestReview[];
}
interface ForestNode {
  kind: string;
  feature_index?: number;
  threshold?: number;
  raw_p?: number;
  left?: ForestNode;
  right?: ForestNode;
}
const model = modelData as unknown as { features: string[]; trees: ForestNode[] };
const values: Record<Role, number> = { pawn: 90, knight: 300, bishop: 300, rook: 500, queen: 1000, king: 0 };
const promotionOrder: Partial<Record<Role, number>> = { queen: 0, rook: 1, bishop: 2, knight: 3 };
const physical = (p: Chess, color: Color): number => {
  let n = 0;
  for (const [, x] of p.board) n += values[x.role] * (x.color === color ? 1 : -1);
  return n;
};
const capture = (p: Chess, m: NormalMove): number => {
  const victim = p.board.get(m.to);
  return victim && victim.color !== p.turn
    ? values[victim.role]
    : p.board.get(m.from)?.role === 'pawn' && m.to === p.epSquare
      ? 90
      : 0;
};
const gain = (p: Chess, m: NormalMove): number =>
  capture(p, m) + (m.promotion ? values[m.promotion] - 90 : 0);
const isCastle = (p: Chess, m: NormalMove): boolean =>
  p.board.get(m.from)?.role === 'king' &&
  ((p.board.get(m.to)?.color === p.turn && p.board.get(m.to)?.role === 'rook') ||
    (Math.floor(m.from / 8) === Math.floor(m.to / 8) && Math.abs((m.from % 8) - (m.to % 8)) === 2));
// Local traversal order only; all legality remains with Chessops. Mirrors Python-chess
// non-pawns descending, castling, pawn captures, single/double pushes, en passant.
function probeMoves(p: Chess): NormalMove[] {
  const check = p.isCheck();
  const rank = (m: NormalMove): number => {
    const role = p.board.get(m.from)!.role;
    if (role !== 'pawn') return check && role === 'king' ? -1 : isCastle(p, m) ? 1 : 0;
    if (m.to === p.epSquare && !p.board.get(m.to)) return 5;
    return capture(p, m) ? 2 : Math.abs(m.to - m.from) === 8 ? 3 : 4;
  };
  return legalMoves(p).sort((a, b) => {
    const ra = rank(a);
    const rb = rank(b);
    if (ra !== rb) return ra - rb;
    if (ra === 3 || ra === 4) return b.to - a.to;
    return (
      b.from - a.from ||
      b.to - a.to ||
      (promotionOrder[a.promotion!] ?? 0) - (promotionOrder[b.promotion!] ?? 0)
    );
  });
}
class ProofTimeout extends Error {}
class Budget {
  nodes = 0;
  readonly start = performance.now();
  constructor(
    readonly cap: number,
    readonly milliseconds = Infinity,
  ) {}
  tick() {
    if (++this.nodes > this.cap || performance.now() - this.start >= this.milliseconds)
      throw new ProofTimeout();
  }
}
function exchange(p: Chess, square: number, b: Budget): number {
  b.tick();
  let best = 0;
  for (const m of probeMoves(p))
    if (m.to === square && capture(p, m)) {
      const child = p.clone();
      child.play(m);
      best = Math.max(best, gain(p, m) - exchange(child, square, b));
    }
  return best;
}
function hasOffer(before: Chess, after: Chess, b: Budget): boolean {
  b.tick();
  if (after.isEnd()) return false;
  const credit = Math.max(0, physical(after, before.turn) - physical(before, before.turn));
  for (const [s, piece] of Array.from(after.board).sort((a, b) => b[0] - a[0]))
    if (
      piece.color !== after.turn &&
      piece.role !== 'pawn' &&
      piece.role !== 'king' &&
      exchange(after, s, b) > credit + 100
    )
      return true;
  return false;
}
function avoidability(before: Chess): boolean | null {
  const budget = new Budget(512);
  try {
    for (const m of legalMoves(before).sort((a, b) =>
      standardUci(before, a).localeCompare(standardUci(before, b)),
    )) {
      const next = before.clone();
      next.play(m);
      if (!hasOffer(before, next, budget)) return true;
    }
    return false;
  } catch (e) {
    if (e instanceof ProofTimeout) return null;
    throw e;
  }
}
function stalemateAcceptance(before: Chess, after: Chess): { value: boolean | null; unknown: boolean } {
  const budget = new Budget(512);
  const credit = Math.max(0, physical(after, before.turn) - physical(before, before.turn));
  let found = false;
  try {
    for (const m of probeMoves(after)) {
      const victim = after.board.get(m.to);
      if (!victim || victim.role === 'pawn' || victim.role === 'king' || !capture(after, m)) continue;
      const next = after.clone();
      next.play(m);
      if (gain(after, m) - exchange(next, m.to, budget) <= credit + 100) continue;
      if (!next.isCheck() && !legalMoves(next).length) found = true;
    }
    return { value: found, unknown: false };
  } catch (e) {
    if (e instanceof ProofTimeout) return { value: null, unknown: true };
    throw e;
  }
}
class PhysicalBudget extends Budget {
  checked = 0;
  mates = 0;
  evasions = 0;
  constructor() {
    super(10000, 250);
  }
}
function physicalSearch(
  p: Chess,
  color: Color,
  depth: number,
  b: PhysicalBudget,
  alpha = -100000,
  beta = 100000,
): number {
  b.tick();
  const value = physical(p, color);
  const moves = probeMoves(p);
  if (!moves.length) {
    if (p.isCheck()) b.mates++;
    return value;
  }
  if (depth === 0) {
    if (p.isCheck()) b.checked++;
    return value;
  }
  const check = p.isCheck();
  const selected = check ? moves : moves.filter(m => capture(p, m) || m.promotion);
  if (check) b.evasions += selected.filter(m => !capture(p, m)).length;
  const maximize = p.turn === color;
  let best = check ? (maximize ? -100000 : 100000) : value;
  for (const m of selected) {
    const next = p.clone();
    next.play(m);
    const score = physicalSearch(next, color, depth - 1, b, alpha, beta);
    if (maximize ? score > best : score < best) best = score;
    if (maximize) alpha = Math.max(alpha, best);
    else beta = Math.min(beta, best);
    if (alpha >= beta) break;
  }
  return best;
}
interface Acceptance {
  square: number;
  net: number;
  debt: number;
}
function physicalProbe(before: Chess, after: Chess) {
  const color = before.turn;
  const base = physical(before, color);
  const credit = Math.max(0, physical(after, color) - base);
  const budget = new PhysicalBudget();
  const acceptances: Acceptance[] = [];
  let unknown = false;
  try {
    for (const m of probeMoves(after)) {
      const victim = after.board.get(m.to);
      if (!victim || victim.role === 'pawn' || victim.role === 'king' || !capture(after, m)) continue;
      const next = after.clone();
      next.play(m);
      const net = gain(after, m) - exchange(next, m.to, new Budget(100000, 1000));
      if (net <= credit + 100) continue;
      const outcome = physicalSearch(next, color, 3, budget);
      acceptances.push({ square: m.to, net, debt: base - outcome });
    }
  } catch (e) {
    if (e instanceof ProofTimeout) unknown = true;
    else throw e;
  }
  return {
    acceptances,
    unknown,
    credit,
    nodes: budget.nodes,
    checked: budget.checked > 0,
    mate: budget.mates > 0,
  };
}
const maximum = (xs: number[]): number | null => (xs.length ? Math.max(...xs) : null);
const minimum = (xs: number[]): number | null => (xs.length ? Math.min(...xs) : null);
const normalizedFeature = (line: ReviewLine | undefined, color: Color): number | null =>
  line
    ? line.mate !== undefined
      ? line.mate * (color === 'white' ? 1 : -1) > 0
        ? 1000
        : line.mate === 0
          ? 0
          : -1000
      : Math.max(-1000, Math.min(1000, line.cp! * (color === 'white' ? 1 : -1)))
    : null;
const logistic = (n: number): number => 100 / (1 + Math.exp(-0.00368208 * n));

export function evaluateBrilliantForest(input: BrilliantForestInput, h: BrilliantForestHelpers) {
  const n = input.positions.length;
  if (n < 2 || input.reviews.length !== n) throw new Error('Forest requires aligned before/after evidence');
  const beforeFen = input.positions[n - 2];
  const afterFen = input.positions[n - 1];
  const priorFen = n > 2 ? input.positions[n - 3] : undefined;
  const before = position(beforeFen);
  const after = position(afterFen);
  const prior = priorFen ? position(priorFen) : undefined;
  const move = parseUci(input.move);
  if (!move || !('from' in move)) throw new Error('Expected a standard move');
  const mover = before.board.get(move.from);
  if (!mover) throw new Error('Missing moving piece');
  const color = before.turn;
  const pp = physicalProbe(before, after);
  const offered = [...new Set(pp.acceptances.map(a => a.square))];
  const avoid = avoidability(before);
  const stalemate = stalemateAcceptance(before, after);
  const rawOffer = h.rawOffer(beforeFen, afterFen);
  const ec = h.isSacrifice(beforeFen, afterFen);
  const mateAcceptance = !ec && h.matingAcceptance(beforeFen, afterFen);
  const f: BrilliantForestFeatures = {
    raw_offer: rawOffer,
    ec_sacrifice: ec,
    mating_acceptance: mateAcceptance,
    checked_continuation: h.checkedContinuation(priorFen, beforeFen, afterFen, input.move),
    converted_material_or_endgame: h.phaseRelevant(beforeFen),
    move_capture: !!capture(before, move),
    move_check: after.isCheck(),
    move_in_check: before.isCheck(),
    move_castling: isCastle(before, move),
    move_en_passant: mover.role === 'pawn' && move.to === before.epSquare && !before.board.get(move.to),
    move_promotion: !!move.promotion,
    raw_material_before: physical(before, color),
    raw_material_after: physical(after, color),
    immediate_material_gain: physical(after, color) - physical(before, color),
    capture_promotion_credit: pp.credit,
    phase: Array.from(before.board).reduce(
      (sum, [, p]) => sum + { pawn: 0, knight: 1, bishop: 1, rook: 2, queen: 4, king: 0 }[p.role],
      0,
    ),
    ec_material_before: h.ecMaterial(beforeFen),
    ec_material_after: h.ecMaterial(afterFen),
    ec_material_margin: h.ecMaterial(beforeFen) + h.ecMaterial(afterFen) - 100,
    physical_unknown: pp.unknown,
    physical_checked_horizon: pp.checked,
    physical_mate_leaf: pp.mate,
    physical_debt3_max: pp.unknown ? null : maximum(pp.acceptances.map(a => a.debt)),
    physical_debt3_min: pp.unknown ? null : minimum(pp.acceptances.map(a => a.debt)),
    offer_exchange_gain_max: maximum(pp.acceptances.map(a => a.net)),
    offer_exchange_gain_min: minimum(pp.acceptances.map(a => a.net)),
    avoidability: avoid,
    avoidability_unknown: avoid === null,
    direct_stalemate_acceptance: stalemate.value,
    stalemate_probe_unknown: stalemate.unknown,
    attribution_unknown: false,
    prior_history_missing: !prior,
    offered_piece_moved: offered.includes(move.to),
    offered_piece_count: offered.length,
    already_vulnerable_same_square_count: null,
    prior_offer_gain_same_square_max: null,
    prior_offer_gain_original_square_max: null,
  };
  for (const role of ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king'] as Role[]) {
    const letter = role === 'knight' ? 'n' : role[0];
    f['moved_role_' + letter] = mover.role === role;
    f['offered_role_' + letter] = offered.some(s => after.board.get(s)?.role === role);
  }
  if (prior) {
    const budget = new Budget(512);
    const same: number[] = [];
    const original: number[] = [];
    let unmoved = 0;
    try {
      for (const square of offered) {
        const piece = after.board.get(square)!;
        let origin = square === move.to ? move.from : square;
        if (isCastle(before, move) && piece.role === 'rook' && [3, 5].includes(square % 8))
          origin = Math.floor(square / 8) * 8 + (square % 8 === 5 ? 7 : 0);
        const old = prior.board.get(square);
        const sameGain =
          old?.role === piece.role && old.color === piece.color ? exchange(prior, square, budget) : 0;
        same.push(sameGain);
        const originalPiece = prior.board.get(origin);
        original.push(
          originalPiece?.role === piece.role && originalPiece.color === piece.color
            ? exchange(prior, origin, budget)
            : 0,
        );
        if (square !== move.to && sameGain > 100) unmoved++;
      }
      f.already_vulnerable_same_square_count = unmoved;
      f.prior_offer_gain_same_square_max = maximum(same) ?? 0;
      f.prior_offer_gain_original_square_max = maximum(original) ?? 0;
    } catch (e) {
      if (e instanceof ProofTimeout) f.attribution_unknown = true;
      else throw e;
    }
  }
  const offerCache = new Map<string, boolean>();
  const isOffer = (uci: string): boolean => {
    if (!offerCache.has(uci))
      offerCache.set(uci, h.rawOffer(beforeFen, uci === input.move ? afterFen : afterMove(beforeFen, uci)));
    return offerCache.get(uci)!;
  };
  const makeWindow = (which: 'current' | 'previous') => {
    const checked = which === 'previous' ? input.confirmation : undefined;
    const b = checked ? checked[checked.length - 2]?.current : input.reviews[n - 2][which];
    const a = checked
      ? checked[checked.length - 1]?.current
      : which === 'previous' && input.reviews[n - 1].terminal
        ? input.reviews[n - 1].current
        : input.reviews[n - 1][which];
    const p = checked
      ? checked[checked.length - 3]?.current
      : n > 2
        ? input.reviews[n - 3][which]
        : undefined;
    const z: BrilliantForestFeatures = {
      ...f,
      window_complete: !!(b && a),
      before_depth: b?.depth ?? null,
      after_depth: a?.depth ?? null,
      prior_depth: p?.depth ?? null,
      before_roots: b?.lines.length ?? 0,
    };
    const best = b?.lines[0];
    const child = a?.lines[0];
    const old = p?.lines[0];
    const root = b?.lines.find(l => l.moves[0] === input.move);
    for (const [name, line] of [
      ['best', best],
      ['after', child],
      ['prior', old],
      ['played_root', root],
    ] as const) {
      z[name + '_cp'] = line?.cp === undefined ? null : line.cp * (color === 'white' ? 1 : -1);
      z[name + '_mate'] = line?.mate === undefined ? null : line.mate * (color === 'white' ? 1 : -1);
      z[name + '_mapped_score'] = normalizedFeature(line, color);
    }
    const complete = !!(best && child);
    const bestScore = best ? h.normalized(best, color) : null;
    const childScore = child ? h.normalized(child, color) : null;
    const priorScore = old ? h.normalized(old, color) : null;
    z.mapped_loss_pp = complete ? h.winChance(bestScore!) - h.winChance(childScore!) : null;
    z.same_root_loss_pp = root
      ? logistic(normalizedFeature(best, color)!) - logistic(normalizedFeature(root, color)!)
      : null;
    z.same_root_rank = root ? b!.lines.indexOf(root) + 1 : null;
    z.played_root_missing = !root;
    z.best_second_gap_pp =
      b && b.lines.length > 1
        ? logistic(normalizedFeature(best, color)!) - logistic(normalizedFeature(b.lines[1], color)!)
        : null;
    z.after_minus_prior_cp = complete && priorScore !== null ? childScore! - priorScore : null;
    z.best_minus_prior_cp = complete && priorScore !== null ? bestScore! - priorScore : null;
    const safe = complete
      ? b!.lines
          .filter(l => l.moves[0] !== input.move && h.normalized(l, color) >= 600 && !isOffer(l.moves[0]))
          .map(l => h.normalized(l, color))
      : [];
    z.winning_safe_alternatives = safe.length;
    z.safe_alternative_best_cp = maximum(safe);
    return {
      features: z,
      eligible:
        complete &&
        b!.lines.length > 1 &&
        rawOffer &&
        (z.mapped_loss_pp as number) <= 5 &&
        childScore! >= -100,
    };
  };
  const windows = { current: makeWindow('current'), previous: makeWindow('previous') };
  const confidenceSufficient =
    typeof input.reviews[n - 2].quality === 'string' &&
    !!input.reviews[n - 2].quality &&
    typeof input.reviews[n - 1].quality === 'string' &&
    !!input.reviews[n - 1].quality &&
    input.reviews[n - 2].quality === input.reviews[n - 1].quality &&
    (!input.confirmation ||
      input.confirmation.every((r, i) => {
        const original = input.reviews[n - input.confirmation!.length + i];
        return (
          !!original &&
          r.quality === original.quality &&
          !!r.current &&
          !!original.current &&
          r.current.depth >= original.current.depth &&
          (!original.terminal ||
            JSON.stringify(r.current.lines[0]) === JSON.stringify(original.current.lines[0]))
        );
      }));
  const scores = { current: 0, previous: 0 };
  for (const which of ['current', 'previous'] as const) {
    const features = windows[which].features;
    const vector = model.features.map(name =>
      name.endsWith('__missing') ? Number(features[name.slice(0, -9)] === null) : features[name],
    );
    if (vector.some(x => x === undefined)) throw new Error('Frozen forest predictor missing');
    if (vector.some(x => typeof x === 'number' && !Number.isFinite(x)))
      throw new Error('Nonfinite forest predictor');
    let total = 0;
    for (const tree of model.trees) {
      let node = tree;
      while (node.kind === 'split') {
        const v = vector[node.feature_index!];
        node = v === null || Number(v) <= node.threshold! ? node.left! : node.right!;
      }
      total += node.raw_p!;
    }
    scores[which] = total / model.trees.length;
  }
  const awarded =
    confidenceSufficient &&
    (['current', 'previous'] as const).every(w => windows[w].eligible && scores[w] >= 0.83);
  return {
    awarded,
    windowScores: scores,
    windows,
    confidenceSufficient,
    diagnostics: { physicalUnknown: pp.unknown, physicalNodes: pp.nodes },
  };
}
