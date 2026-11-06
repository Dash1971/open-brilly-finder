import { encodeHistory, policy, type Candidate } from './core';
import type { EnginePreferences } from './preferences';

export const reviewAllowed = (mode: string, enabled: boolean, hidden: boolean, threat: boolean): boolean =>
  mode === 'view' && enabled && !hidden && !threat;

export interface MaiaInference {
  predict(input: {
    tokens: Float32Array;
    selfElo: number;
    opponentElo: number;
    includeValue: boolean;
  }): Promise<Float32Array>;
  release(): void;
}
export interface ReviewContext {
  id: string;
  fens: string[];
  preferences: EnginePreferences;
}
// An unavailable context means assistance is prohibited, not merely hidden.
// All result publication is tied to the complete context and generation.
export class ReviewMaia {
  primary: Candidate[] = [];
  secondary: Candidate[] = [];
  status = '';
  private key = '';
  private generation = 0;
  private client?: MaiaInference;
  private tail: Promise<unknown> = Promise.resolve();
  constructor(
    private readonly load: (model: '5m' | '79m') => Promise<MaiaInference>,
    private readonly changed: () => void,
  ) {}
  set(context?: ReviewContext): void {
    const key = context
      ? JSON.stringify({
          ...context,
          preferences: {
            model: context.preferences.model,
            selfElo: context.preferences.selfElo,
            opponentElo: context.preferences.selfElo,
            secondMaiaEnabled: context.preferences.secondMaiaEnabled,
            secondMaiaElo: context.preferences.secondMaiaElo,
            history: context.preferences.history,
          },
        })
      : '';
    if (key === this.key) return;
    const previousModel = this.key && (JSON.parse(this.key) as ReviewContext).preferences.model;
    this.key = key;
    const generation = ++this.generation;
    this.primary = [];
    this.secondary = [];
    this.status = context ? 'Loading local Maia…' : '';
    if (!context || (previousModel && previousModel !== context.preferences.model)) {
      this.client?.release();
      this.client = undefined;
    }
    this.changed();
    if (!context) return;
    this.tail = this.tail
      .catch(() => {})
      .then(async () => {
        if (generation !== this.generation) return;
        try {
          if (!this.client) {
            const client = await this.load(context.preferences.model);
            if (generation !== this.generation) {
              client.release();
              return;
            }
            this.client = client;
          }
          const { preferences: prefs, fens } = context;
          const tokens = encodeHistory(fens, prefs.history);
          const predict = async (selfElo: number) =>
            policy(
              fens[fens.length - 1],
              await this.client!.predict({
                tokens,
                selfElo,
                opponentElo: selfElo,
                includeValue: false,
              }),
            );
          const primary = await predict(prefs.selfElo);
          if (generation !== this.generation) return;
          const secondary = prefs.secondMaiaEnabled ? await predict(prefs.secondMaiaElo) : [];
          if (generation !== this.generation) return;
          this.primary = primary;
          this.secondary = secondary;
          this.status = '';
          this.changed();
        } catch {
          if (generation !== this.generation) return;
          this.client?.release();
          this.client = undefined;
          this.status = 'Maia unavailable';
          this.changed();
        }
      });
  }
  cancel(): void {
    this.set(undefined);
  }
}

export async function loadBrowserMaia(model: '5m' | '79m'): Promise<MaiaInference> {
  const moduleUrl = '/assets/nosweat/analysis/maia-client.js?v=analysis1';
  const [module, response] = await Promise.all([
    import(moduleUrl),
    fetch('/assets/nosweat/analysis/config.json', { cache: 'no-store', signal: AbortSignal.timeout(15000) }),
  ]);
  if (!response.ok) throw new Error('Maia configuration unavailable');
  const config = { ...(await response.json()), browserModel: model };
  return new module.MaiaClient({
    config: async () => config,
    worker: () => new Worker('/assets/nosweat/analysis/maia-worker.js?v=analysis2', { type: 'module' }),
  });
}
