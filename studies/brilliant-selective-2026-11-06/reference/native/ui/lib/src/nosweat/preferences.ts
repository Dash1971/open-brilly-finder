import { engineColors, type EngineColors } from './arrows';

export interface EnginePreferences {
  model: '5m' | '79m';
  selfElo: number;
  // Retained for old saved preferences; always normalized to the primary rating.
  opponentElo: number;
  secondMaiaEnabled: boolean;
  secondMaiaElo: number;
  history: boolean;
  maiaArrows: boolean;
  fishArrows: boolean;
  arrowColors: EngineColors;
}
export const defaultEnginePreferences: EnginePreferences = {
  model: '5m',
  selfElo: 1500,
  opponentElo: 1500,
  secondMaiaEnabled: true,
  secondMaiaElo: 2400,
  history: true,
  maiaArrows: true,
  fishArrows: true,
  arrowColors: { ...engineColors },
};
export function readEnginePreferences(raw: string | null): EnginePreferences {
  let input: Partial<EnginePreferences> = {};
  try {
    input = JSON.parse(raw ?? '{}') ?? {};
  } catch {
    /* Invalid browser preference falls back safely. */
  }
  const rating = (n: unknown, fallback = 1500) =>
    typeof n === 'number' && Number.isInteger(n) && n >= 600 && n <= 2600 && n % 100 === 0 ? n : fallback;
  const boolean = (key: 'history' | 'maiaArrows' | 'fishArrows') =>
    typeof input[key] === 'boolean' ? input[key] : true;
  const colors = input.arrowColors;
  const color = (key: keyof EngineColors) =>
    colors && typeof colors[key] === 'string' && /^#[0-9a-f]{6}$/i.test(colors[key])
      ? colors[key].toLowerCase()
      : engineColors[key];
  return {
    model: input.model === '79m' ? '79m' : '5m',
    selfElo: rating(input.selfElo),
    opponentElo: rating(input.selfElo),
    secondMaiaEnabled: typeof input.secondMaiaEnabled === 'boolean' ? input.secondMaiaEnabled : true,
    secondMaiaElo: rating(input.secondMaiaElo, 2400),
    history: boolean('history'),
    maiaArrows: boolean('maiaArrows'),
    fishArrows: boolean('fishArrows'),
    arrowColors: {
      stockfish: color('stockfish'),
      stockfishSecond: color('stockfishSecond'),
      maia: color('maia'),
      maiaSecond: color('maiaSecond'),
    },
  };
}
