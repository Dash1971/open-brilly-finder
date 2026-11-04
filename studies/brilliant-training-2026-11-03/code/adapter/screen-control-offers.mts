// One-study sampling sidecar. Static legal offers only; no engine, model or labels.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { isMuteSacrifice } from '../../brilliants-improvement-2026-11-03/root/frozen-v4/noSweatClassify.ts';

const [input, output] = process.argv.slice(2);
if (!output) throw Error('Expected immutable queue and new sidecar output');
const hash = (p: any) => createHash('sha256').update(readFileSync(p)).digest('hex');
const queue = JSON.parse(readFileSync(input, 'utf8'));
const started = performance.now();
const games: any[] = [];
let stopped = false;
for (const game of queue.games) {
  const positions: any[] = [];
  for (const p of game.positions) {
    if (performance.now() - started > 20000) { stopped = true; break; }
    positions.push({ ply: p.ply, raw_legal_offer: isMuteSacrifice(p.fen_before, p.fen_after) });
  }
  games.push({ game_id: game.game_id, positions, complete: positions.length === game.positions.length });
  if (stopped) break;
}
writeFileSync(output, JSON.stringify({
  scope: 'Static legal-offer sampling before any current labels or model scores. Prefer these among unannotated controls; unknown/unscanned positions remain unknown, never false.',
  queue_sha256: hash(input), script_sha256: hash(new URL(import.meta.url)),
  source_helper_sha256: hash(new URL('../../brilliants-improvement-2026-11-03/root/frozen-v4/noSweatClassify.ts', import.meta.url)),
  created_at_utc: new Date().toISOString(), stopped_at_wall_cap: stopped, games,
}, null, 2) + '\n');
console.log(JSON.stringify({ games: games.length, positions: games.reduce((n, g) => n + g.positions.length, 0), offers: games.reduce((n, g) => n + g.positions.filter((p: any) => p.raw_legal_offer).length, 0), stopped }));
