import { INITIAL_FEN } from 'chessops/fen';
import { ChildNode, Node, makeComment, makeOutcome, makePgn, type PgnNodeData } from 'chessops/pgn';

import type { TreeNodeLite } from 'lib/tree/types';

import type AnalyseCtrl from './ctrl';
import { position } from './noSweatCore';

export type PgnExportMode = 'annotated' | 'raw';

// Use the same Chessops PGN model as native import. Export the actual tree,
// including annotations and variations, rather than an unsubmitted import draft.
// Native postgame raw export rebuilds SAN without any comments or NAGs, even
// imported ones (game/PgnDump.scala; api/PgnDump.scala). Raw follows that mainline
// behavior; annotated includes all variations. Both use current board headers.
export function boardPgn(ctrl: AnalyseCtrl, mode: PgnExportMode = 'annotated'): string {
  const annotated = mode === 'annotated';
  const root = ctrl.tree.root;
  let end: TreeNodeLite = root;
  while (end.children[0]) end = end.children[0];
  const headers = new Map(
    ctrl.data.noSweatPgnHeaders ?? [
      ['Event', 'Analysis'],
      ['Site', 'https://mutechess.org'],
      ['Date', '????.??.??'],
      ['Round', '?'],
      ['White', '?'],
      ['Black', '?'],
      ['Result', makeOutcome(position(end.fen).outcome())],
    ],
  );
  const outcome = position(end.fen).outcome();
  if (outcome) headers.set('Result', makeOutcome(outcome));
  if (root.fen !== INITIAL_FEN) {
    headers.set('SetUp', '1');
    headers.set('FEN', root.fen);
  } else {
    headers.delete('SetUp');
    headers.delete('FEN');
  }
  const moves = new Node<PgnNodeData>();
  const append = (into: Node<PgnNodeData>, from: TreeNodeLite) => {
    for (const child of annotated ? from.children : from.children.slice(0, 1)) {
      if (!child.san) continue;
      const comments = annotated ? (child.comments?.map(c => c.text) ?? []) : [];
      const score = annotated ? (child.eval ?? child.ceval) : undefined;
      const clock =
        annotated && child.clock !== undefined && Number.isFinite(child.clock) && child.clock >= 0
          ? child.clock / 100
          : undefined;
      if (score?.mate !== undefined || score?.cp !== undefined || clock !== undefined)
        comments.push(
          makeComment({
            evaluation:
              score?.mate !== undefined
                ? { mate: score.mate, depth: score.depth }
                : score?.cp !== undefined
                  ? { pawns: score.cp / 100, depth: score.depth }
                  : undefined,
            clock,
          }),
        );
      const node = new ChildNode<PgnNodeData>({
        san: child.san,
        nags: annotated ? [...new Set(child.glyphs?.map(g => g.id))] : undefined,
        comments,
      });
      into.children.push(node);
      append(node, child);
    }
  };
  append(moves, root);
  return makePgn({ headers, moves, comments: annotated ? root.comments?.map(c => c.text) : undefined });
}

export function downloadBoardPgn(ctrl: AnalyseCtrl, mode: PgnExportMode = 'annotated'): void {
  const url = URL.createObjectURL(
    new Blob([boardPgn(ctrl, mode)], { type: 'application/x-chess-pgn;charset=utf-8' }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = mode === 'raw' ? 'mutechess-analysis-raw.pgn' : 'mutechess-analysis.pgn';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
