import type { BrowserEngineInfo } from 'lib/ceval';
// Native Stockfish loader; candidate stages follow Maia frontend 325b85c3 (GPL-3.0).
// The existing watchdog remains a Mute resource bound, not Maia's depth policy.
import { StockfishWebEngine } from 'lib/ceval/engines/stockfishWebEngine';
import { Protocol } from 'lib/ceval/protocol';

import { legalUcis, position, terminalScore } from './noSweatCore';
import { SearchSnapshots, type Snapshot } from './noSweatSnapshots';

export interface Review {
  current: Snapshot;
  previous?: Snapshot;
  terminal?: boolean;
  quality?: string;
}
export interface CandidateSearchOptions {
  allRoots?: boolean;
  maxMultiPv?: 4;
  onUpdate?: (review: Review) => void;
}
const info: BrowserEngineInfo = {
  id: 'nosweat-review-sf19-small',
  name: 'Stockfish 19 · 1MB',
  tech: 'NNUE',
  short: 'SF19',
  minThreads: 1,
  maxThreads: 1,
  minMem: 1536,
  requires: ['sharedMem', 'simd', 'dynamicImportFromWorker'],
  assets: { root: 'npm/stockfish-web', js: 'sf_19_smallnet.js' },
};
class ReviewProtocol extends Protocol {
  private output?: (command: string) => void;
  private session?: symbol;
  private task?: {
    fen: string;
    moves: string[];
    depth: number;
    time: number;
    snapshots: SearchSnapshots;
    resolve: (r: Review) => void;
    reject: (e: Error) => void;
    signal: AbortSignal;
    started: boolean;
    onUpdate?: (review: Review) => void;
    timer: ReturnType<typeof setTimeout>;
  };
  private booted!: () => void;
  private bootFailure!: (e: Error) => void;
  readonly boot: Promise<void>;
  constructor(engineInfo: BrowserEngineInfo) {
    super(engineInfo);
    this.boot = new Promise((resolve, reject) => {
      this.booted = resolve;
      this.bootFailure = reject;
    });
    this.boot.catch(() => {});
  }
  override connected(send: (command: string) => void): void {
    this.output = send;
    send('uci');
  }
  override isComputing(): boolean {
    return !!this.task;
  }
  override received(text: string): void {
    if (text === 'uciok') {
      for (const cmd of [
        'setoption name Threads value 1',
        'setoption name Hash value 16',
        'setoption name UCI_Chess960 value false',
        'setoption name UCI_AnalyseMode value true',
        'isready',
      ])
        this.output?.(cmd);
    } else if (text === 'readyok') {
      this.booted();
      const t = this.task;
      if (t && !t.started) {
        t.started = true;
        this.output?.('position fen ' + t.fen);
        this.output?.(
          `go depth ${t.depth}` +
            (t.time > 0 ? ` movetime ${t.time}` : '') +
            (t.moves.length ? ' searchmoves ' + t.moves.join(' ') : ''),
        );
      }
    } else if (text.startsWith('info ')) {
      const task = this.task;
      if (!task) return;
      const previous = task.snapshots.completed;
      task.snapshots.add(text);
      if (task.snapshots.completed && previous !== task.snapshots.completed && !task.signal.aborted)
        task.onUpdate?.({ current: task.snapshots.completed, previous: task.snapshots.previous });
    } else if (text.startsWith('bestmove')) {
      const t = this.task;
      if (!t) return;
      clearTimeout(t.timer);
      this.task = undefined;
      if (t.signal.aborted) t.reject(new Error('Cancelled'));
      else if (t.snapshots.completed)
        t.resolve({ current: t.snapshots.completed, previous: t.snapshots.previous });
      else t.reject(new Error('Stockfish did not finish a complete MultiPV iteration'));
    }
  }
  fail(error: Error): void {
    this.bootFailure(error);
    const t = this.task;
    this.task = undefined;
    if (t) {
      clearTimeout(t.timer);
      t.reject(error);
    }
  }
  async search(
    fen: string,
    moves: string[],
    depth: number,
    time: number,
    signal: AbortSignal,
    session?: symbol,
    multiPv = 2,
    options?: CandidateSearchOptions,
  ): Promise<Review> {
    let deadline: ReturnType<typeof setTimeout> | undefined;
    try {
      await Promise.race([
        this.boot,
        new Promise<never>((_, reject) => {
          deadline = setTimeout(() => reject(new Error('Stockfish startup timed out')), 45000);
        }),
      ]);
    } finally {
      clearTimeout(deadline);
    }
    if (signal.aborted) throw new Error('Cancelled');
    const terminal = terminalScore(fen);
    if (terminal) return { current: { depth: 99, lines: [{ ...terminal, moves: [] }] }, terminal: true };
    const legal = new Set(moves.length ? moves : legalUcis(fen));
    const count = Math.min(
      legal.size,
      options?.allRoots && !moves.length
        ? 256
        : Number.isFinite(multiPv)
          ? Math.max(1, Math.min(options?.maxMultiPv ?? 3, Math.floor(multiPv)))
          : 2,
    );
    return new Promise((resolve, reject) => {
      if (this.task) {
        reject(new Error('Review queue busy'));
        return;
      }
      const t = (this.task = {
        fen,
        moves,
        depth,
        time,
        resolve,
        reject,
        signal,
        started: false,
        onUpdate: options?.onUpdate,
        snapshots: new SearchSnapshots(legal, count, position(fen).turn === 'white'),
        timer: setTimeout(() => this.fail(new Error('Stockfish review timed out')), time + 15000),
      });
      signal.addEventListener(
        'abort',
        () => {
          if (this.task === t) {
            if (t.started) this.output?.('stop');
            else {
              clearTimeout(t.timer);
              this.task = undefined;
              reject(new Error('Cancelled'));
            }
          }
        },
        { once: true },
      );
      if (!session || session !== this.session) {
        this.output?.('ucinewgame');
        this.output?.('setoption name Clear Hash');
      }
      this.session = session;
      this.output?.('setoption name MultiPV value ' + count);
      this.output?.('isready');
    });
  }
}
class OwnedReviewEngine extends StockfishWebEngine {
  private disposed = false;
  override async boot(): Promise<void> {
    await super.boot();
    if (this.disposed) this.destroy();
  }
  override destroy = (): void => {
    this.disposed = true;
    this.module?.uci('quit');
    this.module = undefined;
  };
}
export class ReviewFish {
  private protocol?: ReviewProtocol;
  private engine?: StockfishWebEngine;
  private tail: Promise<unknown> = Promise.resolve();
  private generation = 0;
  constructor(
    private readonly status: (s: string) => void,
    private readonly engineInfo: BrowserEngineInfo = info,
  ) {}
  search(
    fen: string,
    moves: string[],
    signal: AbortSignal,
    depth = 14,
    time = 1200,
    session?: symbol,
    multiPv = 2,
    options?: CandidateSearchOptions,
  ): Promise<Review> {
    const generation = this.generation;
    const job = this.tail
      .catch(() => {})
      .then(async () => {
        if (signal.aborted || generation !== this.generation) throw new Error('Cancelled');
        if (!this.protocol) {
          const protocol = (this.protocol = new ReviewProtocol(this.engineInfo));
          this.engine = new OwnedReviewEngine(
            { ...this.engineInfo, assets: { ...this.engineInfo.assets } },
            s => {
              if (s?.error) protocol.fail(new Error(s.error));
              else if (s?.download) this.status('Loading Stockfish review…');
            },
            protocol,
          );
        }
        try {
          return await this.protocol.search(fen, moves, depth, time, signal, session, multiPv, options);
        } catch (error) {
          // A depth-only phase can hit the watchdog. Discard that worker before
          // another search so its late info/bestmove cannot enter a new task.
          const cleanCancellation = signal.aborted && error instanceof Error && error.message === 'Cancelled';
          if (!cleanCancellation && generation === this.generation) this.destroy();
          throw error;
        }
      });
    this.tail = job;
    return job;
  }
  destroy(): void {
    this.generation++;
    this.protocol?.fail(new Error('Cancelled'));
    this.engine?.destroy();
    this.engine = undefined;
    this.protocol = undefined;
  }
}
