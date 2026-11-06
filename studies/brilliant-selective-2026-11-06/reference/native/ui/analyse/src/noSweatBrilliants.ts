import { parseUci } from 'chessops/util';

import type { TreeNodeBase, Glyph } from 'lib/tree/types';

import { muteBrilliantSource, type ClassificationInput, type ClassificationResult } from './noSweatClassify';
import { position, standardUci } from './noSweatCore';
import type { Review } from './noSweatFish';

export const brilliantSource = muteBrilliantSource;
export const mainlineKey = (nodes: TreeNodeBase[]): string =>
  JSON.stringify(nodes.map(n => [n.ply, n.fen, n.uci]));
export const hasQualityGlyph = (node: TreeNodeBase): boolean =>
  !!node.glyphs?.some(g => g.id >= 1 && g.id <= 6);
export const brilliantGlyph = (): Glyph => ({
  id: 3,
  symbol: '!!',
  name: 'Brilliant',
  comp: true,
  source: brilliantSource,
});

interface Dependencies {
  sacrifice(before: string, after: string, signal: AbortSignal): Promise<boolean>;
  search(fen: string, signal: AbortSignal, depth: number, time: number): Promise<Review>;
  classify(input: ClassificationInput, signal: AbortSignal): Promise<ClassificationResult>;
}
export interface VerifiedBrilliant {
  ply: number;
  fen: string;
  uci: string;
}

// Add only !!. Native judgments, evaluations and accuracy are never replaced.
export class BrilliantVerifier {
  constructor(private readonly deps: Dependencies) {}
  async run(
    nodes: TreeNodeBase[],
    signal: AbortSignal,
    current: () => boolean,
    progress: (done: number, total: number) => void,
  ): Promise<VerifiedBrilliant[]> {
    const valid = () => {
      if (signal.aborted || !current()) throw new Error('Cancelled');
    };
    const cache = new Map<string, Review>();
    const baseline = async (fen: string) => {
      if (!cache.has(fen))
        cache.set(fen, { ...(await this.deps.search(fen, signal, 14, 1200)), quality: brilliantSource });
      return cache.get(fen)!;
    };
    const verified: VerifiedBrilliant[] = [];
    for (let i = 1; i < nodes.length; i++) {
      valid();
      const before = nodes[i - 1];
      const after = nodes[i];
      progress(i - 1, nodes.length - 1);
      if (!after.uci || hasQualityGlyph(after) || position(after.fen).isEnd()) continue;
      const move = parseUci(after.uci);
      if (!move) continue;
      const uci = standardUci(position(before.fen), move);
      // The complete capture-root check runs off the UI thread, without a node cap.
      if (!(await this.deps.sacrifice(before.fen, after.fen, signal))) continue;
      valid();
      const reviews = [await baseline(before.fen), await baseline(after.fen)];
      valid();
      const input = { positions: [before.fen, after.fen], reviews, move: uci };
      const candidate = await this.deps.classify(input, signal);
      valid();
      if ((candidate.provisional || candidate.symbol) !== '!!') continue;
      // Independent, stronger, whole-decision-window corroboration, as in Mobile Maia.
      const confirmation: Review[] = [];
      for (let n = 0; n < 2; n++) {
        confirmation.push({
          ...(await this.deps.search(
            input.positions[n],
            signal,
            Math.max(16, reviews[n].current.depth + 2),
            1800,
          )),
          quality: brilliantSource,
        });
        valid();
      }
      const result = await this.deps.classify({ ...input, confirmation }, signal);
      valid();
      if (result.symbol === '!!' && !result.withheld)
        verified.push({ ply: after.ply, fen: after.fen, uci: after.uci });
    }
    valid();
    progress(nodes.length - 1, nodes.length - 1);
    return verified;
  }
}
