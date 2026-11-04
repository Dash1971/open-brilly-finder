// Mobile Maia dev-260-alpha2 dd4e041, lib/src/stockfish.dart (AGPL-3.0).
export const gameReviewQualities = [
  { name: 'Fast', depth: 12, movetime: 500 },
  { name: 'Balanced', depth: 14, movetime: 1000 },
  { name: 'Thorough', depth: 16, movetime: 1500 },
] as const;
export const gameReviewQuality = (name: string | null): (typeof gameReviewQualities)[number] =>
  gameReviewQualities.find(q => q.name === name) ?? gameReviewQualities[0];
