import { Chess } from 'chessops/chess';
import { makeFen, parseFen } from 'chessops/fen';

import { escapeHtml } from 'lib';
import { domDialog } from 'lib/view';

import type AnalyseCtrl from './ctrl';

export type OpeningEntry = readonly [epd: string, eco: string, name: string];
let entries: Map<string, string> | undefined;
let loading: Promise<void> | undefined;

export function openingEpd(fen: string): string | undefined {
  try {
    const setup = parseFen(fen).unwrap();
    // Match Mobile Maia / Lichess EPD normalization, including legal en passant.
    const pos = Chess.fromSetup(setup).unwrap();
    return makeFen(pos.toSetup()).split(' ').slice(0, 4).join(' ');
  } catch {
    return undefined;
  }
}

export function identifyOpening(
  fens: readonly string[],
  table: ReadonlyMap<string, string>,
): string | undefined {
  for (let i = fens.length - 1; i >= 0; i--) {
    const epd = openingEpd(fens[i]);
    const name = epd && table.get(epd);
    if (name) return name;
  }
  return undefined;
}

function loadOpenings(): Promise<void> {
  return (loading ??= fetch(site.asset.url('nosweat/openings.json'))
    .then(response => {
      if (!response.ok) throw new Error('Opening names unavailable');
      return response.json();
    })
    .then((rows: OpeningEntry[]) => {
      entries = new Map(rows.map(([epd, eco, name]) => [epd, `${eco} · ${name}`]));
    }));
}

export class OpeningLabel {
  private readonly row = document.createElement('div');
  private readonly label = document.createElement('button');
  private readonly observer: ResizeObserver;
  private name = '';
  private context = '';

  constructor(
    private readonly ctrl: AnalyseCtrl,
    underboard: HTMLElement,
  ) {
    this.row.className = 'nosweat-opening';
    this.label.type = 'button';
    this.label.className = 'nosweat-opening-name';
    this.label.hidden = true;
    this.row.append(this.label);
    underboard.prepend(this.row);
    this.label.onclick = () => {
      if (this.label.scrollWidth <= this.label.clientWidth) return;
      domDialog({
        modal: true,
        show: true,
        easyClose: 'clickOutside',
        class: 'nosweat-opening-dialog',
        htmlText: `<h2>${escapeHtml(i18n.site.opening)}</h2><p>${escapeHtml(this.name)}</p><button class="button">${escapeHtml(i18n.site.close)}</button>`,
        actions: [{ selector: 'button', listener: (_event, dialog) => dialog.close() }],
      });
    };
    this.observer = new ResizeObserver(() => this.measure());
    this.observer.observe(this.label);
    const playerStrip = underboard.closest('.analyse')?.querySelector('.analyse__player_strip.bottom');
    if (playerStrip) this.observer.observe(playerStrip);
    void document.fonts?.ready.then(() => this.measure());
    window.addEventListener('pagehide', () => this.observer.disconnect(), { once: true });
    void loadOpenings()
      .then(() => this.redraw())
      .catch(() => this.redraw());
    this.redraw();
  }

  redraw(): void {
    if (!this.row.isConnected) return;
    const context = `${this.ctrl.path}:${this.ctrl.node.fen}:${!!entries}`;
    if (context === this.context) return;
    this.context = context;
    const path = this.ctrl.nodeList;
    const fallback = this.ctrl.data.game.opening;
    // A final-game opening is a safe fallback only once its own node is on this path.
    this.name =
      (entries &&
        identifyOpening(
          path.map(n => n.fen),
          entries,
        )) ||
      (fallback &&
      path.some(
        n => n.ply === fallback.ply && n.fen === this.ctrl.mainline.find(m => m.ply === fallback.ply)?.fen,
      )
        ? `${fallback.eco} · ${fallback.name}`
        : '');
    this.label.textContent = this.name;
    this.label.hidden = !this.name;
    this.label.title = this.name;
    this.measure();
  }

  destroy(): void {
    this.observer.disconnect();
    this.row.remove();
  }

  private measure(): void {
    // Native material and clocks share this row. Keep the name centered on the
    // board by reserving the lower player strip's width on both sides.
    const strip = this.row.closest('.analyse')?.querySelector('.analyse__player_strip.bottom');
    const width = strip?.getBoundingClientRect().width ?? 0;
    this.row.style.setProperty('--nosweat-opening-clearance', `${width > 1 ? Math.ceil(width) + 8 : 0}px`);
    const truncated = this.label.scrollWidth > this.label.clientWidth;
    this.label.disabled = !truncated;
    this.label.classList.toggle('truncated', truncated);
    this.label.setAttribute('aria-label', this.name + (truncated ? '. Show full opening name' : ''));
    this.label.setAttribute('aria-haspopup', truncated ? 'dialog' : 'false');
  }
}
