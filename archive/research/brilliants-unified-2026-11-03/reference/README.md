# Pinned rules and reproduction

These source copies support the unified 618-move comparison. They are study inputs, not new application dependencies. The Mute material guard was selected with development examples, then held fixed for prospective checks and reserved-game validation; see [methods](../METHODS.md).

## Sources and licenses

- `current-v2/noSweatClassify.ts` is an unmodified copy from Mute main [`b3585f2`](https://github.com/Dash1971/mute-chess/tree/b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12), carried by `deploy/lila/patches/lila-nostr-maia.patch`. Its header identifies the En Croissant / Mobile Maia port as **GPL-3.0**. [GPL license](GPL-3.0.txt).
- `proposed-v3/noSweatClassify.ts` is the unmodified candidate from [`ac298a0`](https://github.com/Dash1971/mute-chess/tree/ac298a0d69ab51808857b089063348f2adac1101). The added Mute gate requires EC material corroboration or an explicit winning mate. EC annotation rules remain unchanged.
- Each `core.ts` is the unmodified Mute `ui/lib/src/nosweat/core.ts` from its pinned native patch. Mute is **AGPL-3.0-only**. Its original header credits Maia3 encoding/vocabulary to CSSLab `1e13597c` and Mobile Maia; retain these credits and [Mute's notices](https://github.com/Dash1971/mute-chess/blob/ac298a0d69ab51808857b089063348f2adac1101/THIRD_PARTY.md). [AGPL license](AGPL-3.0.txt).
- `noSweatCore.ts` is an import-path shim. `package.json` only selects ESM. Each `provenance.json` records exact source hashes, native patch blobs and adaptations. The replay rejects changed pinned source bodies.
- `ec-score.ts` is the existing standalone scoring oracle from [Mobile Maia preview `8563954`](https://github.com/Dash1971/maia-chess-android-preview/blob/8563954429c2fb53ce0fe0e16c73c5d8a73ccfe0/tool/hardening/classification/reference/score.ts). Its original GPL header documents removed unrelated imports/formatting and the supplied clamp. This study makes no further function edits. Original [EC scoring source](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src/utils/score.ts).
- Latest stable EC v0.15.1 scoring and material files were verified byte-identical to that pinned reference. [Blob evidence](../ec-latest-stable-check.json). This checks code equivalence, not identical application search budgets.

## Replay saved inputs

Requirements: **Node 24** (tested 24.22.1), **tsx 4.23.15**, **Chessops 0.15.1**. From the study directory, use an existing compatible dependency directory, or install those exact versions into a temporary directory. Point both `reference/current-v2/node_modules` and `reference/proposed-v3/node_modules` at it. Dependencies and local symlinks are not published. Their distributions retain their own licenses.

No browser, application checkout, Maia models, database or engine is needed to replay the saved evidence:

```sh
node --import ./reference/current-v2/node_modules/tsx/dist/loader.mjs \
  ./replay.mts ./analysis-baseline.json "" ./comparison-v2-replayed.json
node --import ./reference/proposed-v3/node_modules/tsx/dist/loader.mjs \
  ./replay-v3.mts ./analysis-baseline.json "" ./comparison-v3-replayed.json
```

To reproduce the separate stronger-window outputs, replace the empty argument with `./analysis-stronger.json` and use new output filenames. `comparison-v2-stronger.json` and `comparison-v3-stronger.json` retain baseline decisions alongside targeted stronger decisions; do not mistake their baseline summary for a sensitivity summary. The latter is [sensitivity-summary.json](../sensitivity-summary.json).

`stronger_window_decision` evaluates the stronger scores themselves. `independent_stronger_confirmation` asks whether stronger evidence corroborates the **baseline** decision; it does not promote a baseline non-award using a better score. Whole-window confirmation is part of Mute's production behavior. The headline EC comparator is direct annotation, without adding Mute's shared-window withholding filter.

## New engine runs and figures

Python 3 plus python-chess and the recorded Stockfish 18 binary support new engine runs. `analysis.py` reads `corpus.sqlite3` and `primary-moves.json`; write new outputs and preserve the published evidence:

```sh
python3 -c 'import analysis; analysis.ENGINE="/path/to/stockfish"; analysis.main()' \
  baseline --output ./analysis-baseline-reproduced.json
```

Each frozen targeted stronger subset in `sensitivity/` can be passed separately with `stronger --subset PATH --output NEW_PATH`. Each is capped at 30 targets. `manifest.json` preserves the original cohort collector hashes and session boundaries of the merged evidence. A new run records its own collector hash, engine hash and node budget; cached evidence is not reused across incompatible provenance. Search session/hash history can cause new engine runs to differ. Report differences rather than forcing labels to match.

The study contains 618 moves; legacy internal quality strings containing `study600` identify original evidence and have no bearing on inclusion. The scripts' actual quantity guard is 618. Rule source hashes are unchanged.

`python3 summarize.py` regenerates move-level outputs and the baseline summary from saved inputs (requires python-chess). `python3 reader-figures.py` regenerates figures from the summary and illustrative cases (requires python-chess, matplotlib and Pillow). Figures contain legal illustrative variations, not claims about forced lines or actual game continuations. Public PGNs contain primary games only; HTTP headers, cookies and session state are excluded.
