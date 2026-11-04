// Mobile Maia / En Croissant annotations over native Lichess analysis.
// Accuracy, ACPL, best lines and Learn from your mistakes stay native.
import { parseUci } from 'chessops/util';

import { moveClasses } from 'lib/nosweat/moveClasses';
import { gameReviewQualities } from 'lib/nosweat/reviewQuality';
import type { Glyph, TreeNodeBase } from 'lib/tree/types';

import {
  muteBrilliantSource,
  type Annotation,
  type ClassificationInput,
  type ClassificationResult,
} from './noSweatClassify';
import { legalUcis, position, standardUci, terminalScore } from './noSweatCore';
import type { Review } from './noSweatFish';

export const reviewSource = 'mobile-maia-full-review-v2';
export { moveClasses } from 'lib/nosweat/moveClasses';
export const qualityGlyph = (symbol: Annotation): Glyph | undefined => {
  const c = moveClasses.find(c => c.symbol === symbol);
  return (
    c && {
      id: c.id,
      name: c.name,
      symbol,
      comp: true,
      source: symbol === '!!' ? muteBrilliantSource : reviewSource,
    }
  );
};

export { gameReviewQualities, gameReviewQuality } from 'lib/nosweat/reviewQuality';

export function nativeReview(node: TreeNodeBase): Review | undefined {
  const terminal = terminalScore(node.fen);
  if (terminal)
    return {
      current: { depth: 99, lines: [{ ...terminal, moves: [] }] },
      terminal: true,
      quality: reviewSource,
    };
  const evals = node.eval?.pvs;
  if (!evals || evals.length < Math.min(2, legalUcis(node.fen).length)) return undefined;
  const pos = position(node.fen);
  const lines = evals.slice(0, 2).map(pv => ({
    ...pv,
    moves: pv.moves.split(' ').map((uci, i) => {
      const move = parseUci(uci);
      return i === 0 && move ? standardUci(pos, move) : uci;
    }),
  }));
  if (new Set(lines.map(l => l.moves[0])).size !== lines.length) return undefined;
  return { current: { depth: node.eval?.depth ?? 0, lines }, quality: reviewSource };
}

interface Dependencies {
  classify(input: ClassificationInput, signal: AbortSignal): Promise<ClassificationResult>;
  search(fen: string, signal: AbortSignal, depth: number, time: number, session?: symbol): Promise<Review>;
}
export class FullGameClassifier {
  constructor(private readonly deps: Dependencies) {}
  async run(
    nodes: TreeNodeBase[],
    signal: AbortSignal,
    current: () => boolean,
    progress: (done: number, total: number, phase?: string) => void,
    quality: { depth: number; movetime: number } = gameReviewQualities[0],
  ): Promise<Map<number, Annotation>> {
    const valid = () => {
      if (signal.aborted || !current()) throw new Error('Cancelled');
    };
    const results = new Map<number, Annotation>();
    if (!nodes.slice(1).some(n => n.uci && !n.glyphs?.some(g => !g.comp && g.id >= 1 && g.id <= 6)))
      return results;
    // Mobile Maia reviews the line forwards in one isolated engine session.
    // Native replay evaluates backwards and does not retain earlier complete
    // iterations. Keep its graph/accuracy untouched, and collect the complete
    // classification evidence separately instead of silently dropping it.
    const session = Symbol();
    const reviews: Review[] = [];
    for (const [i, node] of nodes.entries()) {
      valid();
      progress(i, nodes.length - 1, 'Checking move evidence');
      reviews.push({
        ...(await this.deps.search(node.fen, signal, quality.depth, quality.movetime, session)),
        quality: `${reviewSource}:${quality.depth}:${quality.movetime}`,
      });
      valid();
    }
    let confirmationBudget = 6;
    for (let i = 1; i < nodes.length; i++) {
      valid();
      progress(i - 1, nodes.length - 1);
      if (!nodes[i].uci || nodes[i].glyphs?.some(g => !g.comp && g.id >= 1 && g.id <= 6)) continue;
      const window = nodes.slice(Math.max(0, i - 2), i + 1);
      const windowReviews = reviews.slice(Math.max(0, i - 2), i + 1);
      const before = window[window.length - 2];
      const move = parseUci(nodes[i].uci!);
      if (!move) continue;
      const input = {
        positions: window.map(n => n.fen),
        reviews: windowReviews,
        move: standardUci(position(before.fen), move),
        ply: nodes[i].ply,
        history: nodes.slice(Math.max(1, i - 6), i).map((node, offset) => {
          const index = Math.max(1, i - 6) + offset;
          const previous = nodes[index - 1];
          const parsed = parseUci(node.uci!);
          return {
            ply: node.ply,
            before: previous.fen,
            after: node.fen,
            move: parsed ? standardUci(position(previous.fen), parsed) : '',
            positions: nodes.slice(Math.max(0, index - 2), index + 1).map(n => n.fen),
            reviews: reviews.slice(Math.max(0, index - 2), index + 1),
          };
        }),
      };
      let result = await this.deps.classify(input, signal);
      valid();
      const provisional = result.provisional ?? result.symbol;
      // A complete earlier-iteration window is already corroboration. Only an
      // unsupported award consumes Mobile Maia's six-search check allowance.
      if ((provisional === '!!' || provisional === '!') && result.withheld) {
        const start = provisional === '!' && i > 1 ? i - 2 : i - 1;
        const cost = i - start + 1;
        if (cost > confirmationBudget) continue;
        confirmationBudget -= cost;
        const confirmation: Review[] = [];
        const confirmationSession = Symbol();
        for (let n = start; n <= i; n++) {
          valid();
          confirmation.push({
            ...(await this.deps.search(
              nodes[n].fen,
              signal,
              quality.depth + 2,
              quality.movetime,
              confirmationSession,
            )),
            quality: reviews[n].quality,
          });
          valid();
        }
        result = await this.deps.classify({ ...input, confirmation }, signal);
        valid();
      }
      if (!result.withheld) results.set(nodes[i].ply, result.symbol);
    }
    valid();
    progress(nodes.length - 1, nodes.length - 1);
    return results;
  }
}

export function classificationCounts(nodes: TreeNodeBase[], color: Color): number[] {
  const counts = moveClasses.map(() => 0);
  for (const node of nodes) {
    if (!node.uci || (node.ply % 2 === 1 ? 'white' : 'black') !== color) continue;
    const category = moveClasses.findIndex(c => node.glyphs?.some(g => g.id === c.id));
    if (category !== -1) counts[category]++;
  }
  return counts;
}
