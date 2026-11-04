# Fixed model and readable reference

The current recommendation is **Mute Selective**, the fixed model with its original chess eligibility gates. [The exact algorithm](../../README.md) explains its 75 features, 64 trees and both-window 5/6 threshold. The [History sources](astra/v5/variants/variantA.ts), [temporal proof](astra/v5/sequence-reference/temporalProof.ts) and [material-recovery guard](../history-recovery/candidate.py) remain comparisons, not required gates for Mute Selective.

This is the current fixed-model reproduction path. The model bytes, scientific source and numeric rules are unchanged. Historical study-root scripts describe earlier evidence; native SF19 accuracy remains separate from saved-input parity.

## Frozen sources and portability

The original research-relative layout is retained so TypeScript imports remain unchanged. The 64-tree model is byte-identical, SHA-256 `44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7`. Python adaptations remove private dependency-search paths, select Node/tsx through the environment, and resolve the included physical helper relatively. Numeric algorithms, guards, thresholds and proof caps are unchanged. [SOURCE-PATH-NORMALIZATION.json](SOURCE-PATH-NORMALIZATION.json) records every original and published SHA plus the exact path-only substitutions. Original freeze hashes remain source identities, not a claim that adapted files retain those hashes.

The original [archived material helper](../../../brilliant-moves-2026-11-03/material-features.py) is untouched. A small path-normalized copy is included at [physical-reference/material-features.py](physical-reference/material-features.py); its mapping is recorded. No database is duplicated inside this reference directory.

## Replay without an engine

Requirements: Python3, `python-chess==1.999` (chess module1.11.2), Node24.22.1, `tsx==4.23.15`, `chessops==0.15.1`. Use an existing compatible environment; exact Node package versions are in [package.json](package.json). Node dependencies must be resolvable from this directory, normally its local `node_modules`. Dependency distributions and their licenses are not vendored. Do not commit local symlinks, installed modules or binaries.

The portable extractor reads requests on stdin. Each contains only full PGN, one-based ply and ordered recorded snapshots; identities/labels are not predictors:

```sh
node --version
python3 astra/v5/fresh-extractor/extractor.py < requests.json > predictions.json
```

Set `MUTE_RESEARCH_NODE` and `MUTE_RESEARCH_TSX_LOADER` if using a preexisting Node/tsx installation outside PATH. The default loader is `reference/v5/node_modules/tsx/dist/loader.mjs`. The [contract](astra/v5/fresh-extractor/CONTRACT.md) specifies exact inputs, validation, finite proof caps, missingness and SF18/300k limits. No fitting or engine search is needed to score saved windows.

Saved test features/decisions are [data/test-forest-predictions.json](../../data/test-forest-predictions.json); all paired classifier traces and Wilson intervals are [data/test-results.json](../../data/test-results.json). The database and selected public PGNs live once at the study root. Main reproduction figures use `python3 reader-figures.py` from the study root with Matplotlib; native boards use the existing Pillow/resvg renderer and its recorded dependencies.

## Native TypeScript prototype

[native/noSweatBrilliantForest.ts](native/noSweatBrilliantForest.ts), its unchanged model and actual classifier are readable source copies. [The final-source mapping](native/PATH-PROVENANCE.json) pins the module and classifier; its only module-resolution shim points to the byte-identical included native core. The native implementation adds an explicit `physicalUnknown` withholding guard. No such timeout occurred among the1,048 recorded cases, so this extra abstention did not change their awards.

The [saved parity result](native/parity.json) reports zero feature/missingness, award, integrated-classifier or EC-result differences on the1,048 recorded SF18 inputs (maximum floating difference2.84e−14). This is implementation parity on recorded evidence, not another fresh accuracy test. The earlier port summary retains its original source hash; use PATH-PROVENANCE for final current source identities. Native SF19 and varying budgets remain unvalidated, and no merge/deployment is claimed.

## Attribution and licenses

Mute Chess source and the study-local derived feature/model/reference code follow the repository's **AGPL-3.0-only** [license](../../../../LICENSE). The copied En Croissant-derived scoring classifier carries **GPL-3.0** notices; retain [GPL-3.0](../GPL-3.0.txt) and original headers. The core retains CSSLab Maia3 `1e13597c` and Mobile Maia credits; see [Mute's third-party notices](https://github.com/Dash1971/mute-chess/blob/main/THIRD_PARTY.md). Python-chess, Chessops and tsx keep their upstream licenses. Board derivatives separately retain Colin M. L. Burnett's Cburnett **GPL-2.0-or-later** notices and complete license under [visuals](../../visuals/README.md). Research and preparation used OpenAI Codex assistance.

The earlier 618-move report and source release remain available through [commit c6969d1](https://github.com/Dash1971/mute-chess-research/tree/c6969d1/studies/brilliant-moves), without another copy of its database.
