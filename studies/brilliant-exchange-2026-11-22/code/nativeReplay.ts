// Run the real classify() with the v8 policy over archived native Stockfish 19 Fast review windows.
// Usage (inside a Lila tree with the Mute Chess patch applied): bun --conditions=source run nativeReplay.ts <work dir>
import { readFileSync, writeFileSync } from 'node:fs';
import { classify } from '../src/noSweatClassify';

const base = process.argv[2];
const { files, test_games } = JSON.parse(readFileSync(base + '/native_files.json', 'utf8'));
const expected: Record<string, boolean> = JSON.parse(readFileSync(base + '/native_expected.json', 'utf8'));
const test = new Set<string>(test_games);
const all = { awards: 0, found: 0, false: 0 }, held = { awards: 0, found: 0, false: 0 };
let mismatch = 0, moves = 0, withheld = 0, errors = 0;
const symbols: Record<string, number> = {};
const out: Record<string, string> = {};
for (const [gid, path] of Object.entries(files as Record<string, string>)) {
  const d = JSON.parse(readFileSync(path, 'utf8'));
  const mo = d.move_outcomes, init = d.initial;
  for (let i = 0; i < mo.length; i++) {
    const m = mo[i];
    if (!m.account_own_move || !m.scored_player || m.position_overlap_excluded) continue;
    moves++;
    // Same window FullGameClassifier builds: the previous position when there is one, before, after.
    const positions = [...(i >= 1 ? [mo[i - 1].fen_before] : []), m.fen_before, m.fen_after];
    const reviews = init.slice(i >= 1 ? i - 1 : i, i + 2).map((r: any) => ({ ...r, quality: 'native:12:500' }));
    let symbol = '';
    try {
      const result = classify({ positions, reviews, move: m.uci, policy: 'mute-brilliant-v8' });
      symbol = result.symbol;
      if (result.withheld) withheld++;
    } catch {
      errors++;
    }
    symbols[symbol] = (symbols[symbol] ?? 0) + 1;
    const key = `${gid}:${m.ply}`;
    out[key] = symbol;
    const brilliant = symbol === '!!';
    if (brilliant !== !!expected[key]) mismatch++;
    if (!brilliant) continue;
    for (const c of test.has(gid) ? [all, held] : [all]) {
      c.awards++;
      if (m.gallery_positive) c.found++;
      else c.false++;
    }
  }
}
writeFileSync(base + '/native_ts_symbols.json', JSON.stringify(out));
console.log(JSON.stringify({ moves, errors, withheldNonBrilliant: withheld, mismatchVsPython: mismatch, all1000: all, heldOut337: held, symbols }));
