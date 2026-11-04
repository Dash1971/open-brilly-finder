# Pinned reference sources and local replay

This folder supports this feasibility pilot only. It is not a new application
dependency or a reusable collection framework. No classifier rules were tuned.

## Sources and licenses

- `current-v2/noSweatClassify.ts` is copied without edits from the native source
  carried by [Mute Chess main b3585f2](https://github.com/Dash1971/mute-chess/blob/b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12/deploy/lila/patches/lila-nostr-maia.patch).
  Its original header identifies the En Croissant v0.15.0 / Mobile Maia port as
  **GPL-3.0**. En Croissant's original scoring source is
  [score.ts at 6f2d2628](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src/utils/score.ts).
  The full retained license text is [GPL-3.0.txt](GPL-3.0.txt).
- `ec-score.ts` is the existing standalone, pinned EC oracle from
  [Mobile Maia preview 8563954](https://github.com/Dash1971/maia-chess-android-preview/blob/8563954429c2fb53ce0fe0e16c73c5d8a73ccfe0/tool/hardening/classification/reference/score.ts).
  Its original GPL-3.0 header is retained. As the header states, unrelated imports
  and formatting were removed in that upstream reference adaptation and a clamp
  supplied; this study makes no further edits to its functions.
- `current-v2/core.ts` is the unmodified Mute `ui/lib/src/nosweat/core.ts` from the
  same pinned native patch. It has no separate file-level license statement;
  Mute's repository is **AGPL-3.0-only**. The original header credits Maia3
  encoding/vocabulary to CSSLab `1e13597c` and Mobile Maia. Keep those source
  credits and [Mute's source/license notices](https://github.com/Dash1971/mute-chess/blob/b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12/THIRD_PARTY.md).
  The repository license is retained as [AGPL-3.0.txt](AGPL-3.0.txt).
- `current-v2/noSweatCore.ts` is only an import-path shim. The private
  `package.json` selects ESM; it declares no dependencies or build scripts.
  `current-v2/provenance.json` records exact source hashes, the verified native
  patch Git blob and upstream pins. Chessops, tsx and python-chess retain their
  respective distributions' licenses; they are not copied here.

## Runtime and exact commands

Run these commands **from the pilot directory**, one level above this file.
The checked-in evidence can be replayed without a browser, a server, Maia models,
or the original temporary application checkout.

Requirements: Node 24 (tested 24.22.1), tsx 4.23.15 and Chessops 0.15.1 for
TypeScript replay; Python 3 with python-chess for engine collection; Stockfish 18
for a new engine run. Point `reference/current-v2/node_modules` at any existing
compatible dependency directory. The pilot's local symlink is replaceable;
`/private/tmp` is not required.

Replay the included baseline and stronger evidence with the actual pinned rules:

```sh
node --import ./reference/current-v2/node_modules/tsx/dist/loader.mjs \
  ./replay.mts ./analysis-baseline.json ./analysis-stronger.json \
  ./comparison-rules-replayed.json
```

Baseline-only replay omits the optional stronger input:

```sh
node --import ./reference/current-v2/node_modules/tsx/dist/loader.mjs ./replay.mts
```

For a new fixed-engine collection, the script defaults to the exact local SF18
path recorded in the pilot. To use another installed path without editing the
frozen collector, override that task-specific constant and write a new output:

```sh
python3 -c 'import analysis; analysis.ENGINE="/path/to/stockfish"; analysis.main()' \
  baseline --output ./analysis-baseline-reproduced.json
```

The binary SHA-256, collector SHA-256, node budget and full position history are
recorded. Cached evidence is not reused across a changed engine or collector.
The original collection and analysis scripts enforce this pilot's fixed
**November 3, 2026, 00:47:02 UTC** deadline; they intentionally refuse a later
collection run without a separately approved study budget. Pure replay also
honors that deadline. These commands document the completed run, not permission
to restart or scale it.

## Interpreting outputs

`comparison-rules.json` separates raw eligibility, awards corroborated by actual
earlier complete iterations, and any supplied independent stronger window.
`stronger_window_decision` evaluates the stronger scores themselves;
`independent_stronger_confirmation` instead asks whether that window corroborates
the **baseline** decision. For a baseline negative label, the latter does not
replace its score with the stronger score. Owner regression controls are kept
separate from fresh Chess.com labels and excluded from their metrics.
