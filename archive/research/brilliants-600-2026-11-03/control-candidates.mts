// Study-local, read-only PGN candidate descriptors. No engine or label inference.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { isMuteSacrifice } from './reference/current-v2/noSweatClassify.ts';
const root = dirname(fileURLToPath(import.meta.url));
const rows = JSON.parse(readFileSync(join(root, 'control-candidates-input.json'), 'utf8'));
const started = Date.now();
for (const row of rows) {
  row.current_v2_legal_piece_offer = isMuteSacrifice(row.fen_before, row.fen_after);
  row.sampling_priority = row.current_v2_legal_piece_offer ? 'apparent_piece_offer'
    : !row.capture && !['p', 'k'].includes(row.moved_piece.toLowerCase()) && row.moved_piece_attacked && row.moved_piece_defended ? 'quiet_attacked_defended_piece'
      : row.recapture_same_square ? 'recapture_exchange'
        : row.capture ? 'other_capture' : 'other_quiet';
  row.source_link = `https://www.chess.com/analysis/game/live/${row.game_id}/review?move=${row.ply - 1}`;
}
for (const account of ['nelsi', 'hansen', 'KNVB', 'GothamChess', 'Hikaru']) {
  const cases = rows.filter((row: any) => row.account === account);
  cases.sort((a: any, b: any) => Number(b.current_v2_legal_piece_offer) - Number(a.current_v2_legal_piece_offer)
    || Number(b.sampling_priority === 'quiet_attacked_defended_piece') - Number(a.sampling_priority === 'quiet_attacked_defended_piece')
    || a.game_id.localeCompare(b.game_id) || a.ply - b.ply);
  writeFileSync(join(root, `control-candidates-v2-${account.toLowerCase()}.json`), JSON.stringify({
    prepared_at: new Date().toISOString(), policy: 'mute-chess-brilliant-v2',
    source_commit: 'b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12',
    label_status: 'All unknown until explicitly selected in fresh Game Review',
    selection: 'Prioritize apparent legal piece offers; quiet attacked/defended moves; capture/exchange controls. No engine or tuning.',
    rows: cases,
  }, null, 2) + '\n');
}
console.log(JSON.stringify({ positions: rows.length, legal_piece_offers: rows.filter((r: any) => r.current_v2_legal_piece_offer).length, elapsed_ms: Date.now() - started }));
