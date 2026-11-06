import type { DrawShape } from '@lichess-org/chessground/draw';
import { parseUci } from 'chessops/util';
import { attributesModule, classModule, init } from 'snabbdom';

import { frag } from 'lib';
import { winningChances } from 'lib/ceval';
import { licon } from 'lib/licon';
import { saveEnginePreferences, showMaiaRating, showEngineSettings } from 'lib/nosweat/engineSettings';
import { maiaExpectedScore } from 'lib/nosweat/expectedScore';
import { muteText } from 'lib/nosweat/i18n';
import { storage } from 'lib/storage';
import { hl, type VNode } from 'lib/view';

import type AnalyseCtrl from './ctrl';
import { engineArrows, engineShapes, engineColors, type EngineColors } from './noSweatArrows';
import { BoardReview } from './noSweatBoardReview';
import { candidateWhiteCp, qualityLabels, stockfishWinrate } from './noSweatCandidateQuality';
import { encodeHistory, legalUcis, policy, san, position, standardUci, type Candidate } from './noSweatCore';
import { reviewClick, reviewMove } from './noSweatEvents';
import { ReviewFish, type Review, type CandidateSearchOptions } from './noSweatFish';
import { withMoveTooltip, type MoveTooltipDetails } from './noSweatMoveTooltip';
import { OpeningLabel } from './noSweatOpening';
import { readEnginePreferences, type EnginePreferences } from './noSweatPreferences';
import {
  ratingSamples as samples,
  ratingChart,
  ratingLegend,
  type RatingChartOptions,
} from './noSweatRatingChart';
import { ratingChartQualities, type RatingChartQuality } from './noSweatRatingChartQuality';

interface MaiaClient {
  predict(input: {
    tokens: Float32Array;
    selfElo: number;
    opponentElo: number;
    includeValue: boolean;
  }): Promise<{ move_logits: Float32Array; value_logits: Float32Array }>;
  release(): void;
  snapshot(): { phase: string };
}
interface Config {
  models: Record<string, { sha256: string }>;
  browserModel: string;
}
interface Prediction {
  candidates: Candidate[];
  score: number;
}
interface Scored {
  score: EvalScore;
  depth: number;
}
export class NoSweatAnalysis {
  readonly boardReview: BoardReview;
  enabled = false;
  model = '5m';
  selfElo = 1500;
  opponentElo = 1500;
  secondMaiaEnabled = true;
  secondMaiaElo = 2400;
  secondaryCandidates: Candidate[] = [];
  expectedScore?: number;
  secondaryExpectedScore?: number;
  private sideRedraw?: () => void;
  private sideHost?: HTMLElement;
  private opening?: OpeningLabel;
  mountOpening(element: HTMLElement): void {
    this.opening?.destroy();
    this.opening = new OpeningLabel(this.ctrl, element);
  }
  history = true;
  maiaArrows = true;
  fishArrows = true;
  arrowColors: EngineColors = { ...engineColors };
  ratingTable = true;
  private ratingContext = '';
  private chartHover?: { fen: string; uci: Uci };
  private chartNotation = { fen: '', moves: new Map<string, string>() };
  private ratingKey(): string {
    return JSON.stringify([
      this.model,
      this.config?.models[this.model].sha256,
      'matched-rating-sweep-v2',
      this.history,
      this.history ? this.historyFens().slice(-8) : this.historyFens().slice(-1),
      this.ctrl.path,
    ]);
  }
  status = '';
  error = '';
  candidates: Candidate[] = [];
  scores = new Map<string, Scored | undefined>();
  byRating = new Map<number, Candidate[]>();
  returnPath?: string;
  private context = '';
  private generation = 0;
  private abort = new AbortController();
  private timer?: ReturnType<typeof setTimeout>;
  private progress?: ReturnType<typeof setInterval>;
  private client?: MaiaClient;
  private config?: Config;
  private maiaTail: Promise<unknown> = Promise.resolve();
  private readonly cache = new Map<string, Prediction>();
  private readonly fish: ReviewFish;
  private readonly reviewCache = new Map<string, Review>();
  private compareBusy = false;
  private qualityBusy = false;
  private qualityRoot?: Review;
  private qualityScreened = false;
  private qualitySession = Symbol('candidate analysis');
  private readonly qualityAttempted = new Set<string>();

  constructor(readonly ctrl: AnalyseCtrl) {
    this.boardReview = new BoardReview(ctrl);
    Object.assign(this, readEnginePreferences(storage.make('nosweat.enginePreferences.v2').get()));
    this.enabled = !!ctrl.cevalEnabled();
    ctrl.ceval.storedPv(2);
    queueMicrotask(() => this.positionChanged());
    this.fish = new ReviewFish(s => {
      this.status = s;
      this.ctrl.redraw();
    });
    window.addEventListener('pagehide', this.shutdown);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.cancel();
        this.status = 'Paused while this tab is hidden';
        this.ctrl.redraw();
      } else if (this.enabled) this.positionChanged(true);
    });
  }
  private readonly refreshReview = (): void => {
    this.ctrl.setAutoShapes();
    this.ctrl.redraw();
  };
  private readonly shutdown = (): void => this.release();
  private enginePreferences(): EnginePreferences {
    return {
      model: this.model === '79m' ? '79m' : '5m',
      selfElo: this.selfElo,
      opponentElo: this.selfElo,
      secondMaiaEnabled: this.secondMaiaEnabled,
      secondMaiaElo: this.secondMaiaElo,
      history: this.history,
      maiaArrows: this.maiaArrows,
      fishArrows: this.fishArrows,
      arrowColors: this.arrowColors,
    };
  }
  engineSettings(): HTMLElement {
    const view = frag<HTMLElement>(`<fieldset class="nosweat-engine-settings"><legend>Engines</legend>
      <button type="button" class="button button-empty nosweat-maia-settings">Engine Analysis settings</button>
      <button type="button" class="button button-empty nosweat-review-engine">Advanced Stockfish settings</button></fieldset>`);
    view.querySelector<HTMLButtonElement>('.nosweat-maia-settings')!.onclick = () => this.openMaiaSettings();
    view.querySelector<HTMLButtonElement>('.nosweat-review-engine')!.onclick = () =>
      site.asset.loadEsm('analyse.local', { init: this.ctrl });
    return view;
  }
  private applyEnginePreferences(next: EnginePreferences): void {
    const inferenceChanged = (
      ['model', 'selfElo', 'secondMaiaEnabled', 'secondMaiaElo', 'history'] as const
    ).some(key => this[key] !== next[key]);
    if (next.model !== this.model) this.release();
    Object.assign(this, next);
    saveEnginePreferences(next);
    if (inferenceChanged) this.positionChanged(true);
    this.refreshReview();
  }
  private openMaiaSettings(): void {
    showEngineSettings(
      this.enginePreferences(),
      next => this.applyEnginePreferences(next),
      () => site.asset.loadEsm('analyse.local', { init: this.ctrl }),
    );
  }
  private get leadingMoveCount(): number {
    return this.secondMaiaEnabled ? 4 : 8;
  }
  private readonly analysisAllowed = (): boolean =>
    this.ctrl.isCevalAllowed() && !this.ctrl.opts.practice && !this.ctrl.study?.data.chapter.practice;

  private readonly valid = (generation: number): boolean =>
    generation === this.generation &&
    !this.abort.signal.aborted &&
    this.enabled &&
    this.analysisAllowed() &&
    !document.hidden;
  private readonly historyFens = (): string[] => this.ctrl.nodeList.map(n => n.fen);
  private readonly key = (fens = this.historyFens(), rating = this.selfElo): string =>
    JSON.stringify([
      'maia3-policy-v1',
      this.model,
      this.config?.models[this.model].sha256,
      rating,
      rating,
      this.history,
      this.history ? fens.slice(-8) : fens.slice(-1),
    ]);
  private cancel(): void {
    this.hoverChartMove();
    this.generation++;
    this.abort.abort();
    this.abort = new AbortController();
    clearTimeout(this.timer);
    clearInterval(this.progress);
    this.progress = undefined;
    this.compareBusy = false;
    this.qualityBusy = false;
  }
  release = (): void => {
    this.cancel();
    this.client?.release();
    this.client = undefined;
    this.fish.destroy();
  };
  positionChanged(force = false): void {
    const context =
      this.key() +
      JSON.stringify([this.secondMaiaEnabled, this.secondMaiaElo]) +
      this.ctrl.path +
      JSON.stringify([this.ctrl.study?.data.chapter.id, !!this.ctrl.study?.data.chapter.practice]);
    if (!force && context === this.context) return;
    this.context = context;
    this.cancel();
    this.candidates = [];
    this.secondaryCandidates = [];
    this.expectedScore = this.secondaryExpectedScore = undefined;
    this.scores.clear();
    this.qualityRoot = undefined;
    this.qualityScreened = false;
    this.qualitySession = Symbol('candidate analysis');
    this.qualityAttempted.clear();
    const ratingContext = this.ratingKey();
    if (ratingContext !== this.ratingContext) this.byRating.clear();
    this.ratingContext = ratingContext;
    this.ctrl.setAutoShapes();
    this.error = '';
    this.status = '';
    if (!this.enabled || !this.analysisAllowed() || document.hidden) return;
    if (position(this.ctrl.node.fen).isEnd()) {
      this.status = 'Terminal position — no moves to predict';
      return;
    }
    this.status = 'Analyzing Maia…';
    const generation = this.generation;
    this.timer = setTimeout(() => {
      this.refresh(generation).catch(e => this.failure(e, generation));
    }, 120);
  }
  private failure(error: unknown, generation: number): void {
    if (!this.valid(generation)) return;
    this.error = String(error instanceof Error ? error.message : error);
    this.status = '';
    this.compareBusy = false;
    this.ctrl.redraw();
  }
  private async prepare(): Promise<MaiaClient> {
    if (this.client) return this.client;
    const moduleUrl = '/assets/nosweat/analysis/maia-client.js?v=analysis1';
    const [module, response] = await Promise.all([
      import(moduleUrl),
      fetch('/assets/nosweat/analysis/config.json', {
        cache: 'no-store',
        signal: AbortSignal.timeout(15000),
      }),
    ]);
    if (!response.ok) throw new Error('Maia configuration unavailable');
    this.config = await response.json();
    const config = { ...this.config!, browserModel: this.model };
    this.client = new module.MaiaClient({
      config: async () => config,
      worker: () => new Worker('/assets/nosweat/analysis/maia-worker.js?v=analysis2', { type: 'module' }),
    });
    return this.client!;
  }
  private predict(fens: string[], rating: number, generation: number): Promise<Prediction> {
    const task = this.maiaTail
      .catch(() => {})
      .then(async () => {
        if (!this.valid(generation)) throw new Error('Cancelled');
        const client = await this.prepare();
        if (!this.valid(generation)) throw new Error('Cancelled');
        const key = this.key(fens, rating);
        const cached = this.cache.get(key);
        if (cached) return cached;
        this.progress = setInterval(() => {
          if (this.valid(generation)) {
            this.status = 'Maia: ' + client.snapshot().phase;
            this.ctrl.redraw();
          }
        }, 400);
        try {
          const logits = await client.predict({
            tokens: encodeHistory(fens, this.history),
            selfElo: rating,
            opponentElo: rating,
            includeValue: true,
          });
          if (!this.valid(generation)) throw new Error('Cancelled');
          const result = {
            candidates: policy(fens[fens.length - 1], logits.move_logits),
            score: maiaExpectedScore(logits.value_logits),
          };
          this.cache.set(key, result);
          if (this.cache.size > 128) this.cache.delete(this.cache.keys().next().value!);
          return result;
        } finally {
          clearInterval(this.progress);
          this.progress = undefined;
        }
      });
    this.maiaTail = task;
    return task;
  }
  private async refresh(generation: number): Promise<void> {
    this.status = 'Preparing local Maia…';
    this.ctrl.redraw();
    this.colorCandidates();
    const fens = this.historyFens();
    const results = await Promise.allSettled([
      this.predict(fens, this.selfElo, generation),
      ...(this.secondMaiaEnabled ? [this.predict(fens, this.secondMaiaElo, generation)] : []),
    ]);
    if (!this.valid(generation)) return;
    this.candidates = results[0].status === 'fulfilled' ? results[0].value.candidates : [];
    this.expectedScore = results[0].status === 'fulfilled' ? results[0].value.score : undefined;
    this.secondaryCandidates = results[1]?.status === 'fulfilled' ? results[1].value.candidates : [];
    this.secondaryExpectedScore = results[1]?.status === 'fulfilled' ? results[1].value.score : undefined;
    this.error = results.some(r => r.status === 'rejected')
      ? 'Maia is unavailable. Turn analysis off and on to retry.'
      : '';
    this.status = '';
    this.ctrl.setAutoShapes();
    this.ctrl.redraw();
    this.colorCandidates();
    if (this.ratingTable && this.candidates.length && this.sideRedraw) this.sampleRatings();
  }
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) {
      this.release();
      this.byRating.clear();
    } else this.ctrl.ceval.storedPv(2);
    this.positionChanged(true);
  }
  mountSide(element: HTMLElement): void {
    if (element === this.sideHost) {
      this.sideRedraw?.();
      return;
    }
    this.sideHost = element;
    const root = document.createElement('div');
    element.prepend(root);
    const patch = init([classModule, attributesModule]);
    let vnode: VNode | HTMLElement = root;
    this.sideRedraw = () => {
      vnode = patch(vnode, this.candidateView());
    };
    this.sideRedraw();
  }
  redrawSide(): void {
    this.sideRedraw?.();
    this.opening?.redraw();
  }
  private nativeLines() {
    return this.ctrl.cevalEnabled() && !this.ctrl.threatMode()
      ? (this.ctrl.node.ceval?.pvs ?? []).slice(0, 2)
      : [];
  }

  private normalUci(uci?: string): string | undefined {
    if (!uci) return undefined;
    const move = parseUci(uci);
    return move ? standardUci(position(this.ctrl.node.fen), move) : undefined;
  }
  private readonly preview = (uci: string): void => {
    this.returnPath ??= this.ctrl.path;
    this.ctrl.playUci(uci);
    this.ctrl.redraw();
  };
  private async review(
    fen: string,
    generation: number,
    moves: string[] = [],
    time = 1200,
    multiPv = 2,
    depth = 12,
    options?: CandidateSearchOptions,
  ): Promise<Review> {
    const key = JSON.stringify([
      'sf19-maia-root-screen-v3',
      fen,
      moves,
      time,
      multiPv,
      depth,
      !!options?.allRoots,
    ]);
    const cached = this.reviewCache.get(key);
    if (cached) return cached;
    const result = await this.fish.search(
      fen,
      moves,
      this.abort.signal,
      depth,
      time,
      this.qualitySession,
      multiPv,
      options,
    );
    if (!this.valid(generation)) throw new Error('Cancelled');
    this.reviewCache.set(key, result);
    if (this.reviewCache.size > 400) this.reviewCache.delete(this.reviewCache.keys().next().value!);
    return result;
  }
  private qualityCandidates(): string[] {
    const selected = new Set<string>();
    for (const candidates of this.secondMaiaEnabled
      ? [this.candidates, this.secondaryCandidates]
      : [this.candidates]) {
      let covered = 0;
      for (const candidate of candidates.slice(0, 4)) {
        selected.add(candidate.uci);
        covered += candidate.probability;
        if (covered >= 0.95) break;
      }
    }
    const played = this.normalUci(this.ctrl.node.children[0]?.uci);
    if (played) selected.add(played);
    return [...selected];
  }

  private colorCandidates(): void {
    const generation = this.generation;
    if (!this.valid(generation) || this.qualityBusy) return;
    const targets = () =>
      this.qualityCandidates().filter(
        move => (this.scores.get(move)?.depth ?? 0) < 18 && !this.qualityAttempted.has(`18:${move}`),
      );
    if (
      this.qualityAttempted.has('screen') &&
      (!this.qualityScreened || (this.qualityAttempted.has('root:18') && !targets().length))
    )
      return;
    this.qualityBusy = true;
    (async () => {
      const fen = this.ctrl.node.fen;
      const legal = new Set(legalUcis(fen));
      const search = async (moves: string[], depth: number, multiPv = 1, allRoots = false) => {
        const publish = (review: Review) => {
          if (!this.valid(generation)) return;
          if (allRoots) {
            const roots = review.current.lines.map(line => this.normalUci(line.moves[0]));
            if (
              roots.length !== legal.size ||
              new Set(roots).size !== legal.size ||
              roots.some(move => !move || !legal.has(move))
            )
              return;
            this.qualityScreened = true;
          }
          if (!this.qualityScreened) return;
          if (!moves.length) this.qualityRoot = review;
          for (const line of review.current.lines) {
            const move = this.normalUci(line.moves[0]);
            if (move && legal.has(move))
              this.scores.set(move, {
                score: line,
                depth: Math.max(this.scores.get(move)?.depth ?? 0, review.current.depth),
              });
          }
          this.ctrl.redraw();
        };
        try {
          const result = await this.review(fen, generation, moves, 0, multiPv, depth, {
            allRoots,
            maxMultiPv: 4,
            onUpdate: publish,
          });
          publish(result);
        } catch {
          // A failed or cancelled phase cannot invent missing root evidence.
          // Completed position-wide iterations remain useful if deepening times out.
        }
      };
      if (!this.qualityAttempted.has('screen')) {
        this.qualityAttempted.add('screen');
        await search([], 10, legal.size, true);
      }
      if (!this.valid(generation) || !this.qualityScreened) return;
      for (const move of this.qualityCandidates()) {
        if (!this.valid(generation)) return;
        if ((this.scores.get(move)?.depth ?? 0) >= 14 || this.qualityAttempted.has(`14:${move}`)) continue;
        this.qualityAttempted.add(`14:${move}`);
        await search([move], 14);
      }
      if (!this.qualityAttempted.has('root:18')) {
        this.qualityAttempted.add('root:18');
        await search([], 18, 4);
      }
      for (;;) {
        if (!this.valid(generation)) return;
        const move = targets()[0];
        if (!move) break;
        this.qualityAttempted.add(`18:${move}`);
        await search([move], 18);
      }
    })()
      .catch(() => {
        // Color evidence is optional; policy probabilities remain usable.
      })
      .finally(() => {
        if (this.valid(generation)) {
          this.qualityBusy = false;
          if (this.status === 'Loading Stockfish review…') this.status = '';
          this.ctrl.redraw();
          // Maia can arrive at a phase boundary; its selected candidates still deepen.
          if (this.qualityScreened && targets().length) this.colorCandidates();
        }
      });
  }

  private candidateQualities(): Map<string, RatingChartQuality> {
    if (!this.enabled || !this.analysisAllowed() || this.ctrl.threatMode()) return new Map();
    return ratingChartQualities(
      new Map([...this.scores].flatMap(([uci, result]) => (result ? [[uci, result.score] as const] : []))),
      position(this.ctrl.node.fen).turn === 'white',
    );
  }

  private moveQuality(uci: string) {
    if (!this.enabled || !this.analysisAllowed() || this.ctrl.threatMode()) return undefined;
    return this.candidateQualities().get(uci)?.quality;
  }

  private moveTooltip(uci: string, probability: number): MoveTooltipDetails | undefined {
    if (!this.enabled || !this.analysisAllowed() || this.ctrl.threatMode()) return undefined;
    const white = position(this.ctrl.node.fen).turn === 'white';
    const score = this.scores.get(uci)?.score;
    const cp = score && candidateWhiteCp(score, white);
    const knownCp = [...this.scores.values()].flatMap(value => {
      const cp = value && candidateWhiteCp(value.score, white);
      return cp === undefined ? [] : [cp];
    });
    const signed = (cp: number) => `${cp > 0 ? '+' : ''}${(cp / 100).toFixed(2)}`;
    const mate = score?.mate;
    return {
      san: san(this.ctrl.node.fen, uci),
      color: this.candidateQualities().get(uci)?.color ?? 'var(--c-font-dim)',
      maiaProbability: probability,
      stockfishEval:
        cp === undefined
          ? undefined
          : mate === undefined
            ? signed(cp)
            : `${(mate === 0 ? !white : mate > 0) ? '+' : '-'}M${Math.abs(mate)}`,
      stockfishWinrate: score && stockfishWinrate(score, white),
      stockfishEvalLoss:
        cp === undefined || !knownCp.length
          ? undefined
          : signed(white ? cp - Math.max(...knownCp) : Math.min(...knownCp) - cp),
    };
  }

  private chartStockfishMoves(): string[] {
    if (!this.enabled || !this.analysisAllowed() || this.ctrl.threatMode()) return [];
    if (this.qualityScreened) return [...this.candidateQualities().keys()].slice(0, 3);
    const lines = this.qualityRoot?.current.lines ?? this.ctrl.node.ceval?.pvs ?? [];
    return [...new Set(lines.slice(0, 3).flatMap(line => this.normalUci(line.moves[0]) ?? []))];
  }

  private chartPrimaryCandidates(): Candidate[] {
    return this.byRating.get(this.selfElo) ?? this.candidates;
  }

  private chartSan(uci: string, fen = this.ctrl.node.fen): string {
    if (this.chartNotation.fen !== fen) this.chartNotation = { fen, moves: new Map() };
    const cached = this.chartNotation.moves.get(uci);
    if (cached) return cached;
    const value = san(fen, uci);
    this.chartNotation.moves.set(uci, value);
    return value;
  }

  private readonly hoverChartMove = (uci?: string): void => {
    if (uci) {
      if (!this.enabled || !this.analysisAllowed() || this.ctrl.threatMode()) return;
      this.chartHover = { fen: this.ctrl.node.fen, uci };
      this.ctrl.ceval.hovering(this.chartHover);
      this.ctrl.setAutoShapes();
    } else if (this.chartHover) {
      const active = this.ctrl.ceval.hovering();
      if (active === this.chartHover) {
        this.ctrl.ceval.hovering(null);
        this.ctrl.setAutoShapes();
      }
      this.chartHover = undefined;
    }
  };

  private chartOptions(): RatingChartOptions {
    const fen = this.ctrl.node.fen;
    const qualities = this.candidateQualities();
    return {
      primary: this.chartPrimaryCandidates(),
      stockfish: this.chartStockfishMoves(),
      color: uci => qualities.get(uci)?.color ?? 'var(--c-font-dim)',
      describe: (uci, rating, probability) => {
        const quality = qualities.get(uci);
        return `${this.chartSan(uci, fen)} · Maia ${rating} · ${(probability * 100).toFixed(1)}% · ${quality ? qualityLabels[quality.quality] + ' (Stockfish estimate)' : 'Stockfish quality not yet available'}`;
      },
      hover: uci => {
        if (this.ctrl.node.fen === fen) this.hoverChartMove(uci);
      },
    };
  }

  sampleRatings = (): void => {
    if (this.compareBusy || !this.enabled || !this.analysisAllowed()) return;
    const context = this.ratingKey();
    if (context !== this.ratingContext) this.byRating.clear();
    this.ratingContext = context;
    if (this.byRating.size === samples.length) return;
    this.compareBusy = true;
    const generation = this.generation;
    const fens = this.historyFens();
    this.ratingTable = true;
    this.error = '';
    (async () => {
      for (const rating of samples) {
        if (!this.valid(generation) || !this.ratingTable) break;
        if (this.byRating.has(rating)) continue;
        this.status = 'Loading rating chart…';
        this.ctrl.redraw();
        // Maia's rating chart conditions BOTH players at the sampled rating.
        // The independently configurable card inputs are not changed by a sweep.
        const result = await this.predict(fens, rating, generation);
        if (!this.valid(generation)) return;
        this.byRating.set(rating, result.candidates);
        this.colorCandidates();
        this.ctrl.redraw();
      }
      if (!this.valid(generation)) return;
      this.status = '';
      this.compareBusy = false;
      this.ctrl.redraw();
    })().catch(e => this.failure(e, generation));
  };
  shapes(): DrawShape[] {
    if (!this.enabled || !this.analysisAllowed() || document.hidden || this.ctrl.threatMode()) return [];
    const lines = this.nativeLines();
    const stockfish =
      this.fishArrows && this.ctrl.showBestMoveArrows()
        ? lines.map((line, i) => ({
            uci: this.normalUci(line.moves[0])!,
            width: i
              ? Math.max(
                  3.125,
                  ((12 -
                    Math.max(0, winningChances.povDiff(position(this.ctrl.node.fen).turn, lines[0], line)) *
                      50) *
                    100) /
                    64,
                )
              : 25,
          }))
        : [];
    return engineShapes(
      engineArrows(
        stockfish,
        this.maiaArrows ? this.candidates[0]?.uci : undefined,
        this.maiaArrows && this.secondMaiaEnabled ? this.secondaryCandidates[0]?.uci : undefined,
        this.arrowColors,
      ),
      this.ctrl.bottomColor(),
    );
  }
  private readonly expanded = [false, false];

  private openRating(secondary: boolean): void {
    showMaiaRating(secondary ? this.secondMaiaElo : this.selfElo, rating =>
      this.chooseRating(rating, secondary),
    );
  }

  private maiaCard(secondary: boolean): VNode {
    const rating = secondary ? this.secondMaiaElo : this.selfElo;
    const candidates = secondary ? this.secondaryCandidates : this.candidates;
    const score = secondary ? this.secondaryExpectedScore : this.expectedScore;
    const color = secondary ? this.arrowColors.maiaSecond : this.arrowColors.maia;
    const white = position(this.ctrl.node.fen).turn === 'white';
    const side = white ? 'White' : 'Black';
    const expanded = this.expanded[Number(secondary)];
    const leading = this.leadingMoveCount;
    const rest = candidates.slice(leading).reduce((sum, c) => sum + c.probability, 0);
    const qualities = this.candidateQualities();
    const moves: (Candidate | undefined)[] = candidates.slice(0, expanded ? undefined : leading);
    while (moves.length < leading) moves.push(undefined);
    const groups = this.secondMaiaEnabled
      ? [moves]
      : [moves.slice(0, Math.ceil(moves.length / 2)), moves.slice(Math.ceil(moves.length / 2))];
    const status = !this.enabled
      ? 'Analysis off'
      : position(this.ctrl.node.fen).isEnd()
        ? 'No legal moves'
        : this.error
          ? 'Unavailable'
          : 'Analyzing…';
    return hl('section.nosweat-maia-card', { attrs: { 'aria-label': `Maia ${rating}` } }, [
      hl('header', [
        hl(
          'button.nosweat-maia-label',
          {
            attrs: {
              type: 'button',
              style: 'color:' + color,
              'aria-label': `Change ${secondary ? 'second' : 'primary'} Maia rating, ${rating}`,
              'aria-haspopup': 'dialog',
            },
            hook: reviewClick(() => this.openRating(secondary)),
          },
          'Maia ' + rating,
        ),
        hl(
          'span.nosweat-score',
          {
            attrs: {
              title: `${side} expected score: win probability plus half draw probability`,
              'aria-label': `${side} expected score ${score === undefined ? 'unavailable' : (score * 100).toFixed(1) + '%'}`,
            },
          },
          [
            hl('i.nosweat-score-side.' + side.toLowerCase(), { attrs: { 'aria-hidden': 'true' } }),
            score === undefined ? '—' : (score * 100).toFixed(1) + '%',
          ],
        ),
      ]),
      hl('div.nosweat-policy-scroll', [
        hl(
          'div.nosweat-policy-columns',
          groups.map((group, column) =>
            hl('table.nosweat-policy', { key: column }, [
              hl('thead', hl('tr', [hl('th', 'Move'), hl('th', 'Probability')])),
              hl(
                'tbody',
                group.map((c, index) => {
                  if (!c)
                    return hl('tr.nosweat-policy-placeholder', { key: 'empty-' + index }, [
                      hl('td', !candidates.length && index === 0 && column === 0 ? status : '—'),
                      hl('td', '—'),
                    ]);
                  const quality = this.moveQuality(c.uci);
                  return hl('tr', { key: this.ctrl.node.fen + c.uci }, [
                    hl(
                      'td',
                      hl(
                        'button.fbt',
                        {
                          attrs: {
                            type: 'button',
                            'data-quality': quality ?? 'pending',
                            style: qualities.has(c.uci) ? `color:${qualities.get(c.uci)!.color}` : false,
                            'aria-label':
                              san(this.ctrl.node.fen, c.uci) +
                              ': ' +
                              (quality ? qualityLabels[quality] : 'quality not yet available'),
                          },
                          hook: withMoveTooltip(
                            reviewMove(
                              () => this.preview(c.uci),
                              active => this.hoverChartMove(active ? c.uci : undefined),
                            ),
                            () => this.moveTooltip(c.uci, c.probability),
                          ),
                        },
                        san(this.ctrl.node.fen, c.uci),
                      ),
                    ),
                    hl('td', (c.probability * 100).toFixed(1) + '%'),
                  ]);
                }),
              ),
            ]),
          ),
        ),
      ]),
      hl(
        'button.nosweat-others',
        {
          attrs: {
            type: 'button',
            'aria-expanded': String(expanded),
            disabled: candidates.length <= leading,
          },
          hook: reviewClick(() => {
            this.expanded[Number(secondary)] = !expanded;
            this.ctrl.redraw();
          }),
        },
        [
          hl('span', expanded ? muteText('LeadingMoves', 'Leading moves') : muteText('Others', 'Others')),
          hl('span', !candidates.length ? '—' : expanded ? '−' : (rest * 100).toFixed(1) + '% +'),
        ],
      ),
    ]);
  }

  private candidateView(): VNode {
    return hl('section.nosweat-candidate-panel', { attrs: { 'aria-label': 'Maia analysis' } }, [
      hl('div.nosweat-maia-cards', [this.maiaCard(false), this.secondMaiaEnabled && this.maiaCard(true)]),
      hl('section.nosweat-rating-explorer', [
        hl('header.nosweat-rating-heading', [
          hl('h3', muteText('MovesByRating', 'Moves by Rating')),
          hl('button.fbt.nosweat-maia-settings', {
            attrs: {
              type: 'button',
              'aria-label': muteText('EngineAnalysis', 'Engine Analysis settings'),
              title: muteText('EngineAnalysis', 'Engine Analysis settings'),
              'data-icon': licon.Gear,
              'aria-haspopup': 'dialog',
            },
            hook: reviewClick(() => this.openMaiaSettings()),
          }),
          ratingLegend(
            this.byRating,
            uci => this.chartSan(uci),
            uci => this.preview(uci),
            this.chartOptions(),
          ),
        ]),
        this.renderRatingChart(),
      ]),
      hl('div.nosweat-maia-feedback', [
        this.returnPath !== undefined &&
          hl(
            'button.fbt.nosweat-return',
            {
              attrs: { type: 'button' },
              hook: reviewClick(() => {
                const path = this.returnPath!;
                this.returnPath = undefined;
                this.ctrl.userJump(path);
                this.ctrl.redraw();
              }),
            },
            'Return to game position',
          ),
        this.returnPath === undefined &&
          hl(
            'span',
            { attrs: { role: this.error ? 'alert' : 'status', title: this.error || this.status } },
            this.error || this.status,
          ),
      ]),
    ]);
  }
  private chooseRating(rating: number, secondary = false): void {
    if (secondary) this.secondMaiaElo = rating;
    else {
      this.selfElo = rating;
      this.opponentElo = rating;
    }
    saveEnginePreferences(this.enginePreferences());
    this.positionChanged(true);
    this.ctrl.redraw();
  }
  private renderRatingChart(): VNode {
    return ratingChart(
      this.byRating,
      uci => this.chartSan(uci),
      rating => this.chooseRating(rating),
      uci => this.preview(uci),
      () => this.sideRedraw?.(),
      this.chartOptions(),
    );
  }
}
