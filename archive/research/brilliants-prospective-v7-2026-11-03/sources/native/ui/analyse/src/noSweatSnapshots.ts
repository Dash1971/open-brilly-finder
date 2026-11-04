// Port of Mobile Maia StockfishSearchSnapshots: exact, complete iterations.
export interface ReviewLine extends EvalScore {
  moves: string[];
}
export interface Snapshot {
  depth: number;
  lines: ReviewLine[];
}
export class SearchSnapshots {
  private depth = -1;
  private readonly pending = new Map<number, ReviewLine>();
  completed?: Snapshot;
  previous?: Snapshot;
  constructor(
    readonly legal: Set<string>,
    readonly count: number,
    readonly white: boolean,
  ) {}
  add(text: string): void {
    if (!text.startsWith('info ')) return;
    const number = (field: string) => {
      const match = text.match(new RegExp(` ${field} (-?\\d+)`));
      return match ? Number(match[1]) : undefined;
    };
    const depth = number('depth');
    const rank = number('multipv') ?? 1;
    if (depth === undefined || depth < 1 || rank < 1 || rank > this.count || depth < this.depth) return;
    if (depth !== this.depth || this.pending.has(rank)) {
      this.pending.clear();
      this.depth = depth;
    }
    if (/ (?:lowerbound|upperbound)/.test(text)) {
      this.pending.clear();
      return;
    }
    const cp = number('score cp');
    const mate = number('score mate');
    const moves = text
      .match(/ pv (.+)$/)?.[1]
      .trim()
      .split(/\s+/);
    if (
      (cp === undefined && mate === undefined) ||
      !moves?.length ||
      !this.legal.has(moves[0]) ||
      moves.some(m => !/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(m))
    ) {
      this.pending.clear();
      return;
    }
    const pov = this.white ? 1 : -1;
    this.pending.set(rank, {
      cp: cp === undefined ? undefined : cp * pov,
      mate: mate === undefined ? undefined : mate * pov,
      moves,
    });
    if (this.pending.size !== this.count) return;
    const lines = Array.from({ length: this.count }, (_, i) => this.pending.get(i + 1)!);
    if (new Set(lines.map(l => l.moves[0])).size !== this.count) {
      this.pending.clear();
      return;
    }
    if (this.completed && depth > this.completed.depth) this.previous = this.completed;
    this.completed = { depth, lines };
    this.pending.clear();
  }
}
