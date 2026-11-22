// Mute Exchange (mute-brilliant-v8): Chess.com-style Brilliant detection.
// A move is a candidate when it leaves a knight, bishop, rook or queen capturable for a
// static-exchange gain of two or more. A gradient-boosted tree model trained on Chess.com
// Game Review labels then scores the candidate from board facts and the review window's
// existing engine lines. Features mirror the open reference implementation exactly; see
// https://github.com/Dash1971/open-brilly-finder (studies/brilliant-exchange-2026-11-22).
import { attacks } from 'chessops/attacks';
import { Chess } from 'chessops/chess';
import { makeBoardFen, parseFen } from 'chessops/fen';
import { SquareSet } from 'chessops/squareSet';
import type { Color, NormalMove, Role, Square } from 'chessops/types';
import { opposite, parseSquare } from 'chessops/util';

import model from './noSweatBrilliantExchangeModel.json';

export const exchangeModel = model as unknown as {
  name: string;
  features: string[];
  baseline: number;
  cutoff: number;
  trees: { f: number[]; t: number[]; l: number[]; r: number[]; v: number[]; leaf: number[] }[];
};

const VAL: Record<Role, number> = { pawn: 1, knight: 3, bishop: 3, rook: 5, queen: 9, king: 100 };
const TYPE: Record<Role, number> = { pawn: 1, knight: 2, bishop: 3, rook: 4, queen: 5, king: 6 };
const PROMOTIONS: Role[] = ['queen', 'rook', 'bishop', 'knight'];

const fromFen = (fen: string): Chess => Chess.fromSetup(parseFen(fen).unwrap()).unwrap();
const descending = (set: SquareSet): Square[] => {
  const out: Square[] = [];
  for (let sq = 63; sq >= 0; sq--) if (set.has(sq)) out.push(sq);
  return out;
};

interface PyMove {
  move: NormalMove; // as chessops plays it (castling is king-takes-rook)
  from: Square;
  to: Square; // standard target square (castling: king destination)
  role: Role;
  capture: boolean; // includes en passant
  ep: boolean;
  castle: boolean;
}

// Legal moves in the order python-chess generates them. Only the relative order of
// captures matters for parity: checked-king moves first, then pieces from the highest
// square down (targets highest first), then pawn captures, then pawn pushes, then en passant.
function pyMoves(pos: Chess): PyMove[] {
  const ctx = pos.ctx();
  const us = pos.turn;
  const out: PyMove[] = [];
  const pawnsLater: PyMove[] = [];
  const eps: PyMove[] = [];
  const push = (from: Square, to: Square, role: Role, list: PyMove[]) => {
    const target = pos.board.get(to);
    const castle = role === 'king' && target?.color === us;
    const ep = role === 'pawn' && to === pos.epSquare && !target && (from & 7) !== (to & 7);
    const capture = ep || (!!target && target.color !== us);
    const std = castle ? from + (to > from ? 2 : -2) : to;
    if (role === 'pawn' && (to < 8 || to >= 56))
      for (const promotion of PROMOTIONS)
        list.push({ move: { from, to, promotion }, from, to: std, role, capture, ep, castle });
    else (ep ? eps : list).push({ move: { from, to }, from, to: std, role, capture, ep, castle });
  };
  const pieces = (includeKing: boolean) => {
    for (const from of descending(pos.board[us].diff(pos.board.pawn))) {
      const role = pos.board.getRole(from)!;
      if (role === 'king' && !includeKing) continue;
      const dests = descending(pos.dests(from, ctx));
      const castles: PyMove[] = [];
      for (const to of dests) {
        if (role === 'king' && pos.board.get(to)?.color === us) push(from, to, role, castles);
        else push(from, to, role, out);
      }
      out.push(...castles);
    }
  };
  if (pos.isCheck()) {
    const king = pos.board.kingOf(us)!;
    for (const to of descending(pos.dests(king, ctx))) push(king, to, 'king', out);
    pieces(false);
  } else pieces(true);
  for (const from of descending(pos.board[us].intersect(pos.board.pawn))) {
    for (const to of descending(pos.dests(from, ctx))) {
      const target = pos.board.get(to);
      const ep = to === pos.epSquare && !target && (from & 7) !== (to & 7);
      if (target || ep) push(from, to, 'pawn', out);
      else push(from, to, 'pawn', pawnsLater);
    }
  }
  return [...out, ...pawnsLater, ...eps];
}

const played = (pos: Chess, m: PyMove): Chess => {
  const next = pos.clone();
  next.play(m.move);
  return next;
};
const gainOf = (pos: Chess, m: PyMove): number => {
  const victim = pos.board.get(m.to);
  let gain = !m.castle && victim ? VAL[victim.role] : m.ep ? 1 : 0;
  if (m.move.promotion) gain += VAL[m.move.promotion] - 1;
  return gain;
};

// Static exchange with full legality: the side to move may always decline to continue.
function seeAfter(pos: Chess, sq: Square): number {
  if (!pos.board.get(sq)) return 0;
  let best: PyMove | undefined;
  for (const m of pyMoves(pos))
    if (!m.castle && !m.ep && m.to === sq && (!best || VAL[m.role] < VAL[best.role])) best = m;
  return best ? Math.max(0, seeCapture(pos, best)) : 0;
}
function seeCapture(pos: Chess, m: PyMove): number {
  const gain = gainOf(pos, m);
  const next = played(pos, m);
  if (next.isCheckmate()) return gain;
  return gain - seeAfter(next, m.to);
}

type Offer = [sq: Square, type: number, attacker: number, gain: number];
// Captures the side to move has against `color`'s non-pawn pieces, best capture per victim.
function offers(pos: Chess, color: Color): Offer[] {
  const out = new Map<Square, Offer>();
  for (const m of pyMoves(pos)) {
    if (m.castle) continue;
    const t = pos.board.get(m.to);
    if (!t || t.color !== color || t.role === 'pawn') continue;
    const g = seeCapture(pos, m);
    const cur = out.get(m.to);
    if (!cur || g > cur[3]) {
      if (cur) cur.splice(0, 4, m.to, TYPE[t.role], TYPE[m.role], g);
      else out.set(m.to, [m.to, TYPE[t.role], TYPE[m.role], g]);
    }
  }
  return [...out.values()];
}
const material = (pos: Chess, color: Color): number =>
  (['pawn', 'knight', 'bishop', 'rook', 'queen'] as Role[]).reduce(
    (sum, role) => sum + VAL[role] * pos.board.pieces(color, role).size(),
    0,
  );
function bestCapture(pos: Chess): [number, PyMove | undefined] {
  let best: [number, PyMove | undefined] = [0, undefined];
  for (const m of pyMoves(pos)) {
    if (!m.capture) continue;
    const g = seeCapture(pos, m);
    if (g > best[0]) best = [g, m];
  }
  return best;
}
const mateInOne = (pos: Chess): boolean => pyMoves(pos).some(m => played(pos, m).isCheckmate());
const maxOr = (values: number[], fallback: number): number =>
  values.length ? Math.max(...values) : fallback;

// The same position with the other side to move (no en passant), or undefined if illegal.
function passed(pos: Chess): Chess | undefined {
  const setup = pos.toSetup();
  setup.turn = opposite(pos.turn);
  setup.epSquare = undefined;
  const result = Chess.fromSetup(setup);
  return result.isOk ? result.value : undefined;
}
const attackers = (pos: Chess, sq: Square, by: Color): SquareSet =>
  pos.kingAttackers(sq, by, pos.board.occupied);

// Capture-only material search: what the side to move can win by force through captures.
function qs(pos: Chess, depth: number, alpha: number, beta: number): number {
  const inCheck = pos.isCheck();
  if (depth === 0) return 0;
  let best = inCheck ? -99 : 0;
  if (best >= beta) return best;
  alpha = Math.max(alpha, best);
  const all = pyMoves(pos);
  const moves = inCheck ? all : all.filter(m => m.capture || m.move.promotion);
  if (inCheck && !moves.length) return -99;
  const scored = moves.map(m => ({ m, g: gainOf(pos, m) })).sort((a, b) => b.g - a.g);
  for (const { m, g } of scored) {
    const v = g - qs(played(pos, m), depth - 1, -beta + g, -alpha + g);
    if (v > best) {
      best = v;
      if (v > alpha) alpha = v;
      if (alpha >= beta) break;
    }
  }
  return best;
}
const clamp30 = (v: number): number => Math.max(-30, Math.min(30, v));
const winChance = (cp: number): number => 100 / (1 + Math.exp(-0.00368208 * cp));
const distance = (a: Square, b: Square): number =>
  Math.max(Math.abs((a & 7) - (b & 7)), Math.abs((a >> 3) - (b >> 3)));

export interface ExchangeLine {
  uci: string;
  cp: number; // from the mover's side, see lineCp
}
export interface ExchangeEvidence {
  before: ExchangeLine[]; // up to two root lines for the position before the move
  after: { cp: number; reply?: string }; // best line for the position after the move
}
// Engine score from the mover's side: centipawns clipped to +-9000, mates beyond that.
export function lineCp(score: { cp?: number; mate?: number }, mover: Color): number {
  const pov = mover === 'white' ? 1 : -1;
  if (score.mate !== undefined) {
    const mate = score.mate * pov;
    if (mate === 0) return -10000;
    return (10000 - Math.min(Math.abs(mate), 99) * 10) * Math.sign(mate);
  }
  return Math.max(-9000, Math.min(9000, (score.cp ?? 0) * pov));
}

function findMove(moves: PyMove[], uci: string): PyMove | undefined {
  const from = parseSquare(uci.slice(0, 2));
  const to = parseSquare(uci.slice(2, 4));
  const promotion =
    uci.length > 4
      ? ({ q: 'queen', r: 'rook', b: 'bishop', n: 'knight' } as const)[uci[4] as 'q']
      : undefined;
  return moves.find(m => m.from === from && m.to === to && m.move.promotion === promotion);
}

// Returns undefined when the move is not a sacrifice candidate.
export function exchangeFeatures(
  fenPrev: string | undefined,
  fenBefore: string,
  uci: string,
  evidence: ExchangeEvidence,
): Record<string, number> | undefined {
  const before = fromFen(fenBefore);
  const mover = before.turn;
  const them = opposite(mover);
  const beforeMoves = pyMoves(before);
  const move = findMove(beforeMoves, uci);
  if (!move) return undefined;

  // What the opponent's last move was (matched by resulting placement).
  let prev: Chess | undefined;
  let oppMove: PyMove | undefined;
  let oppCap = 0;
  if (fenPrev) {
    prev = fromFen(fenPrev);
    const target = makeBoardFen(before.board);
    for (const m of pyMoves(prev)) {
      if (makeBoardFen(played(prev, m).board) !== target) continue;
      const victim = prev.board.get(m.to);
      oppCap = !m.castle && victim ? VAL[victim.role] : m.ep ? 1 : 0;
      oppMove = m;
      break;
    }
  }

  const capPiece = before.board.get(move.to);
  const capVal = !move.castle && capPiece ? VAL[capPiece.role] : move.ep ? 1 : 0;
  const inCheck = before.isCheck();
  const beforePassed = inCheck ? undefined : passed(before);
  const beforeOffers = beforePassed ? offers(beforePassed, mover) : undefined;
  const after = played(before, move);
  const mate = after.isCheckmate();
  const offered = mate ? [] : offers(after, mover);
  if (!offered.some(o => o[3] >= 2)) return undefined;

  const hang = offered.filter(o => o[3] > 0);
  let top = hang[0];
  for (const o of hang) if (o[3] > top[3] || (o[3] === top[3] && o[1] > top[1])) top = o;
  const sq = top[0];
  const bo = new Map((beforeOffers ?? []).map(o => [o[0], o]));
  const f: Record<string, number> = {};
  const matOwn = material(before, mover);
  const matOpp = material(before, them);
  const afterMoves = pyMoves(after);

  // --- the offer itself
  f.net = capVal - top[3];
  f.hang_see = top[3];
  f.hang_type = top[1];
  f.hang_attacker = top[2];
  f.hang_is_moved = +(sq === move.to);
  f.hang_already_attacked = +(sq !== move.to && bo.has(sq));
  f.hang_already_hanging = +(sq !== move.to && bo.has(sq) && bo.get(sq)![3] > 0);
  f.before_hang_max = beforeOffers
    ? maxOr(
        beforeOffers.map(o => o[3]),
        0,
      )
    : -1;
  f.n_hang = hang.length;
  f.hang_sum = hang.reduce((s, o) => s + o[3], 0);
  f.n_capturable = offered.length;
  f.moved_type = TYPE[move.role];
  f.cap_val = capVal;
  f.gives_check = +after.isCheck();
  f.in_check = +inCheck;
  f.promo = move.move.promotion ? TYPE[move.move.promotion] : 0;
  f.matdiff = matOwn - matOpp;
  f.mat_total = matOwn + matOpp;
  f.mat_own = matOwn;
  f.opp_prev_cap = oppCap;
  f.recapture = +(!!oppMove && oppMove.to === move.to && capVal > 0);
  f.n_legal = beforeMoves.length;
  f.n_replies = afterMoves.length;

  // --- could the mover have kept material instead?
  const altNets = new Map<string, number>();
  const keyOf = (m: PyMove) => `${m.from}-${m.to}-${m.move.promotion ?? ''}`;
  for (const m of beforeMoves) {
    if (m === move) continue;
    const victim = before.board.get(m.to);
    const cv = !m.castle && victim ? VAL[victim.role] : m.ep ? 1 : 0;
    const next = played(before, m);
    altNets.set(
      keyOf(m),
      next.isCheckmate()
        ? 99
        : cv -
            maxOr(
              offers(next, mover).map(o => o[3]),
              0,
            ),
    );
  }
  const alt = [...altNets.values()];
  f.alt_best_net = maxOr(alt, -99);
  f.alt_safe_frac = alt.length ? alt.filter(v => v >= 0).length / alt.length : 0;
  f.alt_n_better_net = alt.filter(v => v > f.net).length;

  // --- static tactics around the offered piece
  f.hang_n_attackers = attackers(after, sq, them).size();
  f.hang_n_defenders = attackers(after, sq, mover).size();
  f.hang_see_before = bo.has(sq) ? bo.get(sq)![3] : sq !== move.to ? 0 : -1;
  f.hang_worsened = +(sq !== move.to && top[3] > (bo.has(sq) ? bo.get(sq)![3] : 0));
  f.from_hang = bo.has(move.from) ? bo.get(move.from)![3] : 0;
  f.moved_safe = +!offered.some(o => o[0] === move.to && o[3] > 0);
  let escape = 0;
  if (sq !== move.to)
    for (const m of beforeMoves) {
      if (m.from !== sq) continue;
      const victim = before.board.get(m.to);
      const cv = !m.castle && victim ? VAL[victim.role] : 0;
      const lost = maxOr(
        offers(played(before, m), mover)
          .filter(o => o[0] === m.to)
          .map(o => o[3]),
        0,
      );
      if (cv - lost >= 0) {
        escape = 1;
        break;
      }
    }
  f.hang_could_escape = escape;
  let threatGain = 0;
  let threatMove: PyMove | undefined;
  let threatMate = 0;
  if (!after.isCheck()) {
    const free = passed(after);
    if (free) {
      [threatGain, threatMove] = bestCapture(free);
      threatMate = +mateInOne(free);
    }
  }
  f.threat_gain = threatGain;
  f.threat_mate1 = threatMate;
  f.threat_by_moved = +(!!threatMove && threatMove.from === move.to);
  f.threat_minus_hang = threatGain - top[3];
  f.pre_capture_gain = bestCapture(before)[0];

  const victimValue = VAL[after.board.get(sq)!.role];
  const accepts = afterMoves.filter(m => !m.castle && !m.ep && m.to === sq && seeCapture(after, m) > 0);
  f.n_accepting = accepts.length;
  f.accept_by_king_only = +(accepts.length > 0 && accepts.every(m => m.role === 'king'));
  const outcomes: { net2: number; regain: number; same: number; pre: number; mate1: number; chk: number }[] =
    [];
  for (const m of accepts) {
    const next = played(after, m);
    if (next.isCheckmate()) continue;
    const [g, bm] = bestCapture(next);
    outcomes.push({
      net2: capVal - victimValue + g,
      regain: g,
      same: +(!!bm && bm.to === sq),
      pre: +(!!bm && !!threatMove && bm.to === threatMove.to && bm.to !== sq),
      mate1: +mateInOne(next),
      chk: +pyMoves(next).some(x => played(next, x).isCheck()),
    });
  }
  if (outcomes.length) {
    let worst = outcomes[0];
    for (const o of outcomes) if (o.net2 < worst.net2) worst = o;
    f.acc_net2_min = worst.net2;
    f.acc_net2_max = Math.max(...outcomes.map(o => o.net2));
    f.acc_regain = worst.regain;
    f.acc_regain_same_sq = worst.same;
    f.acc_regain_pre_threat = worst.pre;
    f.acc_mate1_any = Math.max(...outcomes.map(o => o.mate1));
    f.acc_mate1_all = Math.min(...outcomes.map(o => o.mate1));
    f.acc_check_avail = worst.chk;
  } else
    for (const k of [
      'acc_net2_min',
      'acc_net2_max',
      'acc_regain',
      'acc_regain_same_sq',
      'acc_regain_pre_threat',
      'acc_mate1_any',
      'acc_mate1_all',
      'acc_check_avail',
    ])
      f[k] = -9;
  const hangSquares = new Set(hang.map(o => o[0]));
  f.opp_other_gain = maxOr(
    afterMoves.filter(m => m.capture && !hangSquares.has(m.to)).map(m => seeCapture(after, m)),
    0,
  );
  const movedPiece = after.board.get(move.to)!;
  let attacksHigher = 0;
  for (const t of attacks(movedPiece, move.to, after.board.occupied)) {
    const p = after.board.get(t);
    if (p && p.color !== mover && p.role !== 'king' && VAL[p.role] > VAL[movedPiece.role]) attacksHigher = 1;
  }
  f.moved_attacks_higher = attacksHigher;
  const theirKing = after.board.kingOf(them);
  f.king_zone_att = 0;
  if (theirKing !== undefined) {
    const zone = attacks({ role: 'king', color: them }, theirKing, SquareSet.empty()).with(theirKing);
    for (const z of zone) if (attackers(after, z, mover).nonEmpty()) f.king_zone_att++;
    f.hang_dist_opp_king = distance(sq, theirKing);
    f.to_dist_opp_king = distance(move.to, theirKing);
  } else f.hang_dist_opp_king = f.to_dist_opp_king = 9;

  // --- capture-only material search
  for (const d of [2, 4, 6, 10]) f[`qs_net${d}`] = clamp30(capVal - qs(after, d, -200, 200));
  f.qs_before6 = beforePassed ? clamp30(-qs(beforePassed, 6, -200, 200)) : 0;
  f.qs_delta6 = f.qs_net6 - f.qs_before6;
  f.qs_own_before6 = clamp30(qs(before, 6, -200, 200));

  // --- was the offer already standing, and what did the opponent just do?
  Object.assign(f, {
    has_prev: 0,
    hang_age: 0,
    prev_hang_max: -1,
    prev_n_hang: 0,
    origin_offered_prev: 0,
    origin_offered_prev_see: 0,
    prev_gives_check: 0,
    hang_see_prev: 0,
    hung_was_there_prev: -1,
    opp_last_attacks_hung: -1,
    opp_last_cap: -1,
    opp_last_piece: 0,
    opp_last_to_hung_sq: 0,
    opp_last_attacks_origin: -1,
    opp_last_see_loss: 0,
    opp_last_discovers_hung: -1,
  });
  if (prev && oppMove) {
    const po = offers(prev, mover);
    f.has_prev = 1;
    f.prev_hang_max = maxOr(
      po.map(o => o[3]),
      0,
    );
    f.prev_n_hang = po.filter(o => o[3] > 0).length;
    f.hang_age = +(sq !== move.to && po.some(o => o[0] === sq && o[1] === top[1] && o[3] > 0));
    f.origin_offered_prev = +po.some(o => o[0] === move.from && o[3] > 0);
    f.origin_offered_prev_see = maxOr(
      po.filter(o => o[0] === move.from).map(o => o[3]),
      0,
    );
    f.prev_gives_check = +prev.isCheck();
    f.hang_see_prev = maxOr(
      po.filter(o => o[0] === sq && o[1] === top[1]).map(o => o[3]),
      0,
    );
    const there = prev.board.get(sq);
    f.hung_was_there_prev = +(!!there && there.color === mover && TYPE[there.role] === top[1]);
    f.opp_last_piece = TYPE[oppMove.role];
    f.opp_last_cap = oppCap;
    const attBefore = attackers(prev, sq, them);
    const afterOpp = played(prev, oppMove);
    const attAfter = attackers(afterOpp, sq, them);
    f.opp_last_attacks_hung = +attAfter.has(oppMove.to);
    f.opp_last_discovers_hung = +attAfter.diff(attBefore).without(oppMove.to).nonEmpty();
    f.opp_last_attacks_origin = +attackers(afterOpp, move.from, them).has(oppMove.to);
    f.opp_last_to_hung_sq = +(oppMove.to === sq);
    f.opp_last_see_loss = maxOr(
      offers(afterOpp, them).map(o => o[3]),
      0,
    );
  }

  // --- engine evidence
  const lines = evidence.before;
  const bestCp = lines[0].cp;
  const playedCp = evidence.after.cp;
  const index = lines.findIndex(l => l.uci === uci);
  const alts = lines.filter(l => l.uci !== uci);
  f.best_cp = bestCp;
  f.best_is_mate = +(bestCp >= 9000);
  f.rank = index >= 0 ? index + 1 : 3;
  f.alt_cp = alts.length ? alts[0].cp : -9999;
  f.played_cp_before = index >= 0 ? lines[index].cp : -9999;
  f.played_cp = playedCp;
  f.played_mate = +(playedCp >= 9000);
  const best = Math.max(bestCp, playedCp);
  f.cp_loss = best - playedCp;
  f.wc_best = winChance(best);
  f.wc_played = winChance(playedCp);
  f.wc_loss = f.wc_best - f.wc_played;
  f.wc_alt = alts.length ? winChance(f.alt_cp) : 0;
  f.wc_gain_vs_alt = f.wc_played - f.wc_alt;
  const reply = evidence.after.reply;
  f.reply_is_accept = +(!!reply && hang.some(o => o[3] > 0 && o[0] === parseSquare(reply.slice(2, 4))));
  f.alt_net = 0;
  if (alts.length) {
    const m = findMove(beforeMoves, alts[0].uci);
    if (m) f.alt_net = altNets.get(keyOf(m)) ?? 0;
  }
  return f;
}

export function exchangeScore(features: Record<string, number>): number {
  const x = exchangeModel.features.map(name => features[name]);
  let raw = exchangeModel.baseline;
  for (const t of exchangeModel.trees) {
    let i = 0;
    while (!t.leaf[i]) i = x[t.f[i]] <= t.t[i] ? t.l[i] : t.r[i];
    raw += t.v[i];
  }
  return 1 / (1 + Math.exp(-raw));
}

export interface ExchangeDecision {
  candidate: boolean;
  score: number;
  brilliant: boolean;
}
// positions: [previous?, before, after]; lines are the review window's root lines (White's point of view).
export function evaluateBrilliantExchange(
  positions: string[],
  beforeLines: { cp?: number; mate?: number; moves: string[] }[],
  afterLines: { cp?: number; mate?: number; moves: string[] }[],
  uci: string,
): ExchangeDecision {
  const none = { candidate: false, score: 0, brilliant: false };
  const n = positions.length;
  if (n < 2 || !beforeLines.length || !afterLines.length) return none;
  const mover = fromFen(positions[n - 2]).turn;
  const features = exchangeFeatures(n > 2 ? positions[n - 3] : undefined, positions[n - 2], uci, {
    before: beforeLines.slice(0, 2).map(l => ({ uci: l.moves[0], cp: lineCp(l, mover) })),
    after: { cp: lineCp(afterLines[0], mover), reply: afterLines[0].moves[0] },
  });
  if (!features) return none;
  const score = exchangeScore(features);
  return { candidate: true, score, brilliant: score >= exchangeModel.cutoff };
}
