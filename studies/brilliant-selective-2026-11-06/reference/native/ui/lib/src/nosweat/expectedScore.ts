// Maia3 value head is [loss, draw, win], from the side-to-move perspective.
// Same calculation as Mobile Maia's browser core.whiteScore, without the White flip.
export function maiaExpectedScore(logits: ArrayLike<number>): number {
  if (logits.length !== 3 || !Array.from(logits).every(Number.isFinite))
    throw new Error('Invalid Maia value output');
  const max = Math.max(...Array.from(logits));
  const [loss, draw, win] = Array.from(logits, n => Math.exp(n - max));
  return (win + draw / 2) / (loss + draw + win);
}
