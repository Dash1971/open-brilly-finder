import { Position } from 'chessops';

import { completeNode } from 'lib/tree/node';
import type { TreeNode, TreeNodeBase, TreeNodeLite } from 'lib/tree/types';

export function treeReconstruct(
  parts: TreeNodeBase[],
  variant: VariantKey,
  sidelines?: TreeNode[][],
): TreeNode {
  const completer = completeNode(variant);
  const root = completer(parts[0]);
  let node = root;
  for (let i = 1; i < parts.length; i++) {
    const n = completer(parts[i]);
    const variations = sidelines ? sidelines[i] : [];
    node.children.unshift(n, ...variations);
    node = n;
  }
  return root;
}

export function addCrazyData(node: TreeNode, pos: Position): void {
  if (pos.pockets)
    node.crazy = {
      pockets: [pos.pockets.white, pos.pockets.black],
    };
}

export function hasUserContent(node: TreeNodeLite): boolean {
  return (
    !node.comp ||
    Boolean(node.comments?.some(comment => !comment.comp)) ||
    Boolean(node.glyphs?.some(glyph => !glyph.comp)) ||
    node.children.some(hasUserContent)
  );
}

// keep computer nodes only when they are needed as ancestors of a user node
export function pruneMainlineAnalysis(node: TreeNodeLite): boolean {
  node.children = node.children.filter(pruneMainlineAnalysis);
  return hasUserContent(node);
}

export function mergeReviewData(into: TreeNodeLite, from: TreeNodeLite): void {
  into.children = into.children.filter(hasUserContent);
  if (from.eval) into.eval = from.eval;

  const comments = new Map(into.comments?.filter(c => !c.comp).map(c => [c.id, c]));
  from.comments?.forEach(c => comments.set(c.id, c));
  into.comments = Array.from(comments.values());

  const glyphs = new Map(into.glyphs?.filter(g => !g.comp).map(g => [`${g.id}:false`, g]));
  from.glyphs?.forEach(g => {
    if (
      (g.source === 'mobile-maia-brilliant-v1' ||
        g.source === 'mute-chess-brilliant-v1' ||
        g.source === 'mute-chess-brilliant-v2' ||
        g.source === 'mute-chess-brilliant-v3' ||
        g.source === 'mute-chess-brilliant-v4' ||
        g.source === 'mute-chess-brilliant-v5' ||
        g.source === 'mute-chess-brilliant-v6' ||
        g.source === 'mute-chess-brilliant-v7') &&
      [...glyphs.values(), ...(from.glyphs ?? []).filter(other => other !== g)].some(
        other => other.id >= 1 && other.id <= 6,
      )
    )
      return;
    glyphs.set(`${g.id}:${!!g.comp}`, g);
  });
  into.glyphs = Array.from(glyphs.values());

  for (const fromChild of from.children) {
    const intoChild = into.children.find(n => fromChild.id === n.id);
    if (intoChild) mergeReviewData(intoChild, fromChild);
    else into.children.push(fromChild);
  }
}
