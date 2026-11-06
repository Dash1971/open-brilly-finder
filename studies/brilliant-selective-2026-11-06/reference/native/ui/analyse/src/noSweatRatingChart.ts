import { hl, type Hooks, type VNode } from 'lib/view';

import type { Candidate } from './noSweatCore';
import { reviewMove } from './noSweatEvents';

// Maia platform a6e52f5: useMoveRecommendations.ts and MovesByRating.tsx.
// Preserve the raw policy and candidate union; adapt only the compact/native view.
export const ratingSamples = Array.from({ length: 21 }, (_, i) => 600 + i * 100);
export const chartX = (rating: number) => 48 + ((rating - 600) / 2000) * 300;
export const chartY = (probability: number) => 200 - Math.max(0, Math.min(1, probability)) * 165;

export interface RatingChartOptions {
  primary?: Candidate[];
  stockfish?: string[];
  color?: (uci: string) => string;
  describe?: (uci: string, rating: number, probability: number) => string;
  hover?: (uci?: string) => void;
}

export function chartMoves(
  data: Map<number, Candidate[]>,
  primary: Candidate[] = [],
  stockfish: string[] = [],
): string[] {
  const moves = new Set<string>();
  primary.slice(0, 3).forEach(move => moves.add(move.uci));
  stockfish.slice(0, 3).forEach(move => moves.add(move));
  for (const rating of ratingSamples) {
    const leader = data.get(rating)?.[0]?.uci;
    if (leader) moves.add(leader);
  }
  return [...moves];
}

function probabilityAt(data: Map<number, Candidate[]>, rating: number, uci: string): number | undefined {
  const sample = data.get(rating);
  if (!sample) return undefined;
  const probability = sample.find(move => move.uci === uci)?.probability ?? 0;
  return Number.isFinite(probability) && probability >= 0 && probability <= 1 ? probability : undefined;
}

export function chartDomain(data: Map<number, Candidate[]>, moves: string[]): 0.6 | 1 {
  if (!ratingSamples.some(rating => data.has(rating))) return 1;
  return ratingSamples.some(rating => moves.some(uci => (probabilityAt(data, rating, uci) ?? 0) > 0.6))
    ? 1
    : 0.6;
}

export function chartPath(data: Map<number, Candidate[]>, uci: string, x = chartX, y = chartY): string {
  let connected = false;
  return ratingSamples
    .map(rating => {
      const probability = probabilityAt(data, rating, uci);
      if (probability === undefined) {
        connected = false;
        return '';
      }
      const segment = `${connected ? 'L' : 'M'}${x(rating)},${y(probability)}`;
      connected = true;
      return segment;
    })
    .join(' ');
}

function chartArea(
  data: Map<number, Candidate[]>,
  uci: string,
  x: (rating: number) => number,
  y: (probability: number) => number,
): string {
  const segments: { rating: number; probability: number }[][] = [];
  let segment: { rating: number; probability: number }[] = [];
  for (const rating of ratingSamples) {
    const probability = probabilityAt(data, rating, uci);
    if (probability === undefined) {
      if (segment.length) segments.push(segment);
      segment = [];
    } else segment.push({ rating, probability });
  }
  if (segment.length) segments.push(segment);
  return segments
    .map(points => {
      const first = points[0];
      const last = points[points.length - 1];
      return `M${x(first.rating)},${y(0)} ${points
        .map(point => `L${x(point.rating)},${y(point.probability)}`)
        .join(' ')} L${x(last.rating)},${y(0)} Z`;
    })
    .join(' ');
}

const moveColor = (uci: string, options: RatingChartOptions) => options.color?.(uci) ?? 'var(--c-font-dim)';
const describe = (
  uci: string,
  rating: number,
  probability: number,
  name: (uci: string) => string,
  options: RatingChartOptions,
) =>
  options.describe?.(uci, rating, probability) ??
  `${name(uci)} · Maia ${rating} · ${(probability * 100).toFixed(1)}% · Stockfish quality unavailable`;

export function ratingLegend(
  data: Map<number, Candidate[]>,
  name: (uci: string) => string,
  preview: (uci: string) => void,
  options: RatingChartOptions = {},
): VNode {
  return hl(
    'div.nosweat-chart-legend',
    chartMoves(data, options.primary, options.stockfish).map(uci =>
      hl(
        'button.fbt',
        {
          key: uci,
          attrs: {
            type: 'button',
            style: `color:${moveColor(uci, options)}`,
            'data-move': uci,
            title: `Preview ${name(uci)}`,
          },
          hook: reviewMove(
            () => preview(uci),
            active => options.hover?.(active ? uci : undefined),
          ),
        },
        name(uci),
      ),
    ),
  );
}

const chartObservers = new WeakMap<Element, ResizeObserver>();
const tooltipRatings = new WeakMap<Element, number>();
let chartSerial = 0;

function hideTooltip(host: Element): void {
  tooltipRatings.delete(host);
  const tooltip = host.querySelector<HTMLElement>('.nosweat-rating-tooltip');
  if (tooltip) {
    tooltip.hidden = true;
    tooltip.replaceChildren();
  }
}

function showTooltip(
  host: Element,
  rating: number,
  data: Map<number, Candidate[]>,
  moves: string[],
  name: (uci: string) => string,
  options: RatingChartOptions,
): void {
  const tooltip = host.querySelector<HTMLElement>('.nosweat-rating-tooltip');
  if (!tooltip) return;
  if (!data.has(rating)) {
    hideTooltip(host);
    return;
  }
  tooltipRatings.set(host, rating);
  const heading = document.createElement('strong');
  heading.textContent = `Maia ${rating}`;
  const rows = moves.flatMap(uci => {
    const probability = probabilityAt(data, rating, uci);
    if (probability === undefined) return [];
    const row = document.createElement('div');
    row.className = 'nosweat-rating-tooltip-row';
    row.style.color = moveColor(uci, options);
    row.title = describe(uci, rating, probability, name, options);
    const label = document.createElement('span');
    label.textContent = name(uci);
    const value = document.createElement('span');
    value.textContent = `${(probability * 100).toFixed(1)}%`;
    row.append(label, value);
    return [row];
  });
  tooltip.replaceChildren(heading, ...rows);
  tooltip.hidden = false;
}

function pointHooks(
  action: (event: MouseEvent) => void,
  uci: string,
  rating: number,
  data: Map<number, Candidate[]>,
  moves: string[],
  name: (uci: string) => string,
  options: RatingChartOptions,
): Hooks {
  let element: Element | undefined;
  const hooks = reviewMove(action, active => {
    options.hover?.(active ? uci : undefined);
    const host = element?.closest('.nosweat-rating-chart');
    if (host) {
      if (active) showTooltip(host, rating, data, moves, name, options);
      else hideTooltip(host);
    }
  });
  const attachKeyboard = (vnode: VNode) => {
    element = vnode.elm as SVGElement;
    const point = element as SVGElement;
    point.onkeydown = event => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const navigation = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'];
      if (!navigation.includes(event.key) && event.key !== 'Enter' && event.key !== ' ') return;
      // These keys explore the chart, never Lichess's board/move shortcuts.
      event.preventDefault();
      event.stopPropagation();
      if (event.key === 'Enter' || event.key === ' ') {
        if (!event.repeat)
          point.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));
        return;
      }
      const ratings = ratingSamples.filter(sample => probabilityAt(data, sample, uci) !== undefined);
      const series = moves.filter(move => probabilityAt(data, rating, move) !== undefined);
      let targetRating = rating;
      let targetMove = uci;
      if (event.key === 'ArrowLeft') targetRating = ratings[Math.max(0, ratings.indexOf(rating) - 1)];
      if (event.key === 'ArrowRight')
        targetRating = ratings[Math.min(ratings.length - 1, ratings.indexOf(rating) + 1)];
      if (event.key === 'Home') targetRating = ratings[0];
      if (event.key === 'End') targetRating = ratings[ratings.length - 1];
      if (event.key === 'ArrowUp') targetMove = series[Math.max(0, series.indexOf(uci) - 1)];
      if (event.key === 'ArrowDown')
        targetMove = series[Math.min(series.length - 1, series.indexOf(uci) + 1)];
      const host = point.closest('.nosweat-rating-chart');
      const targetSeries = [...(host?.querySelectorAll('.nosweat-rating-series') ?? [])].find(
        group => group.getAttribute('data-move') === targetMove,
      );
      const target = targetSeries?.querySelector<SVGElement>(`a[data-rating="${targetRating}"]`);
      if (host && target) {
        host
          .querySelectorAll('.nosweat-rating-point[tabindex="0"]')
          .forEach(el => el.setAttribute('tabindex', '-1'));
        target.setAttribute('tabindex', '0');
        target.focus();
      }
    };
  };
  return {
    ...hooks,
    insert: vnode => {
      hooks.insert?.(vnode);
      attachKeyboard(vnode);
    },
    update: (old, vnode) => {
      hooks.update?.(old, vnode);
      attachKeyboard(vnode);
    },
  };
}

export function ratingChart(
  data: Map<number, Candidate[]>,
  name: (uci: string) => string,
  select: (rating: number) => void,
  _preview: (uci: string) => void,
  redraw: Redraw = () => {},
  options: RatingChartOptions = {},
): VNode {
  const moves = chartMoves(data, options.primary, options.stockfish);
  const width = document.querySelector<HTMLElement>('.nosweat-rating-chart')?.clientWidth || 300;
  const height = 149;
  const left = 41;
  const right = Math.min(68, Math.max(38, ...moves.map(uci => name(uci).length * 6 + 9)));
  const top = 7;
  const bottom = 23;
  const domain = chartDomain(data, moves);
  const gradientPrefix = `nosweat-rating-${chartSerial++}`;
  const firstRating = ratingSamples.find(rating =>
    moves.some(uci => probabilityAt(data, rating, uci) !== undefined),
  );
  const firstMove =
    firstRating === undefined
      ? undefined
      : moves.find(uci => probabilityAt(data, firstRating, uci) !== undefined);
  const x = (rating: number) => left + ((rating - 600) / 2000) * (width - left - right);
  const y = (p: number) =>
    height - bottom - (Math.max(0, Math.min(domain, p)) / domain) * (height - top - bottom);
  // Every series remains in the plot/legend. Only endpoint labels are bounded by
  // the available height; dense cases remain fully named in the shared tooltip.
  const endpoints = moves
    .flatMap(uci => {
      const probability = probabilityAt(data, 2600, uci);
      return probability === undefined ? [] : [{ uci, y: y(probability) }];
    })
    .slice(0, Math.floor((height - bottom - top) / 12) + 1)
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < endpoints.length; i++)
    endpoints[i].y = Math.max(endpoints[i].y, endpoints[i - 1].y + 12);
  if (endpoints.length) {
    endpoints[endpoints.length - 1].y = Math.min(endpoints[endpoints.length - 1].y, height - bottom);
    for (let i = endpoints.length - 2; i >= 0; i--)
      endpoints[i].y = Math.min(endpoints[i].y, endpoints[i + 1].y - 12);
  }
  const attachSurface = (vnode: VNode) => {
    const svg = vnode.elm as SVGSVGElement;
    svg.onmousemove = event => {
      const rect = svg.getBoundingClientRect();
      if (!rect.width) return;
      const mouseX = ((event.clientX - rect.left) / rect.width) * width;
      if (mouseX < left || mouseX > width - right) {
        const host = svg.closest('.nosweat-rating-chart');
        if (host) hideTooltip(host);
        return;
      }
      const rating = 600 + Math.round(((mouseX - left) / (width - left - right)) * 20) * 100;
      const host = svg.closest('.nosweat-rating-chart');
      if (host) showTooltip(host, rating, data, moves, name, options);
    };
    svg.onmouseleave = () => {
      const host = svg.closest('.nosweat-rating-chart');
      if (host && !svg.contains(document.activeElement)) hideTooltip(host);
    };
  };
  return hl(
    'div.nosweat-rating-chart',
    {
      hook: {
        insert: vnode => {
          const el = vnode.elm as HTMLElement;
          let previous = width;
          const observer = new ResizeObserver(() => {
            const next = el.clientWidth;
            if (next && next !== previous) {
              previous = next;
              redraw();
            }
          });
          chartObservers.set(el, observer);
          observer.observe(el);
        },
        postpatch: (_, vnode) => {
          const host = vnode.elm as Element;
          const rating = tooltipRatings.get(host);
          if (rating !== undefined) showTooltip(host, rating, data, moves, name, options);
          const active = document.activeElement;
          if (active?.matches('.nosweat-rating-point') && active.closest('.nosweat-rating-chart') === host) {
            host
              .querySelectorAll('.nosweat-rating-point[tabindex="0"]')
              .forEach(el => el.setAttribute('tabindex', '-1'));
            active.setAttribute('tabindex', '0');
          }
        },
        destroy: vnode => {
          chartObservers.get(vnode.elm as Element)?.disconnect();
          tooltipRatings.delete(vnode.elm as Element);
        },
      },
    },
    [
      hl(
        'svg',
        {
          attrs: {
            viewBox: `0 0 ${width} ${height}`,
            role: 'group',
            'aria-label':
              'Moves by rating: Maia probability from 600 to 2600. Arrow keys explore; Enter selects a rating.',
            'data-domain': domain,
          },
          hook: { insert: attachSurface, update: (_, vnode) => attachSurface(vnode) },
        },
        [
          ...[0, 0.25, 0.5, 0.75, 1].flatMap(fraction => {
            const p = fraction * domain;
            return [
              hl('line', {
                attrs: {
                  x1: left,
                  x2: width - right,
                  y1: y(p),
                  y2: y(p),
                  stroke: 'currentColor',
                  opacity: 0.18,
                  'stroke-dasharray': '3 3',
                },
              }),
              hl(
                'text',
                {
                  attrs: {
                    x: left - 6,
                    y: y(p) + 4,
                    'text-anchor': 'end',
                    fill: 'currentColor',
                    'font-size': 11,
                  },
                },
                `${Math.round(p * 100)}%`,
              ),
            ];
          }),
          ...(width < 360 ? [600, 1600, 2600] : [600, 1000, 1400, 1800, 2200, 2600]).flatMap(rating => [
            hl('line', {
              attrs: {
                x1: x(rating),
                x2: x(rating),
                y1: top,
                y2: height - bottom,
                stroke: 'currentColor',
                opacity: 0.12,
                'stroke-dasharray': '3 3',
              },
            }),
            hl(
              'text',
              {
                attrs: {
                  x: x(rating),
                  y: height - 5,
                  'text-anchor': 'middle',
                  fill: 'currentColor',
                  'font-size': 11,
                },
              },
              String(rating),
            ),
          ]),
          hl(
            'text',
            {
              attrs: {
                transform: `translate(10 ${(top + height - bottom) / 2}) rotate(-90)`,
                'text-anchor': 'middle',
                fill: 'currentColor',
                'font-size': 11,
              },
            },
            'Maia probability',
          ),
          hl(
            'defs',
            moves.map(uci =>
              hl(
                'linearGradient',
                {
                  key: uci,
                  attrs: { id: `${gradientPrefix}-${uci}`, x1: '0', y1: '0', x2: '0', y2: '1' },
                },
                [
                  hl('stop', {
                    attrs: { offset: '5%', 'stop-color': moveColor(uci, options), 'stop-opacity': 0.5 },
                  }),
                  hl('stop', {
                    attrs: { offset: '95%', 'stop-color': moveColor(uci, options), 'stop-opacity': 0 },
                  }),
                ],
              ),
            ),
          ),
          ...moves.map(uci => {
            const color = moveColor(uci, options);
            return hl('g.nosweat-rating-series', { key: uci, attrs: { 'data-move': uci } }, [
              hl('path.nosweat-rating-area', {
                attrs: {
                  d: chartArea(data, uci, x, y),
                  fill: `url(#${gradientPrefix}-${uci})`,
                  'pointer-events': 'none',
                },
              }),
              hl('path.nosweat-rating-line', {
                attrs: {
                  d: chartPath(data, uci, x, y),
                  fill: 'none',
                  stroke: color,
                  'stroke-width': 2,
                  'stroke-linejoin': 'round',
                  'pointer-events': 'none',
                },
              }),
              ...ratingSamples.flatMap(rating => {
                const p = probabilityAt(data, rating, uci);
                if (p === undefined) return [];
                const title = describe(uci, rating, p, name, options);
                return [
                  hl(
                    'a.nosweat-rating-point',
                    {
                      key: rating,
                      attrs: {
                        href: '#',
                        role: 'button',
                        'aria-label': `${title} · Select Maia ${rating}`,
                        'data-rating': rating,
                        tabindex: uci === firstMove && rating === firstRating ? 0 : -1,
                      },
                      hook: pointHooks(
                        event => {
                          event.preventDefault();
                          select(rating);
                        },
                        uci,
                        rating,
                        data,
                        moves,
                        name,
                        options,
                      ),
                    },
                    [
                      hl('title', title),
                      hl('circle', { attrs: { cx: x(rating), cy: y(p), r: 2.5, fill: color } }),
                    ],
                  ),
                ];
              }),
            ]);
          }),
          ...endpoints.map(point =>
            hl(
              'text.nosweat-rating-endpoint',
              {
                key: point.uci,
                attrs: {
                  x: width - right + 5,
                  y: point.y + 4,
                  fill: moveColor(point.uci, options),
                  'font-size': 11,
                  'data-move': point.uci,
                },
              },
              name(point.uci),
            ),
          ),
        ],
      ),
      // This small tooltip owns its DOM children so pointer/focus updates do not
      // redraw the board or mutate the native analysis tree.
      hl('div.nosweat-rating-tooltip', { attrs: { role: 'tooltip', hidden: true } }),
    ],
  );
}
