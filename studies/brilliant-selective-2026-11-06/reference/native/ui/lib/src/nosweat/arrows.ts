// Mobile Maia review.dart / ReviewBoardOverlayPainter, AGPL-3.0.
import type { DrawShape } from '@lichess-org/chessground/draw';
export const engineColors = {
  stockfish: '#3d9be9',
  stockfishSecond: '#8ac8f5',
  maia: '#e89b3c',
  maiaSecond: '#e85d68',
};
export type EngineColors = typeof engineColors;
export interface EngineArrow {
  uci: string;
  tail: string[];
  head: string[];
  width: number;
}
const valid = (uci?: string): uci is string => !!uci && /^[a-h][1-8][a-h][1-8][qrbn]?$/.test(uci);
// Each Maia channel contributes ONE top move, not its top three probabilities.
export function engineArrows(
  stockfish: { uci: string; width?: number }[],
  primary?: string,
  secondary?: string,
  colors: EngineColors = engineColors,
): EngineArrow[] {
  const sf = [
    ...new Map(
      stockfish
        .filter(s => valid(s.uci))
        .slice(0, 2)
        .map(s => [s.uci, s]),
    ).values(),
  ];
  const maia = new Map<string, string[]>();
  for (const [move, color] of [
    [primary, colors.maia],
    [secondary, colors.maiaSecond],
  ] as const)
    if (valid(move)) maia.set(move, [...(maia.get(move) ?? []), color]);
  const result: EngineArrow[] = [];
  sf.forEach((s, i) => {
    const color = i ? colors.stockfishSecond : colors.stockfish;
    const agreed = maia.get(s.uci);
    result.push({ uci: s.uci, tail: [color], head: agreed ?? [color], width: agreed ? 25 : (s.width ?? 25) });
    maia.delete(s.uci);
  });
  for (const [uci, colors] of maia) result.push({ uci, tail: colors, head: colors, width: 25 });
  return result;
}
// One owned Chessground custom SVG per unique move. Agreement is painted once:
// SF shaft + Maia head; two Maias share a split head (and split shaft without SF).
// Chessground anchors a custom 100x100 SVG at the square corner (its outer
// viewBox starts at -3.5). Translate to (50,50) before rotating around the center.
export function engineShapes(arrows: EngineArrow[], orientation: Color): DrawShape[] {
  return arrows.map(arrow => {
    const { uci, tail, head, width } = arrow;
    const sign = orientation === 'white' ? 1 : -1;
    const dx = (uci.charCodeAt(2) - uci.charCodeAt(0)) * sign;
    const dy = (Number(uci[1]) - Number(uci[3])) * sign;
    const distance = Math.hypot(dx, dy) * 100;
    const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
    const headHeight = 48 * Math.cos(Math.PI / 5);
    const headHalf = 48 * Math.sin(Math.PI / 5);
    const end = distance - headHeight;
    const shaft =
      tail.length === 1
        ? `<path d="M33.333 0 H${end}" stroke="${tail[0]}" stroke-width="${width}"/>`
        : tail
            .map(
              (color, i) =>
                `<path d="M33.333 ${i ? width / 4 : -width / 4} H${end}" stroke="${color}" stroke-width="${width / 2 + 0.1}"/>`,
            )
            .join('');
    const tip =
      head.length === 1
        ? `<path d="M${end} ${-headHalf} L${distance} 0 L${end} ${headHalf} Z" fill="${head[0]}"/>`
        : `<path d="M${end} ${-headHalf} L${distance} 0 L${end} 0 Z" fill="${head[0]}"/><path d="M${end} 0 L${distance} 0 L${end} ${headHalf} Z" fill="${head[1]}"/>`;
    return {
      orig: uci.slice(0, 2) as Key,
      dest: uci.slice(2, 4) as Key,
      below: true,
      customSvg: {
        html: `<g class="nosweat-engine-arrow" data-move="${uci}" data-tail="${tail.join(',')}" data-head="${head.join(',')}" transform="translate(50,50) rotate(${angle})" fill="none">${shaft}${tip}</g>`,
      },
    };
  });
}
