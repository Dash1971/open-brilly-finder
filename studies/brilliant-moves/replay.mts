// Study-only replay of pinned, unmodified TypeScript annotation predicates.
// Run with the existing native tsx loader; no application checkout is changed.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  annotation, classify, isSacrifice, isMuteSacrifice, naiveMaterial, muteBrilliantSource,
  muteBrilliantRules, normalized, winChance,
} from './reference/current-v2/noSweatClassify.ts';
import { after } from './reference/current-v2/noSweatCore.ts';
import { getAnnotation } from './reference/ec-score.ts';

const root = dirname(fileURLToPath(import.meta.url));
const authorization = JSON.parse(readFileSync(join(root, 'manifest.json'), 'utf8')).metadata;
const guard = () => { if (authorization.quantity_completion_authorized !== true || authorization.tuning_authorized !== false) throw new Error('Frozen quantity-only study authorization missing'); };
guard();
const json = (file: string) => JSON.parse(readFileSync(file, 'utf8'));
const sha = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
const baseline = json(process.argv[2] || join(root, 'analysis-baseline.json'));
if (baseline.targets.length > 618) throw new Error('Authorized sample exceeds 618 moves');
const stronger = process.argv[3] ? json(process.argv[3]) : undefined;
const output = process.argv[4] || join(root, 'comparison-v2.json');
const provenance = json(join(root, 'reference/current-v2/provenance.json'));
for (const file of provenance.files)
  if (sha(join(root, 'reference/current-v2', file.local_file)) !== file.sha256)
    throw new Error('Pinned source changed: ' + file.local_file);
if (muteBrilliantSource !== 'mute-chess-brilliant-v2') throw new Error('Wrong Mute policy source');
if (stronger && stronger.engine_sha256 !== baseline.engine_sha256) throw new Error('Engine evidence changed');

// The quality identity fixes engine/options. Node budgets remain explicit on each
// complete decision window; no score is mixed between budgets inside a window.
const quality = 'extra300-fixed-sf18:' + baseline.engine_sha256;
const reviewsFor = (data: any, target: any) => target.snapshot_ids.map((id: string) => {
  const snapshot = data?.snapshots[id];
  return snapshot && {
    current: snapshot.current,
    previous: snapshot.previous || undefined,
    terminal: snapshot.terminal,
    quality,
  };
});
const materialCache = new Map<string, number>();
const material = (fen: string) => {
  guard();
  if (!materialCache.has(fen)) materialCache.set(fen, naiveMaterial(fen));
  return materialCache.get(fen)!;
};
const score = (value: any) => value.mate === undefined
  ? { type: 'cp', value: value.cp ?? 0 }
  : { type: 'mate', value: value.mate };
const diagnostics = (target: any, reviews: any[], color: any) => {
  const before = reviews.at(-2).current;
  const next = reviews.at(-1).current.lines[0];
  const alternatives = before.lines.filter((line: any) => line.moves[0] !== target.uci).map((line: any) => ({
    move: line.moves[0], cp_mover: normalized(line, color),
    piece_offer: isMuteSacrifice(target.fen_before, after(target.fen_before, line.moves[0])),
  }));
  return { mapped_loss_pp: winChance(normalized(before.lines[0], color)) - winChance(normalized(next, color)),
    after_cp_mover: normalized(next, color), played_piece_offer: isMuteSacrifice(target.fen_before, target.fen_after),
    evaluated_alternatives: alternatives,
    routine_winning_safe_alternatives: alternatives.filter((line: any) => line.cp_mover >= muteBrilliantRules.routineWinCp && !line.piece_offer) };
};

const rows: any[] = [];
const materialDifferences: any[] = [];
for (const target of baseline.targets) {
  guard();
  const reviews = reviewsFor(baseline, target);
  if (reviews.some((review: any) => !review)) throw new Error('Incomplete baseline window');
  const snapshots = target.snapshot_ids.map((id: string) => baseline.snapshots[id]);
  const positions = snapshots.map((snapshot: any) => snapshot.fen);
  const n = reviews.length;
  const before = reviews[n - 2].current;
  const next = reviews[n - 1].current.lines[0];
  const previous = n > 2 ? reviews[n - 3].current.lines[0] : undefined;
  const color = target.fen_before.split(' ')[1] === 'w' ? 'white' : 'black';
  for (const snapshot of snapshots) {
    const actual = material(snapshot.fen);
    if (actual !== snapshot.ec_material)
      materialDifferences.push({ game_id: target.game_id, ply: snapshot.position_ply,
        python_material: snapshot.ec_material, actual_typescript_material: actual });
  }
  const sacrifice = isSacrifice(target.fen_before, target.fen_after, material);
  const oracle = getAnnotation(previous ? score(previous) : null,
    score(before.lines[0]), score(next), color,
    before.lines.map((line: any) => ({ score: { value: score(line) }, sanMoves: line.moves })),
    sacrifice, target.uci);
  const port = annotation(previous, before, next, color, target.uci, sacrifice);
  if (oracle !== port) throw new Error('Independent EC scoring oracle disagrees with retained port');
  const input = { positions, reviews, move: target.uci };
  const ec = classify({ ...input, policy: 'en-croissant' }, material);
  const mute = classify({ ...input, policy: 'mute-brilliant-v2' }, material);
  const independent: Record<string, any> = {};
  let strongerWindow: any = null;
  if (stronger) {
    const checks = reviewsFor(stronger, target);
    if (checks.every(Boolean)) {
      const strongInput = { ...input, reviews: checks };
      const strongEC = classify({ ...strongInput, policy: 'en-croissant' }, material);
      strongerWindow = {
        ec: strongEC,
        mute_v2: classify({ ...strongInput, policy: 'mute-brilliant-v2' }, material),
        gates: diagnostics(target, checks, color),
      };
    }
    for (const [name, policy, initial] of [
      ['ec', 'en-croissant', ec], ['mute_v2', 'mute-brilliant-v2', mute],
    ] as const) {
      const cost = initial.provisional === '!!' ? 2 : Math.min(3, n);
      const confirmation = checks.slice(n - cost);
      independent[name] = confirmation.every(Boolean)
        ? classify({ ...input, policy, confirmation }, material)
        : { status: 'independent_window_incomplete' };
    }
  }
  const freshBinary = [...new Set(target.observations
    .filter((observation: any) => observation.source_type === 'fresh_review' && observation.label !== 'unknown')
    .map((observation: any) => observation.label === '!!'))];
  const primary = freshBinary.length === 1 ? (freshBinary[0] ? 'brilliant' : 'non_brilliant') : null;
  rows.push({ game_id: target.game_id, ply: target.ply, san: target.san, uci: target.uci,
    split: target.split, observations: target.observations, primary_fresh_binary_label: primary,
    fresh_binary_disagreement: freshBinary.length > 1, ec_sacrifice: sacrifice,
    mute_piece_offer: isMuteSacrifice(target.fen_before, target.fen_after),
    ec_raw_unchanged_oracle: oracle, ec: ec,
    mute_v2: mute, baseline_gates: diagnostics(target, reviews, color),
    stronger_window_decision: strongerWindow, independent_stronger_confirmation: independent });
}

function metrics(cases: any[], accessor: (row: any) => any) {
  const tally = { TP: 0, FN: 0, FP: 0, TN: 0, withheld_positive: 0, withheld_negative: 0 };
  for (const row of cases) {
    if (!row.primary_fresh_binary_label) continue;
    const value = accessor(row);
    if (!value || value.status) continue;
    const positive = row.primary_fresh_binary_label === 'brilliant';
    const awarded = value.symbol === '!!';
    tally[positive ? (awarded ? 'TP' : 'FN') : (awarded ? 'FP' : 'TN')]++;
    if (value.withheld) tally[positive ? 'withheld_positive' : 'withheld_negative']++;
  }
  return { ...tally,
    positive_n: tally.TP + tally.FN, negative_n: tally.FP + tally.TN,
    brilliant_detection_rate: tally.TP + tally.FN ? tally.TP / (tally.TP + tally.FN) : null,
    false_positive_rate: tally.FP + tally.TN ? tally.FP / (tally.FP + tally.TN) : null };
}
const summaries: Record<string, any> = {};
for (const policy of ['ec', 'mute_v2']) {
  const groups: Record<string, any> = { all_fresh: metrics(rows, row => row[policy]) };
  for (const split of ['development', 'discovery', 'reserved_validation'])
    groups[split] = metrics(rows.filter(row => row.split === split), row => row[policy]);
  groups.raw_eligibility_all_fresh = metrics(rows, row => ({
    symbol: policy === 'ec' ? row.ec_raw_unchanged_oracle : row.mute_v2.provisional,
    withheld: false,
  }));
  groups.by_account = Object.fromEntries(['nelsi', 'hansen', 'KNVB', 'GothamChess', 'Hikaru'].map(account => [
    account, metrics(rows.filter(row => row.observations.some((observation: any) => observation.account === account)), row => row[policy]),
  ]));
  const categories = [...new Set(rows.flatMap(row => row.observations.flatMap((observation: any) =>
    [...(observation.categories || []).map((category: string) => 'gallery:' + category),
      ...(observation.negative_category ? ['analyst:' + observation.negative_category] : [])])))] as string[];
  groups.by_observed_category = Object.fromEntries(categories.map(category => [category,
    metrics(rows.filter(row => row.observations.some((observation: any) =>
      category.startsWith('gallery:') ? observation.categories?.includes(category.slice(8))
        : observation.negative_category === category.slice(8))), row => row[policy]),
  ]));
  summaries[policy] = groups;
}
const method = json(join(root, 'methodology.json'));
const ownerControls = method.owner_regression_controls.map((control: any) => {
  guard();
  const fenAfter = after(control.fen_before, control.uci);
  return { ...control, derived_fen_after: fenAfter,
    actual_ec_sacrifice: isSacrifice(control.fen_before, fenAfter, material),
    actual_mute_v2_piece_offer: isMuteSacrifice(control.fen_before, fenAfter),
    not_in_fresh_label_metrics: true };
});
writeFileSync(output, JSON.stringify({
  completed_at: new Date().toISOString(), quantity_limit: 618,
  source_provenance: provenance, baseline_file: process.argv[2] || 'analysis-baseline.json',
  stronger_file: process.argv[3] || null, independent_ec_oracle_sha256: sha(join(root, 'reference/ec-score.ts')),
  observations_with_usable_PGN: rows.length, rows, summaries,
  python_vs_typescript_material_differences: materialDifferences,
  owner_controls_separate_from_chesscom_labels: ownerControls,
  limitations: [
    'Selected benchmark with development and separate prospective games; no population-generalization claim.',
    'Primary metrics require explicit fresh-review labels; gallery-only rows are excluded.',
    'Eligibility and confirmation-aware awards are separate. Withheld means no award, with counts retained.',
    'Prior snapshots are actual completed iterations; independent stronger windows are used only when supplied and nonshallower.',
    'Local SF18 evidence does not reproduce Chess.com engine or deployed browser search budgets.',
  ],
}, null, 2) + '\n');
console.log(JSON.stringify({ output, rows: rows.length, summaries }, null, 2));
