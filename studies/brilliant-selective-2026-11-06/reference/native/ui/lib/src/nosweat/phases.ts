// Mobile Maia 8563954429c2fb53ce0fe0e16c73c5d8a73ccfe0, GamePhaseDetector.
// Visual boundaries only: native evaluations, accuracy and game division are unchanged.
interface Piece {
  piece: string;
  file: number;
  rank: number;
}
export interface PhasePosition {
  fen: string;
  ply: number;
}
export interface GamePhases {
  middle?: number;
  end?: number;
}

const regionScore = (y: number, w: number, b: number): number => {
  if (!w && !b) return 0;
  if (w === 1 && !b) return 1 + (8 - y);
  if (w === 2 && !b) return y > 2 ? y : 0;
  if ((w === 3 || w === 4) && !b) return y > 1 ? 3 + y - 1 : 0;
  if (!w && b === 1) return 1 + y;
  if (w === 1 && b === 1) return 5 + Math.abs(4 - y);
  if (w === 2 && b === 1) return 4 + y - 1;
  if (w === 3 && b === 1) return 5 + y - 1;
  if (!w && b === 2) return y < 6 ? 2 + 6 - y : 0;
  if (w === 1 && b === 2) return 4 + 7 - y;
  if (w === 2 && b === 2) return 7;
  if (!w && (b === 3 || b === 4)) return y < 7 ? 3 + 7 - y : 0;
  if (w === 1 && b === 3) return 5 + 7 - y;
  return 0;
};

export function detectGamePhases(positions: readonly PhasePosition[]): GamePhases {
  const result: GamePhases = {};
  for (const { fen, ply } of positions) {
    const ranks = fen.split(' ')[0].split('/');
    if (ranks.length !== 8) continue;
    const board: Piece[] = [];
    ranks.forEach((row, y) => {
      let file = 0;
      for (const piece of row) {
        if (/[1-8]/.test(piece)) file += Number(piece);
        else {
          board.push({ piece, file, rank: 7 - y });
          file += 1;
        }
      }
    });
    const majorMinor = board.filter(p => 'qrbn'.includes(p.piece.toLowerCase())).length;
    const white = (p: Piece) => p.piece === p.piece.toUpperCase();
    const sparse =
      board.filter(p => p.rank === 0 && white(p)).length < 4 ||
      board.filter(p => p.rank === 7 && !white(p)).length < 4;
    let mixedness = 0;
    if (result.middle === undefined && majorMinor > 10 && !sparse)
      for (let y = 0; y <= 6; y++)
        for (let x = 0; x <= 6; x++) {
          const region = board.filter(p => p.file >= x && p.file <= x + 1 && p.rank >= y && p.rank <= y + 1);
          const w = region.filter(white).length;
          mixedness += regionScore(y + 1, w, region.length - w);
        }
    if (result.middle === undefined && (majorMinor <= 10 || sparse || mixedness > 150)) result.middle = ply;
    if (result.middle !== undefined && result.end === undefined && majorMinor <= 6) result.end = ply;
  }
  return result;
}
