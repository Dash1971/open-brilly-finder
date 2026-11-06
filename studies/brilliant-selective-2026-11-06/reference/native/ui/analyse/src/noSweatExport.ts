import { url } from 'lib/xhr';

import type AnalyseCtrl from './ctrl';
import { boardPgn } from './noSweatPgn';

// Unsaved lines have no game ID. Reuse native position routes and pure-PGN GIF
// rendering instead of inventing a saved-game URL or persisting an import.
export function positionImageUrl(ctrl: AnalyseCtrl): string {
  const ds = document.body.dataset;
  return url(`${window.location.origin}/export/fen.gif`, {
    fen: ctrl.node.fen,
    color: ctrl.bottomColor(),
    lastMove: ctrl.node.uci,
    variant: 'standard',
    theme: ds.board,
    piece: ds.pieceSet,
  });
}

export function positionShareUrl(ctrl: AnalyseCtrl, embed = false): string {
  return url(`${window.location.origin}/${embed ? 'embed/analysis' : 'analysis/standard'}`, {
    fen: ctrl.node.fen,
    color: ctrl.bottomColor(),
    ...(embed && { theme: 'auto', bg: 'auto' }),
  });
}

export function analysisGifUrl(
  ctrl: AnalyseCtrl,
  orientation: Color,
  prefs: Record<string, boolean>,
): string {
  return url('/analysis/export.gif', {
    pgn: boardPgn(ctrl, 'raw'),
    color: orientation,
    theme: document.body.dataset.board,
    piece: document.body.dataset.pieceSet,
    ...prefs,
    glyphs: false,
  });
}

export function canExportAnalysisGif(ctrl: AnalyseCtrl): boolean {
  return ctrl.mainline.length >= 2 && ctrl.mainline.length <= 601 && boardPgn(ctrl, 'raw').length <= 5000;
}
