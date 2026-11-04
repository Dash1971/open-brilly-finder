# Methods, sources and reproduction

**Private review draft.** This is the technical companion to the [reader report](REPORT-DRAFT.md) and [exact algorithm](README-DRAFT.md). It documents a fixed-candidate experiment, not a native deployment or a recovered Chess.com formula.

## Study roles and sampling

The unified corpus contains **1,048 labeled moves from 545 games**. The **848-move, 439-game development partition** supplied feature development, diagnostic comparisons and the final frozen model. It contains 413 current observed Brilliants and 435 explicitly non-Brilliant controls. Every development result is treated as development evidence, including grouped cross-validation and engine-budget sensitivity.

The **200-move, 106-game fresh test** contains 100 current Brilliants and 100 explicit non-Brilliants. Each of nelsi, hansen, KNVB, GothamChess and Hikaru contributes 20 per class. Entire games and sampled positions are excluded across the development/test boundary; prior reviewed/regression examples are also excluded under the frozen plan. This test uses the final full-data forest, not the development fold-specific models.

Historical Chess.com galleries supply labeled candidate positions; published monthly full-game PGNs preserve history. Category availability differs by sampling frame and account. The test is deliberately balanced and its controls favor relevant captures, offers, recaptures and tactical alternatives; not every control is difficult or non-opening. Book and Forced are retained when explicitly observed. Gallery absence alone never supplies a negative label.

Candidate source, extractor, model, threshold, selection order and systematic reserves were frozen before current test labels. Explicit Game Review classifications determine the primary labels. A historical candidate that is currently non-Brilliant and an intended control that is currently Brilliant remain secondary rather than being relabeled. Fixed reserves satisfy the class quotas without consulting classifier predictions. The completed audit retains **10 secondary observations: six gallery-label differences and four Brilliant control attempts**. Those are not part of the 200 primary metrics.

This is a test within five established-player accounts, not new-player, beginner, account-independent or ordinary-game-distribution validation. Chess.com’s [published criteria](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) describe player-strength dependence. This model has no rating predictor or learned beginner curve. [Game Review documentation](https://support.chess.com/en/articles/8584089-how-does-game-review-work) explains why engine settings and deeper reviews can affect labels; current visible observations and historical gallery evidence retain distinct roles.

## Identity, labels and audit

The [completed core freeze](../future-validation-v5/CORE-FREEZE.json) binds the exact primary file and read-only research database. Numeric game ID, live/daily URL namespace, one-based ply, SAN/UCI, legal full-PGN replay and FEN identity are verified. All 200 selected positions have captured rendered-board identity; the audit reports no identity, namespace, old-game or position conflicts.

Current labels are observed interface classifications with timestamps and source URLs. No hidden site API, inferred gallery absence, coach text or observed label is a prediction input. Coach explanations are supplementary evidence and incomplete visible text is not silently completed. Missing optional evidence stays missing. Original public PGNs and private evidence remain traceable; cookies, credentials and private HTTP headers are not publication artifacts.

Core-freeze SHA-256:

```text
99bcffb5a77209f13e61bd0c495625950da6950c028ab9b64a5a1b8eea6a3394
```

[FINAL-AUDIT.json](../future-validation-v5/engine-core/FINAL-AUDIT.json) verifies all 106 PGN hashes and unchanged model, extractor, source, engine, database and primary-selection hashes. [Full predictions](../future-validation-v5/engine-core/fresh-results.json) join decisions to observed labels only for evaluation.

## Engine evidence and confidence

Core evidence uses pinned **Stockfish 18**, **300,000 requested nodes per position**, **one thread per worker**, **64 MB hash**, and **MultiPV 2 where two legal roots exist**. There are **581 distinct core snapshots**: the unique previous-own-after, target-before and target-after positions needed for all 200 moves. Each search receives full legal PGN history.

Four fixed whole-game partitions run independent existing collectors. Each clears hash and starts a new UCI game at a game boundary, processes positions chronologically and saves completed snapshots atomically. There is no prior-history warmup in the core bank, selective stronger-score substitution or retry of completed positions. The ten-minute worker safeguard did not trigger: maximum worker wall time was 64.19 seconds; aggregate recorded search work was 205.56 seconds. These timings describe this research run, not expected browser latency.

A snapshot keeps the final two **completed, exact, same-depth MultiPV iterations**, with distinct legal root moves and no bound-only scores. “Both windows” refers to the current and preceding completed engine iterations, not two different games or an invented duplicate score. Every core snapshot had actual preceding completed iterations. Terminal snapshots have a separate explicit convention; a missing nonterminal prior window is not manufactured.

The history rule’s label-independent structural coverage found one relevant earlier origin, already fully covered by core evidence. It required **zero supplemental searches** and had zero proof unknowns. Its [coverage, source freeze and predictions](../future-validation-v5/engine-s/results.json) remain separate from the forest’s feature extraction. No development-origin or different-budget window substitutes for test evidence.

The validated domain remains SF18/300k. Native Mute Chess SF19 and variable browser budgets are unvalidated. A TypeScript translation or parity check does not validate a changed engine, search budget, memory lifecycle or user-facing badge frequency.

## Fixed candidates and comparisons

The primary forest has 64 trees, maximum depth 6, minimum eight distinct original moves per leaf, 12 randomly sampled split features, seed 20261103 and non-Brilliant training cost 5. It uses 75 semantic values plus 75 missing indicators. Whole-game/identical-before-position groups are bootstrapped; current/prior windows stay linked. The final full-data model is frozen at SHA-256:

```text
44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7
```

The exact [feature definitions](../learning-v5/FEATURE-DEFINITIONS.json), [model](../learning-v5/forest-diagnostic/forest-full.json), [training protocol](../learning-v5/forest-diagnostic/PROTOCOL.json) and [standalone extractor freeze](../astra/v5/fresh-extractor/FREEZE.json) are authoritative. Hard quality/offer gates and the **5/6 raw mean-leaf threshold in each window** are unchanged. Mean leaf fractions are not calibrated probabilities. Required engine confidence is distinct from optional proof-feature unknownness.

S is the separate frozen history comparator, using confirmed unsuppressed A decisions for prior origins. Its effective temporal source SHA is `16faa288afc2e18716cdc7135efa8275712cd3b12624e4f696f33f25f6b3fe29`. Its [contract](../astra/v5/sequence-reference/PROSPECTIVE-CONTRACT.md) and [effective source freeze](../astra/v5/sequence-reference/source-freeze-castling-addendum.json) define repeat-offer suppression and the two finite forcing exceptions. It is not an extra hidden forest gate. A and v4 are saved secondary comparator outputs.

The peer is **direct En Croissant annotation** on identical current saved windows. Its material-sacrifice helper and best/second-root gap are preserved. Sources are pinned at [score.ts](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src/utils/score.ts) and [chess.rs](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src-tauri/src/chess.rs), verified byte-identical to [v0.15.1](https://github.com/franciscoBSalgueiro/en-croissant/releases/tag/v0.15.1). [The equivalence record](../../../mute-chess-research/studies/brilliant-moves/ec-latest-stable-check.json) contains the source hashes. This is a classifier comparison under common evidence, not identical whole-app engine behavior. EC with shared-window confirmation is also saved and happens to give the same test counts; it never silently replaces direct EC. Mobile Maia is unchanged.

## Outcomes and uncertainty

| Candidate | TP | FN | FP | TN | Agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen forest | 55 | 45 | 1 | 99 | 77.0% |
| S | 78 | 22 | 5 | 95 | 86.5% |
| EC direct | 26 | 74 | 2 | 98 | 62.0% |
| A | 78 | 22 | 6 | 94 | 86.0% |
| v4 | 78 | 22 | 6 | 94 | 86.0% |
| EC confirmed | 26 | 74 | 2 | 98 | 62.0% |

Metrics use separate denominators: recognition TP/(TP+FN), extra-control rate FP/(FP+TN), sample badge precision TP/(TP+FP), agreement (TP+TN)/N. An empty denominator is undefined, never automatically 100%. Overall and per-account descriptive 95% Wilson intervals are in the full results. The forest’s intervals are 45.24–64.39% recognition, 0.18–5.45% extra-control rate, 90.55–99.68% sample badge precision and 70.69–82.29% agreement.

Wilson intervals assume independent moves; games contribute multiple moves, so these are **not game-cluster-adjusted intervals**. Five accounts also limit generalization. The comparison is paired, but a count of one extra award versus two does not prove a universal lower error rate. Balanced/enriched controls do not identify natural-game prevalence or deployment precision. No 90% agreement goal is claimed achieved.

There were no physical-feature timeouts, insufficient-confidence cases or S proof unknowns. Four avoidability proofs were unknown in both windows and retained fixed missing routing. Other None values include alternate cp/mate fields, absent top-two played roots, absent safe alternatives and no-offer physical features. Do not count all 2,724 None fields as proof failures. Exact counts and every feature/proof/decision trace are saved.

Development diagnostic results are not pooled with the fresh test. Forest grouped out-of-fold results are 223 TP / 2 FP versus EC direct 113 / 7; full-model training 247 / 0 is resubstitution. The [small-tree](../learning-v5/README.md), [surprise](../learning-v5/surprise-extension/README.md), [rating](../learning-v5/rating-extension/README.md) and [forest](../learning-v5/forest-diagnostic/PROTOCOL.json) audits preserve unsuccessful directions. A uniform [1.5m-node sensitivity check](../uniform-stronger-v5/README.md) did not solve the matching problem: S changes 322/19 to 323/18, while the fixed full-data forest changes 247/0 to 240/1 on development evidence. That is not another fresh test or permission to mix budgets.

## Figures, native assets and illustration truth

The [two-panel chart source](reader-figures.py) reads only the completed test summary, asserts 200 moves/106 games and class denominators of 100, and writes PNG/SVG plus a plotted-count/input-hash receipt. It uses Mute Moss colors `#C7CFBA` and `#668478`, graphite text and native gold `#D9B25F`. Recognition and extra controls have separate panels; precision is not plotted as agreement.

The successful illustration is **Hansen 17.Bxh7+**, fresh-test game `167741829524`, ply 33. Current Chess.com Brilliant and the unchanged forest award agree. The public PGN verifies both **Bxh7+ Kxh7** as actual moves; [the receipt](illustration-proof.json) includes their legal states and PGN hash. Only Bxh7+ is the labeled target. Acceptance is not claimed forced; no compensation or mate line is invented.

Hikaru’s development **27.Bg2** is a documented forest miss that S recognizes. Its subsequent **...Bxb1 Rxb1** moves are a conditional legal illustration, not asserted game replies. Both outside pawn-winning references remain excluded from all 1,048 benchmark moves; the forest withholds both the Excellent Ndxe5 and Brilliant Nxd5 reference. Those capture lines are also conditional, not forced.

Boards use the existing native renderer, Mute Chess **Moss** square colors, native translucent gold highlights and the exact **Cburnett SVG pieces by Colin M. L. Burnett, GPL-2.0-or-later**. Original vectors and the complete license accompany [asset provenance](../visuals/ASSET-PROVENANCE.json), [renderer and credits](../visuals/README.md), and the pinned [rasterizer receipt](../visuals/RASTERIZER-PROVENANCE.json). No AI-generated artwork or Unicode-piece substitutes are used. The existing animation uses eased piece motion, short capture fades and a fixed palette; every state is legally replayed.

Reproduce the private chart and successful illustration from this directory:

```sh
python3 reader-figures.py
python3 ../visuals/render-boards.py --cases illustration-cases.json --case fresh-bxh7 --formats png,svg,gif --output figures
```

Use the existing recorded Matplotlib/Pillow/Python-chess dependencies and cached native assets; do not install a new rendering framework. The original SVGs/license must remain with published derivatives. Private report links need remapping only when the publication allowlist is finalized; no public write or deployment is implied by these drafts.
