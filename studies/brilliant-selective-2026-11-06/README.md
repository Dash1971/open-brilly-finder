# Mute Selective: exact algorithm and reproduction

[Read the report](REPORT.md) · [Methods](METHODS.md) · [Download all seven accounts](data/seven-accounts-last-12-months-chesscom-brilliants.pgn)

Mute Selective uses a trained 128-tree forest with a **0.83** cutoff in each completed engine window. Model SHA-256: `1a7150fbe52f440922d94d3ae2af337383d63f370b52d0379aeee22d581d056c`. [Native source and weights](reference/native/ui/analyse/src/) are published unchanged. Full-game confirmation preserves the preceding, before-move and after-move positions when available. The source mapping is documented in [Methods](METHODS.md).

## Award rule

For each of two completed windows (current and previous), the engine evidence must be complete, the before-position must have at least two root lines, the move must make a legal piece offer, mapped win-chance loss must be at most **5 percentage points**, and the mover’s after-position score must be at least **−100 centipawns**. The classification integration preserves ordinary error rejections. Required physical proof that runs out of its budget causes abstention.

The forest uses **75 chess features and 75 explicit missing-value indicators**, covering move quality, material/phase, piece roles, legal offers, immediate gains, exchange recovery, mating acceptance, offer attribution, safe winning alternatives, and bounded proof results. Exact names and extraction are in [noSweatBrilliantForest.ts](reference/native/ui/analyse/src/noSweatBrilliantForest.ts) and the model’s `features` array. Account, game ID, date, gallery category, coach text, and rating are not predictors. Missing optional evidence remains `null`, with a missing indicator; it is not a fabricated zero or a proof of failure.

A split goes left for a missing value or `value <= threshold`. Each leaf stores its raw positive fraction. A window’s score is the arithmetic mean of its 128 leaf fractions:

`score(window) = sum(tree_leaf.raw_p) / 128`

A final Brilliant requires **both** window scores `>= 0.83`, both windows eligible, known required physical evidence, and sufficient confidence. Confidence requires consistent nonempty review-quality tags and, when confirmation is present, compatible quality/depth/terminal evidence. Scores are learned similarity scores, not calibrated probabilities of Chess.com agreement. The integration’s exact checks are in [noSweatClassify.ts](reference/native/ui/analyse/src/noSweatClassify.ts).

Proof caps and ordering are part of the algorithm: avoidability and attribution use 512-node budgets; physical recovery uses 10,000 nodes / 250 ms; its same-square exchange helper is capped at 100,000 nodes / 1,000 ms. See see the constants, `ProofTimeout`, and bounded physical/avoidability/attribution searches in the native feature extractor. Optional unknowns are preserved; required physical unknowns withhold the badge. This is ordinary local tree traversal and chess search, not a remote AI call or a neural network. Mobile Maia’s En Croissant policy is unchanged.

## Recount the published results

From the repository root, Python 3 standard library is enough:

```sh
python3 studies/brilliant-selective-2026-11-06/reproduce.py
python3 tools/infer_saved_features.py --model selective20261106 --case-key 1006812690:48
```

The first command checks every published move outcome against the frozen matrices and model hash. The second uses already-extracted feature windows; it does not analyze a new FEN or reproduce full engine confirmation.

## Complete scientific artifacts

[Source manifest](SOURCE-MANIFEST.json) lists every archive member, original and published hashes, exclusions, and portable path normalization. Extract the numbered archives into a new empty directory to recover the `research/` source layout:

```sh
mkdir extracted
for archive in studies/brilliant-selective-2026-11-06/data/archives/*.tar.gz; do
  tar -xzf "$archive" -C extracted
done
```

Archives contain the complete search recipes/scout/promoted results, every fold and full-fit model, fitting cases and splits, original PGNs/gallery evidence, full replay inputs, initial/confirmation engine outputs, raw decisions, summaries, audits, and preserved failed/partial attempts. Duplicate generated runtime bundles, installed packages, and operational logs are omitted explicitly. They do not contain additional labels or scientific decisions. Relative source-link reconstruction receipts are in the manifest; no private runtime installation is bundled.

Saved-feature reproduction needs no dependencies. Retraining uses the archived `prepare.py`, `fit_worker.py`, `choose.py`, `MANIFEST.json`, `CASES.json`, `DATA.npz`, and pinned `capacity-tree.py`; original NumPy/scikit-learn/threadpoolctl versions and seeds are recorded. Full native replay additionally needs the pinned chessops/badrap sources, build tools, engine assets, and the original Node 24 environment. Original inputs and outcomes are included so the evidence can be audited without rerunning thousands of engine searches. Publication path changes are recorded separately from unchanged scientific values; original freeze hashes identify original source bytes.

## Engine settings

The fresh test used **Stockfish 19 smallnet (1 MB), native Fast: depth 12 / 500 ms initial searches, depth 14 / 500 ms confirmation, one thread, 16 MB hash, at most six confirmation searches per variant per game**. Full PGN history and both colors’ positions are preserved. Results establish behavior under these settings, not every browser, engine, budget, or player. App release information belongs in the [Mute Chess repository](https://github.com/Dash1971/mute-chess).
