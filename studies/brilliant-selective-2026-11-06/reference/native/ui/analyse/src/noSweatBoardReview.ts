import type { AcplChart, ChartGame } from 'chart';

import { escapeHtml } from 'lib';
import { licon } from 'lib/licon';
import { pubsub } from 'lib/pubsub';
import { bind, confirm, dataIcon, domDialog, hl, onInsert, type VNode } from 'lib/view';

import type AnalyseCtrl from './ctrl';
import { canExportAnalysisGif, positionImageUrl, positionShareUrl } from './noSweatExport';
import { boardPgn, downloadBoardPgn, type PgnExportMode } from './noSweatPgn';

type ExportCopy = 'fen' | 'image' | 'share' | PgnExportMode;

// The free board uses the same local review, chart and summary as game replay.
// The unsaved board separates editable imports from native-styled local exports.
export class BoardReview {
  private selected = 'import';
  private panel?: HTMLElement;
  private chart?: AcplChart;
  private pending = false;
  private generation = 0;
  private dirty = false;
  private failed = false;
  private button?: HTMLButtonElement;
  private copied?: ExportCopy;
  private copyError = '';
  private copyTimer?: ReturnType<typeof setTimeout>;

  constructor(private readonly ctrl: AnalyseCtrl) {}

  showComputerAnalysis(): void {
    this.selected = 'computer-analysis';
    this.ctrl.settings.set('showMainlineAnalysis', true);
    this.ctrl.redraw();
    this.chart?.resize();
  }

  view(inputs?: VNode): VNode {
    this.sync();
    const tab = (id: string, label: string) =>
      hl(
        'button',
        {
          attrs: { type: 'button', role: 'tab', 'aria-selected': String(this.selected === id) },
          class: { active: this.selected === id },
          hook: bind('click', () => {
            this.selected = id;
            if (id === 'computer-analysis') this.ctrl.settings.set('showMainlineAnalysis', true);
            this.ctrl.redraw();
            this.chart?.resize();
          }),
        },
        label,
      );
    return hl(
      'div.analyse__underboard',
      {
        hook: {
          ...onInsert(elm => this.ctrl.noSweat?.mountOpening(elm)),
          destroy: () => clearTimeout(this.copyTimer),
        },
      },
      [
        hl('div.analyse__underboard__menu', { attrs: { role: 'tablist' } }, [
          tab('computer-analysis', i18n.site.computerAnalysis),
          tab('import', 'Import'),
          tab('export', 'Export'),
        ]),
        hl('div.analyse__underboard__panels', [
          hl('div.computer-analysis', {
            class: { active: this.selected === 'computer-analysis' },
            hook: {
              ...onInsert(elm => {
                this.panel = document.createElement('div');
                this.panel.className = 'nosweat-review-chart';
                elm.append(this.panel);
                pubsub.on('analysis.server.progress', this.onAnalysis);
                this.sync();
              }),
              destroy: () => {
                this.reset();
                this.panel = undefined;
                pubsub.off('analysis.server.progress', this.onAnalysis);
              },
            },
          }),
          hl('div.import', { class: { active: this.selected === 'import' } }, [inputs]),
          hl(
            'div.fen-pgn',
            { class: { active: this.selected === 'export' } },
            this.selected === 'export' ? this.exportView() : [],
          ),
        ]),
      ],
    );
  }

  private exportView(): VNode[] {
    const names: Record<ExportCopy, string> = {
      fen: 'FEN',
      image: String(i18n.site.positionAsImage),
      share: 'position link',
      annotated: 'annotated PGN',
      raw: 'raw PGN',
    };
    const copyMe = (target: VNode, kind: ExportCopy, cls = '') =>
      hl('div.copy-me' + cls, [
        target,
        hl('button.copy-me__button.button', {
          class: { 'button-metal': this.copied !== kind },
          attrs: {
            type: 'button',
            title: `Copy ${names[kind]}`,
            'aria-label': this.copied === kind ? `${names[kind]} copied` : `Copy ${names[kind]}`,
            'data-icon': this.copied === kind ? licon.Checkmark : licon.Clipboard,
          },
          hook: bind('click', event => {
            event.stopPropagation();
            void this.copy(kind);
          }),
        }),
      ]);
    const input = (value: string, label: string) =>
      hl('input.copy-me__target', {
        attrs: { readonly: true, spellcheck: 'false', 'aria-label': label },
        props: { value },
      });
    const pgn = (mode: PgnExportMode) =>
      copyMe(
        hl(
          'a.copy-me__target',
          {
            attrs: { href: '#', role: 'button' },
            hook: bind('click', event => {
              event.preventDefault();
              downloadBoardPgn(this.ctrl, mode);
            }),
          },
          mode === 'raw' ? i18n.site.downloadRaw : i18n.site.downloadAnnotated,
        ),
        mode,
      );
    const gifAvailable = canExportAnalysisGif(this.ctrl);
    return [
      hl('div', [
        hl('strong', 'FEN'),
        copyMe(input(this.ctrl.node.fen, 'FEN export'), 'fen', '.analyse__underboard__fen'),
      ]),
      hl('div', [
        hl('strong', 'Image'),
        hl(
          'a.text.game-gif',
          {
            attrs: {
              href: '#',
              ...dataIcon(licon.Download),
              'aria-disabled': String(!gifAvailable),
              ...(!gifAvailable && {
                title:
                  this.ctrl.mainline.length < 2
                    ? 'Add moves to export a GIF.'
                    : 'This line is too long for GIF export. Download the PGN instead.',
              }),
            },
            hook: bind('click', event => {
              event.preventDefault();
              if (gifAvailable) void site.asset.loadEsm('analyse.gifDialog', { init: this.ctrl });
            }),
          },
          i18n.site.gameAsGIF,
        ),
        copyMe(
          hl(
            'a.copy-me__target',
            { attrs: { href: positionImageUrl(this.ctrl), target: '_blank', rel: 'noopener' } },
            i18n.site.positionAsImage,
          ),
          'image',
          '.position-gif',
        ),
      ]),
      hl('div', [
        hl('strong', 'Share'),
        hl(
          'a.text.embed-howto',
          {
            attrs: { href: '#', ...dataIcon(licon.Expand), title: 'Embed this position' },
            hook: bind('click', event => {
              event.preventDefault();
              this.embedPosition();
            }),
          },
          i18n.site.embedInYourWebsite,
        ),
        copyMe(input(positionShareUrl(this.ctrl), 'Share current position'), 'share'),
      ]),
      hl('div', [hl('strong', 'PGN'), pgn('annotated'), pgn('raw')]),
      ...(this.copyError ? [hl('p', { attrs: { role: 'status' } }, this.copyError)] : []),
      hl(
        'div.pgn',
        {
          attrs: { 'aria-label': 'PGN export', tabindex: 0 },
          hook: bind('click', event => {
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(event.currentTarget as HTMLElement);
            const unselected = selection?.isCollapsed;
            selection?.removeAllRanges();
            if (unselected) selection?.addRange(range);
          }),
        },
        boardPgn(this.ctrl),
      ),
    ];
  }

  private embedPosition(): void {
    const iframe = `<iframe src="${positionShareUrl(this.ctrl, true)}"
width=600 height=397 frameborder=0></iframe>`;
    void domDialog({
      modal: true,
      show: true,
      easyClose: 'clickOutside',
      htmlText: `<div><strong style="font-size:1.5em">${escapeHtml(String(i18n.site.embedInYourWebsite))}</strong><br /><br /><pre>${escapeHtml(iframe)}</pre><br />${iframe}</div>`,
    });
  }

  private async copy(kind: ExportCopy): Promise<void> {
    try {
      const value =
        kind === 'fen'
          ? this.ctrl.node.fen
          : kind === 'image'
            ? positionImageUrl(this.ctrl)
            : kind === 'share'
              ? positionShareUrl(this.ctrl)
              : boardPgn(this.ctrl, kind);
      await navigator.clipboard.writeText(value);
      this.copied = kind;
      this.copyError = '';
      clearTimeout(this.copyTimer);
      this.copyTimer = setTimeout(() => {
        this.copied = undefined;
        this.ctrl.redraw();
      }, 1000);
    } catch {
      this.copyError = 'Copy is unavailable. Select the FEN, link or PGN text, or download the PGN.';
    }
    this.ctrl.redraw();
  }

  private readonly start = () => {
    if (!this.ctrl.canAnalyseMainline()) return;
    this.ctrl.settings.set('showMainlineAnalysis', true);
    void site.asset.loadEsm('analyse.local', { init: { ctrl: this.ctrl, start: true } });
  };

  private readonly clear = async () => {
    if (await confirm(i18n.study.clearLocal)) await this.ctrl.idbTree.clear('analysis');
  };

  private readonly onAnalysis = () => {
    this.dirty = true;
  };

  private reset(): void {
    this.generation++;
    if (this.chart) {
      pubsub.off('ply', this.chart.selectPly);
      this.chart.destroy();
    }
    this.chart = undefined;
    this.pending = false;
    this.failed = false;
    this.panel?.replaceChildren();
    this.button = undefined;
  }

  sync(): void {
    const panel = this.panel;
    if (!panel) return;
    if (!this.ctrl.mainlineAnalysis) {
      if (this.chart || this.pending) this.reset();
      if (!this.button) {
        this.button = document.createElement('button');
        this.button.type = 'button';
        this.button.className = 'button text';
        this.button.dataset.icon = licon.Cogs;
        this.button.onclick = this.start;
        panel.append(this.button);
      }
      this.button.disabled = !this.ctrl.canAnalyseMainline();
      this.button.textContent = this.button.disabled ? 'Add moves to analyze' : 'Analyze game';
      return;
    }
    if (this.chart) {
      if (this.dirty) this.chart.updateData(this.ctrl.data, this.ctrl.mainline);
      this.dirty = false;
      return;
    }
    if (this.pending || this.failed) return;
    this.reset();
    const generation = this.generation;
    this.pending = true;
    const container = document.createElement('div');
    container.id = 'acpl-chart-container';
    container.className = 'analysis-chart nosweat-chart';
    const actions = document.createElement('div');
    actions.className = 'analysis-chart-actions';
    for (const [label, icon, click] of [
      ['Analyze game', licon.Cogs, this.start],
      [i18n.study.clearLocal, licon.X, this.clear],
    ] as const) {
      const button = document.createElement('button');
      button.type = 'button';
      button.title = label;
      button.setAttribute('aria-label', label);
      button.dataset.icon = icon;
      button.onclick = click;
      actions.append(button);
    }
    const plot = document.createElement('div');
    plot.className = 'analysis-chart-plot';
    const canvas = document.createElement('canvas');
    canvas.id = 'acpl-chart';
    plot.append(canvas);
    container.append(actions, plot);
    panel.append(container);
    void site.asset
      .loadEsm<ChartGame>('chart.game')
      .then(async module => {
        if (generation !== this.generation || !canvas.isConnected) return;
        const chart = await module.acpl(canvas, this.ctrl.data, this.ctrl.mainline);
        if (generation !== this.generation || !canvas.isConnected) {
          pubsub.off('ply', chart.selectPly);
          chart.destroy();
          return;
        }
        this.chart = chart;
        this.pending = false;
        this.dirty = true;
        this.sync();
      })
      .catch(() => {
        if (generation !== this.generation) return;
        this.reset();
        this.failed = true;
        const retry = document.createElement('button');
        retry.className = 'button';
        retry.textContent = 'Retry graph';
        retry.onclick = () => {
          this.failed = false;
          this.sync();
        };
        panel.append(retry);
      });
  }
}
