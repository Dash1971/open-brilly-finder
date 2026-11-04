# Methods, sources and reproduction

**Current recommendation: Mute Selective, the fixed model plus its original chess rules.** The headline evidence is 400 test moves from 215 games, not training fit. Selective 112TP/88FN/3FP/197TN versus EC 53/147/3/197; the newest 200 alone gives 57/43/2/98 versus EC 27/73/1/99. The separate History Rule’s 78/22/13/87 found more Brilliants but gave too many extra badges to justify choosing it. No model, feature, threshold or algorithm was changed for this comparison.

## Selective-model test roles

The full model 44704ac… was trained on 848 development moves and frozen before both 200-move tests. The first test has 106 games; the newest has 109, with no game overlap, giving 400 test moves/ 215 games and 200 positions per class. Sources, weights, eligibility gates and 5/6 per-window threshold remain unchanged. The newest replay uses already captured SF18/300k core windows: no extra searches, tuning or training. [RUN-FREEZE](data/selective-replay/RUN-FREEZE.json), [new results](data/selective-replay/RESULTS.json), [raw feature/score decisions](data/selective-replay/predictions.json) and the [joined 400 rows](data/selective-independent-tests.json) retain exact inputs and hashes.

These games were not used for fitting or threshold selection. The decision to choose this method follows inspection of comparisons, so the combined result is not a new blind test of the policy-selection process. Account/game clustering and balanced hard-control sampling limit generalization; the sample badge fraction 112/115 must not be read as calibrated production precision. The next step is fixed future candidates tested on new games, not post-test threshold adjustment.

The material-recovery guard and History Rule are retained as comparisons only. Native 10-game execution evidence below tested that History path, not the selected fixed model. The selected model’s SF19/variable-budget/browser domain therefore remains unvalidated. Earlier evidence sections remain historical and must not be pooled into the 400 test headline.


**History Rule comparison (not the selected recommendation).** On 200 fresh moves from 109 games, the unchanged rule and core rule each give 78TP/22FN/13FP/87TN (82.5% agreement), versus direct En Croissant 27/73/1/99 (63.0%). Thirteen false awards among 100 controls remain an important limit and a target for further refinement. There was no guard-specific decision difference. The combined 1,248-move/654-game descriptive counts are 478/135/35/600 (86.4%) versus EC 166/447/10/625 (63.4%). Combined totals include development examples and must not replace the fresh-test estimate. [New evidence and audits](data/prospective-history/PRIMARY-AUDIT.json) and [combined move-level results](data/combined-history-results.json) accompany the update.


**Historical History Rule comparison.** The refinement’s all 1,048 replay gives 400TP/113FN/22FP/513TN, removing exactly two extras while retaining all 400 previous matches. It was designed after inspecting these labels, including the historical 200 test. **All 1,048 are development for the refinement, the replay itself supplies no unseen validation; the separate 200-move assessment is reported above.** The unrefined frozen S 200 result 78/22/5/95 remains independent evidence only for that earlier base rule. Native SF19 and varying budgets remain unvalidated.

This is the technical companion to the [reader report](REPORT.md) and [exact algorithm](README.md). It documents a fixed-candidate experiment, not a native deployment or a recovered Chess.com formula.

## Evidence roles: historical test versus retrospective refinement

The unified corpus contains **1,048 labeled moves from 545 games**. The **848-move, 439-game development partition** supplied feature development, diagnostic comparisons and the final frozen model. It contains 413 current observed Brilliants and 435 explicitly non-Brilliant controls. Every development result is treated as development evidence, including grouped cross-validation and engine-budget sensitivity.

The **200-move, 106-game fresh test** contains 100 current Brilliants and 100 explicit non-Brilliants. Each of nelsi, hansen, KNVB, GothamChess and Hikaru contributes 20 per class. Entire games and sampled positions are excluded across the development/test boundary; prior reviewed/regression examples are also excluded under the frozen plan. The rule and all comparators were fixed before fresh labels. The forest comparison uses its final full-data model, not development fold-specific models.

Historical Chess.com galleries supply labeled candidate positions; published monthly full-game PGNs preserve history. Category availability differs by sampling frame and account. The test is deliberately balanced and its controls favor relevant captures, offers, recaptures and tactical alternatives; not every control is difficult or non-opening. Book and Forced are retained when explicitly observed. Gallery absence alone never supplies a negative label.

For the original S/forest/EC comparison, candidate source, extractor, model, threshold, selection order and systematic reserves were frozen before current test labels. Those archived sources/results remain unchanged. This statement does not describe the new material guard, which uses all 1,048 as development. Explicit Game Review classifications determine the primary labels. A historical candidate that is currently non-Brilliant and an intended control that is currently Brilliant remain secondary rather than being relabeled. Fixed reserves satisfy the class quotas without consulting classifier predictions. The completed audit retains **10 secondary observations: six gallery-label differences and four Brilliant control attempts**. Those are not part of the 200 primary metrics.

This is a test within five established-player accounts, not new-player, beginner, account-independent or ordinary-game-distribution validation. Chess.com’s [published criteria](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) describe player-strength dependence. This model has no rating predictor or learned beginner curve. [Game Review documentation](https://support.chess.com/en/articles/8584089-how-does-game-review-work) explains why engine settings and deeper reviews can affect labels; current visible observations and historical gallery evidence retain distinct roles.

## Identity, labels and audit

The [completed core freeze](data/protocol/CORE-FREEZE.json) binds the exact primary file and read-only research database. Numeric game ID, live/daily URL namespace, one-based ply, SAN/UCI, legal full-PGN replay and FEN identity are verified. All 200 selected positions have captured rendered-board identity; the audit reports no identity, namespace, old-game or position conflicts.

Current labels are observed interface classifications with timestamps and source URLs. No hidden site API, inferred gallery absence, coach text or observed label is a prediction input. Coach explanations are supplementary evidence and incomplete visible text is not silently completed. Missing optional evidence stays missing. Original public PGNs and private evidence remain traceable; cookies, credentials and private HTTP headers are not publication artifacts.

Core-freeze SHA-256:

```text
99bcffb5a77209f13e61bd0c495625950da6950c028ab9b64a5a1b8eea6a3394
```

[FINAL-AUDIT.json](data/protocol/FINAL-AUDIT.json) verifies all 106 PGN hashes and unchanged model, extractor, source, engine, database and primary-selection hashes. [Full predictions](data/test-results.json) join decisions to observed labels only for evaluation.

## Engine evidence and confidence

Core evidence uses pinned **Stockfish 18**, **300,000 requested nodes per position**, **one thread per worker**, **64 MB hash**, and **MultiPV 2 where two legal roots exist**. There are **581 distinct core snapshots**: the unique previous-own-after, target-before and target-after positions needed for all 200 moves. Each search receives full legal PGN history.

Four fixed whole-game partitions run independent existing collectors. Each clears hash and starts a new UCI game at a game boundary, processes positions chronologically and saves completed snapshots atomically. There is no prior-history warmup in the core bank, selective stronger-score substitution or retry of completed positions. The ten-minute worker safeguard did not trigger: maximum worker wall time was 64.19 seconds; aggregate recorded search work was 205.56 seconds. These timings describe this research run, not expected browser latency.

A snapshot keeps the final two **completed, exact, same-depth MultiPV iterations**, with distinct legal root moves and no bound-only scores. “Both windows” refers to the current and preceding completed engine iterations, not two different games or an invented duplicate score. Every core snapshot had actual preceding completed iterations. Terminal snapshots have a separate explicit convention; a missing nonterminal prior window is not manufactured.

The history rule’s label-independent structural coverage found one relevant earlier origin, already fully covered by core evidence. It required **zero supplemental searches** and had zero proof unknowns. Its [coverage, source freeze and predictions](data/test-sequence-results.json) remain separate from the forest’s feature extraction. No development-origin or different-budget window substitutes for test evidence.

The validated domain remains SF18/300k. Native Mute Chess SF19 and variable browser budgets are unvalidated. A TypeScript translation or parity check does not validate a changed engine, search budget, memory lifecycle or user-facing badge frequency.

## Fixed candidates and comparisons

The comparison forest has 64 trees, maximum depth 6, minimum eight distinct original moves per leaf, 12 randomly sampled split features, seed 20261103 and non-Brilliant training cost 5. It uses 75 semantic values plus 75 missing indicators. Whole-game/identical-before-position groups are bootstrapped; current/prior windows stay linked. The final full-data model is frozen at SHA-256:

```text
44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7
```

The exact [feature definitions](reference/v5/learning-v5/FEATURE-DEFINITIONS.json), [model](reference/v5/learning-v5/forest-diagnostic/forest-full.json), [training protocol](reference/v5/learning-v5/forest-diagnostic/PROTOCOL.json) and [standalone extractor freeze](reference/v5/astra/v5/fresh-extractor/FREEZE.json) are authoritative. Hard quality/offer gates and the **5/6 raw mean-leaf threshold in each window** are unchanged. Mean leaf fractions are not calibrated probabilities. Required engine confidence is distinct from optional proof-feature unknownness.

S is the frozen base History Rule, using confirmed unsuppressed A decisions for prior origins. Its effective temporal source SHA is `16faa288afc2e18716cdc7135efa8275712cd3b12624e4f696f33f25f6b3fe29`. Its [contract](reference/v5/astra/v5/sequence-reference/PROSPECTIVE-CONTRACT.md) and [effective source freeze](reference/v5/astra/v5/sequence-reference/source-freeze-castling-addendum.json) define repeat-offer suppression and the two finite forcing exceptions. It is not an extra hidden forest gate. A and v4 are saved secondary comparator outputs.

The peer is **direct En Croissant annotation** on identical current saved windows. Its material-sacrifice helper and best/second-root gap are preserved. Sources are pinned at [score.ts](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src/utils/score.ts) and [chess.rs](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src-tauri/src/chess.rs), verified byte-identical to [v0.15.1](https://github.com/franciscoBSalgueiro/en-croissant/releases/tag/v0.15.1). [The equivalence record](ec-latest-stable-check.json) contains the source hashes. This is a classifier comparison under common evidence, not identical whole-app engine behavior. EC with shared-window confirmation is also saved and happens to give the same test counts; it never silently replaces direct EC. Mobile Maia is unchanged.


## Material-recovery refinement: fixed retrospective audit

The [new guard plan](data/history-recovery-plan.json), [candidate](reference/history-recovery/candidate.py), [material proof](reference/history-recovery/probe.py) and [path/source map](reference/history-recovery/SOURCE-MAPPING.json) specify one conjunction; there was no ID/account/label filter in prediction and no model refit. This is a label-informed refinement, not a new untouched test. Both former partitions are development for this rule. The new-game check above is separate from this historical replay.

The guard only acts on existing S awards for non-checking captures that do not face check or promote. Every qualifying offer must be of an unmoved piece and have identical legal attacker/victim geometry and same-square liability on a before-position clone whose side is flipped and en-passant square cleared. Both completed **after-position first roots** must accept qualifying old offers. For every qualifying acceptance, one quiet noncapturing/nonpromoting response must cover **every legal defense**, with a legal nonchecking, nonterminal recovery capture stabilized against maximum same-square recapture liability. Its mover material must reach at least pre-target balance minus 100. All tests share 100,000 nodes/one second. Any incompleteness or exhaustion leaves the original S decision unchanged. Exact definitions are in the [README](README.md#added-guard-existing-offer-material-recovery).

The retrospective [1,048-row outcomes](data/history-recovery-results.json) change exactly two non-Brilliant awards: nelsi 18...hxg6 (`171488501692:36`) and hansen 15...hxg5 (`173517772799:30`). Original S: 400TP/113FN/24FP/511TN; refined: 400TP/113FN/22FP/513TN. All 400 previously matching awards remain, with zero proof unknowns. The [independent audit](data/history-recovery-audit.json) replays the source and checks the legal witnesses, all four defenses after Qc5+ and all 43 after Ba6, and the final SEE-adjusted material condition.

Within the historical 200 subset, the new result is 78TP/22FN/3FP/97TN. This is a **retrospective subset replay**, not a replacement independent score. Keep the untouched original S 78/22/5/95 below and do not quote the refined subset as fresh validation. The two targeted corrections and no observed lost true awards support a narrow development claim; they do not establish future sensitivity, deployment precision or a 90% agreement result.

## Historical frozen-rule outcomes and uncertainty

| Candidate | TP | FN | FP | TN | Agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| History Rule S — comparison | 78 | 22 | 5 | 95 | 86.5% |
| Selective forest — comparison | 55 | 45 | 1 | 99 | 77.0% |
| EC direct | 26 | 74 | 2 | 98 | 62.0% |
| A | 78 | 22 | 6 | 94 | 86.0% |
| v4 | 78 | 22 | 6 | 94 | 86.0% |
| EC confirmed | 26 | 74 | 2 | 98 | 62.0% |

Metrics use separate denominators: recognition TP/(TP+FN), extra-control rate FP/(FP+TN), sample badge precision TP/(TP+FP), agreement (TP+TN)/N. An empty denominator is undefined, never automatically 100%. Overall and per-account descriptive 95% Wilson intervals are in the full results. The forest’s intervals are 45.24–64.39% recognition, 0.18–5.45% extra-control rate, 90.55–99.68% sample badge precision and 70.69–82.29% agreement.

Wilson intervals assume independent moves; games contribute multiple moves, so these are **not game-cluster-adjusted intervals**. Five accounts also limit generalization. The comparison is paired, but a count of one extra award versus two does not prove a universal lower error rate. Balanced/enriched controls do not identify natural-game prevalence or deployment precision. No 90% agreement goal is claimed achieved.

There were no physical-feature timeouts, insufficient-confidence cases or S proof unknowns. Four avoidability proofs were unknown in both windows and retained fixed missing routing. Other None values include alternate cp/mate fields, absent top-two played roots, absent safe alternatives and no-offer physical features. Do not count all 2,724 None fields as proof failures. Exact counts and every feature/proof/decision trace are saved.

<a id="development-audits"></a>

Development diagnostic results are not pooled with the fresh test. Forest grouped out-of-fold results are 223 TP / 2 FP versus EC direct 113 / 7; full-model training 247 / 0 is resubstitution. The [small-tree](METHODS.md#development-audits), [surprise](METHODS.md#development-audits), [rating](METHODS.md#development-audits) and [forest](reference/v5/learning-v5/forest-diagnostic/PROTOCOL.json) audits preserve unsuccessful directions. A uniform [1.5m-node sensitivity check](METHODS.md#development-audits) did not solve the matching problem: S changes 322/19 to 323/18, while the fixed full-data forest changes 247/0 to 240/1 on development evidence. That is not another fresh test or permission to mix budgets.

## Figures, native assets and illustration truth

The [chart source](reader-figures.py) distinguishes the retrospective refinement replay from preserved historical test charts, asserts appropriate class denominators (513/535 versus 100/100), and writes PNG/SVG plus plotted-count/input-hash receipts. It uses Mute Moss colors `#C7CFBA` and `#668478`, graphite text and native gold `#D9B25F`. Recognition and extra controls have separate panels; precision is not plotted as agreement.

The retained History Rule illustration is **Hansen 17.Bxh7+**, fresh-test game `167741829524`, ply 33. Current Chess.com Brilliant and the unchanged History Rule award agree (the comparison forest also awards it). The public PGN verifies both **Bxh7+ Kxh7** as actual moves; [the receipt](visuals/fresh-success-proof.json) includes their legal states and PGN hash. Only Bxh7+ is the labeled target. Acceptance is not claimed forced; no compensation or mate line is invented.

Hikaru’s development **27.Bg2** is a documented forest miss that S recognizes. Its subsequent **...Bxb1 Rxb1** moves are a conditional legal illustration, not asserted game replies. Both outside pawn-winning references remain excluded from all 1,048 benchmark moves; the forest withholds both the Excellent Ndxe5 and Brilliant Nxd5 reference. Those capture lines are also conditional, not forced.

Boards use the existing native renderer, Mute Chess **Moss** square colors, native translucent gold highlights and the exact **Cburnett SVG pieces by Colin M. L. Burnett, GPL-2.0-or-later**. Original vectors and the complete license accompany [asset provenance](visuals/ASSET-PROVENANCE.json), [renderer and credits](visuals/README.md), and the pinned [rasterizer receipt](visuals/RASTERIZER-PROVENANCE.json). No AI-generated artwork or Unicode-piece substitutes are used. The existing animation uses eased piece motion, short capture fades and a fixed palette; every state is legally replayed.

Reproduce the chart and successful illustration from this directory:

```sh
python3 reader-figures.py
python3 visuals/render-boards.py --cases visuals/cases-fresh-test.json --case fresh-bxh7 --formats png,svg,gif --output visuals/outputs
```

Use the existing recorded Matplotlib/Pillow/Python-chess dependencies and cached native assets; do not install a new rendering framework. The original SVGs/license accompany these derivatives. These reference materials do not imply a deployed native classifier.


## Native prototype and recorded-input parity

A bounded [TypeScript reference port](reference/v5/README.md#native-typescript-prototype) reproduces all 75 features, missingness, scores and integrated decisions on the **1,048 recorded SF18 cases**, including the 200-move test, with no award or EC-result differences (maximum floating difference 2.84e−14). This is implementation parity, not another accuracy test or a claim of native SF19 validation. The native prototype adds an explicit physical-probe-timeout withholding guard; no such timeout occurred on these cases, so this additional abstention did not change their outputs. Frozen research decisions and the native guard remain distinct contracts.

Native module SHA-256: `10ac40a04d29492e85d09ddfbd0ac5c8ab32f64a8dce28cb6d78cd1cecbfb499`; classifier SHA-256: `be222880d7158a6ae3604bd482cb1e218d69c59ee815ea0a0c6ad34e4f1b18c9`. The [source/path audit](reference/v5/native/PATH-PROVENANCE.json) and [parity trace](reference/v5/native/parity.json) accompany the readable reference. No merge or deployment is claimed. **The separate fixed SF19 assessment below is limited; variable-budget and browser validation remain limited.**

The earlier 618-move report is archived by [commit c6969d1](https://github.com/Dash1971/mute-chess-research/blob/c6969d1/studies/brilliant-moves/REPORT.md); no duplicate historical database is required.

The two new native-board recovery animations are generated from [cases-recovery.json](visuals/cases-recovery.json). Every move is legal; only the first target has the recorded Best label. Their subsequent branches are conditional illustrations, not asserted game moves or unique forced choices. The complete 4/43-defense certificates live in the audit, not merely in the displayed branch.

## Native refined-rule reference

The readable [native History Rule and recovery integration](reference/native-history-v7/ui/analyse/src/noSweatClassify.ts), [source mapping](reference/native-history-v7/SOURCE-MAPPING.json), [summary](reference/native-history-v7/SUMMARY.json) and [parity trace](reference/native-history-v7/parity.json) preserve the completed 1,048-input comparison: zero decision, guard-certificate or full EC-result differences, 57 focused checks. This is parity on retrospective development evidence, not an additional unseen test. The [six](data/history-origin-six.json) and [ten](data/history-origin-completion.json) supporting history-origin snapshots remain separate; no core window is replaced. This SF18 replay did not validate native SF19. The separate fixed native assessment below provides limited headless execution evidence; variable-budget and browser validation remain limited.

## Technical archives

Earlier source/evidence releases remain available without becoming part of the current reader narrative: [the feasibility study](../brilliant-moves-pilot-2026-11-03/REPORT.md), [tactical references](../brilliant-moves-followup-2026-11-03/README.md), [development-reference release](../brilliant-moves-2026-11-03/REPORT.md), and [the earlier report at commit c6969d1](https://github.com/Dash1971/mute-chess-research/blob/c6969d1/studies/brilliant-moves/REPORT.md). Their original denominators and validation roles are retained.

## Prospective fixed-rule validation and release decision

The prospective study excludes all previously reviewed/regression games and known sampled positions before current-label collection. It freezes the native source, policy comparison, queue/reserve order and engine configuration. The finalized 200 primary moves span 109 new games, 100 current Brilliants and 100 explicit controls, 20 per class per account. All 217 raw captures are retained, including 17 secondary observations. Controls follow the original 20 nominated games per account regardless of whether a gallery nomination keeps its Brilliant label; positives advance through fixed reserves. The audited metadata correction preserves original captures and extra reserve controls as secondary.

The new SF18 evidence contains 573 core snapshots and 150 separate prior-origin snapshots, at 300,000 nodes/Threads1/Hash64 with full PGN history and actual completed current/prior iterations. No core window is replaced by a supplementary window. Required histories are complete; the [primary audit](data/prospective-history/PRIMARY-AUDIT.json) reports no history/recovery proof unknowns. V7 and the core v6 rule make identical primary decisions: 78TP/22FN/13FP/87TN. EC direct gives 27/73/1/99; shared-window EC gives 25/75/1/99 and remains a separate comparator. The source, data and protocol freezes and raw labels are published under [data/prospective-history](data/prospective-history/DATA-PROVENANCE.json).

The 10-game native assessment is separate: 884 moves processed through 902 requests using the headless Node-hosted actual SF19 smallnet Balanced whole-game path. Only 19 primary moves have reference labels in this assessment: both Mute rules give 7TP/2FN/2FP/8TN; EC direct gives 0/9/0/10. A prediction-selected audit of all 13 native Brilliant awards found 9 matching labels and 4 extras; it is not a population error-rate sample and is never pooled with the primary 200. These are limited execution-profile checks, not broad browser UI, device, timed-mode or native-domain validation. The [native audit](data/prospective-history/NATIVE10-AUDIT.json) preserves the original and later supplemental-label roles. The 57MB full native search output is omitted; its exact SHA accompanies the compact audit.

The separate guard-activation discovery scanned 500 new public-PGN games and found 12 board candidates, but **zero actual v7 veto activations**. No fresh panel labels were collected. Direct validation of the guard’s rejection behavior is therefore **inconclusive**, not a zero-error result. [Panel selection](data/prospective-history/PANEL-ACTIVATIONS-FREEZE.json), engine evidence and the [separate-assessment summary](data/prospective-history/separate-assessments-summary.json) preserve that shortfall.

The History Rule is retained as a comparison; the selected system is the more selective fixed model described above. More Brilliants are recognized than with EC, with 13 extras per 100 fresh controls remaining a significant limitation; the fresh results do not establish a benefit of the material guard. No classifier, threshold or source was tuned in response. Previous 1,048 development and earlier test artifacts remain byte-for-byte preserved; new 200, native audit, panel and secondary observations are not silently pooled. The combined 1,248-move descriptive result is separate from the prospective 200 estimate. Sampling remains balanced and enriched, moves share games, and five accounts limit generalization.

## Native selective replay receipt

The [new 200 native parity summary](data/selective-replay/native-parity-summary.json) and [full trace](data/selective-replay/native-parity-trace.json) show zero feature/missingness, score, award, integrated-symbol or EC-object differences on the exact saved SF18 inputs. Optional avoidability is unknown in one case in both windows; no physical timeout occurs. Exact frozen model bytes match. These are parity findings, not a native SF19 accuracy test. The prior History 10-game assessment is not promoted into evidence for the selected model.
