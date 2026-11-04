# Methods and reproducible evidence

This technical appendix supports [What makes a move brilliant?](REPORT.md). The published comparison contains **318 distinct game/move pairs: 159 observed Chess.com Brilliants and 159 explicitly classified non-Brilliants, from 153 games and four accounts**. The original target was 600 moves across five accounts; that target was not completed. Directory names and retained `quantity_limit: 600` fields describe the original ceiling, not the analyzed sample size.

## Sample, labels and identity

| Account | Brilliant moves | Non-Brilliant moves |
| --- | ---: | ---: |
| nelsi | 60 | 60 |
| hansen | 29 | 29 |
| GothamChess | 10 | 10 |
| Hikaru | 60 | 60 |
| KNVB | 0 | 0 |
| **Total** | **159** | **159** |

Positive candidates came from the profiles' Queen, Rook, Bishop and Knight Sacrifice galleries with the one-year view selected. The planned allocation was 15 positives per category per account. Both completed accounts, nelsi and Hikaru, achieved that allocation; the partial accounts did not. Gallery categories identify offered material and need not identify the piece that moved. Next-unused eligible reserves in the same category replaced historical entries whose observed Game Review label differed. Historical labels, changed labels and secondary observations remain distinct.

Comparison moves were separate moves by these players in the selected games. Selection deliberately favored apparent legal piece offers under the frozen Mute v2 predicate, quiet attacked/defended pieces, exchanges and captures. Each candidate required an explicit Game Review classification. A candidate found Brilliant was retained as secondary evidence and replaced in the negative sample. Missing gallery membership was never used as a negative label. This enrichment makes the sample a targeted challenge, rather than a random estimate of awards in ordinary games.

“Fresh review” means the label displayed when Game Review was opened or a move selected at the recorded capture time. It does not prove that Chess.com recalculated the position then, and it is not a claim about the label forever afterward. No deeper rerun was requested and Chess.com's review configuration was not exposed. Historical gallery labels and these observations are separate evidence layers.

Each primary move matches a numeric game ID, visible SAN and an exact one-based ply against legal full-PGN replay. A source query `move=N` is zero-based and must agree with ply `N+1`. Rendered board pieces corroborate the after-position when available; a mismatch blocks inclusion. Missing board imagery remains explicit, with SAN/game/ply identity still required. Full PGNs preserve history, castling and en-passant state, player ratings, dates, time controls and recorded clocks. Derived before/after FENs are convenient views, not replacements for that history.

Previously inspected games and regression positions were excluded from the new primary sample. The exclusions include the feasibility-pilot moves, the earlier nine-example investigation and owner regression examples; exact position checks normalize FENs with python-chess and compare their first four fields. Known explanatory examples outside the sample do not enter the confusion counts.

## Partitions and retrospective tuning

The game partitions were fixed before engine comparison. All games involving Hikaru form `player_holdout`; other game IDs enter `game_holdout` when the full SHA-256 of the numeric ID, interpreted as an integer, has remainder zero modulo five. Remaining games are `development`. A game is never split between partitions.

The analyzed sample has 153 development moves from 73 games, 45 game-holdout moves from 22 games, and 120 player-holdout moves from 58 games. The [analysis-plan freeze](analysis-plan-freeze.json) records the pre-analysis source hashes and settings for the existing EC and Mute v2 comparison.

**Mute v3 was chosen after inspecting this challenge set.** Its results, including results in the historically named holdout partitions, are retrospective rule tuning. Those partitions are not untouched validation for v3. The [proposal record](policy-proposal.json) states this explicitly. A genuinely new sample is needed to estimate how the proposed rule generalizes. The original v2 comparison remains a comparison of pre-existing rules under the frozen engine plan.

## Sources and exact decision rules

The baseline Mute source is [`b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12`](https://github.com/Dash1971/mute-chess/tree/b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12), policy `mute-chess-brilliant-v2`. Native `ui/analyse/src/noSweatClassify.ts` and its core are carried by `deploy/lila/patches/lila-nostr-maia.patch`, Git blob `addef7a02c1e6807e72910dcffca5cfaf7f4c5aa`. The [copied-source provenance](reference/current-v2/provenance.json) pins file hashes. An import-path shim permits standalone replay; rule bodies are unchanged.

En Croissant is pinned to [v0.15.0, `6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53`](https://github.com/franciscoBSalgueiro/en-croissant/tree/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53). The independent scoring oracle is the already adapted reference from [Mobile Maia preview `8563954429c2fb53ce0fe0e16c73c5d8a73ccfe0`](https://github.com/Dash1971/maia-chess-android-preview/tree/8563954429c2fb53ce0fe0e16c73c5d8a73ccfe0). This identifies an inspected reference, not the latest Mobile Maia release. Mobile Maia is not changed by this study. [Reference documentation and retained licenses](reference/README.md) describe the adaptations and runtime.

Both classifiers map mover-normalized centipawns through `W(cp) = 100 / (1 + exp(-0.00368208 * cp))`, with centipawns clamped to ±1000 and winning/losing mate scores mapped to those limits. This heuristic scale is not Chess.com's rating-dependent Expected Points Model, a calibrated outcome probability, a Maia move probability or native game accuracy.

**EC:** mapped loss above 20 points returns Blunder, above 10 Mistake, and above 5 Dubious. With at least two evaluated roots, Brilliant requires the played first-choice move, a best-versus-second mapped gap strictly greater than 10 points, and EC's sacrifice predicate. For a nonterminal position that predicate is `M(before) > -M(after) + 100`, using the copied capture-only material search after every legal root. Physical values are pawn90, knight300, bishop300, rook500 and queen1000. Its other annotation rules remain unchanged. The comparison publishes both the unchanged annotation oracle and the application's complete-window confirmation result; headline counts use confirmed awards.

**Mute v2:** retains the negative move-quality labels. A provisional Brilliant requires at least two evaluated roots, mapped loss at most5 points, an after score at least−100 centipawns for the mover, a legal offer of a non-pawn/non-king piece, and no other evaluated root at or above+600 centipawns that lacks such an offer. The played move need not be the first root or uniquely best.

For each offered piece, the legal-offer predicate searches captures and recaptures on that same square, allowing either side to stop exchanging. The opponent's best exchange gain must be strictly greater than `max(0, raw mover material after - raw mover material before) + 100`. Immediate capture and promotion gains are credited. Legality, pins and promotions use the copied Chessops source. Pawn-only and delayed offers do not qualify. Material recovered on another square is outside this local predicate.

**Proposed Mute v3:** adds this corroboration condition to v2's Brilliant eligibility:

```ts
ecSacrifice || (after.mate !== undefined && normalized(after, mover) > 0)
```

A legal offer must therefore also pass the existing broader EC material predicate, or the searched after-position must report a winning mate for the mover. A high centipawn score alone does not activate the mate exception. The exception avoids treating EC's mate sentinel as physical material. All other v2 soundness/relevance thresholds remain unchanged.

The safe-alternative veto deliberately still uses the **raw local legal-offer predicate** for alternative roots. It does not recursively ask whether an alternative would receive a v3 Brilliant badge or pass the new EC/mate condition. This distinction preserves the previous alternative semantics. The guard is evaluated again when corroborating a whole decision window. The candidate source is [`ac298a0d69ab51808857b089063348f2adac1101`](https://github.com/Dash1971/mute-chess/tree/ac298a0d69ab51808857b089063348f2adac1101), with exact hashes in [proposed-v3 provenance](reference/proposed-v3/provenance.json).

For both Mute versions, sacrifice-derived EC Brilliant/Interesting labels are cleared when the legal-offer test fails. Existing fallbacks otherwise retain their defined semantics. Provisional Brilliant and Good decisions require complete-window corroboration from actual earlier completed snapshots or compatible independent evidence at no shallower depth. Contradictory or incomplete confirmation withholds the standout. Raw eligibility and confirmed awards are retained separately; no prior snapshot is fabricated by copying the final score.

## Fixed engine evidence and baseline results

All policies receive identical saved Stockfish18 evidence: one thread,64MB hash and300,000 requested nodes per position. The binary SHA-256 is `ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374`. Searches retain full PGN history and cover the preceding, before and after positions, deduplicating overlapping windows. Terminal positions are recorded without a search charge.

Only complete same-depth MultiPV iterations with distinct legal roots are accepted. Two roots are requested when available. Actual preceding completed iterations provide the baseline corroboration. Hash is cleared at each game/budget session boundary; requested positions are searched forward within that session. Identity-checked cached snapshots were reused as collection grew. This fixed research budget differs from Mute's browser review settings and does not reproduce Chess.com's engine configuration.

| Confirmed policy | TP | FN | FP | TN | Brilliant detection | Extra awards among controls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EC reference | 44 | 115 | 2 | 157 | 44/159 (27.7%) | 2/159 (1.3%) |
| Mute v2 | 143 | 16 | 42 | 117 | 143/159 (89.9%) | 42/159 (26.4%) |
| Proposed v3, retrospective | 117 | 42 | 6 | 153 | 117/159 (73.6%) | 6/159 (3.8%) |

Here TP/FN refer to observed Brilliant moves; FP/TN refer to explicitly observed non-Brilliant comparison moves. A withheld decision is not an award. The [v2 comparison](comparison-rules.json) and [v3 comparison](comparison-v3.json) contain every row and account/partition breakdown. Category membership for interpretation comes from the verified `sampling_category` in [primary-moves.json](primary-moves.json), not a union of superseded gallery captures.

Relative to v2, v3 removes36 extra awards and also loses26 observed Brilliant detections:11 from nelsi,10 Hikaru,4 hansen and1 GothamChess. Seven observed positives are retained solely through the winning-mate exception when the EC predicate is false. These describe this sample and the chosen search budget; they are not independent validation or a measurement of enjoyment.

## Stronger-search sensitivity check

The predeclared stronger subset contains30 v2 disagreements:15 false awards and15 missed Brilliants, selected by ascending SHA-256 of `gameID + ":" + ply` within each class. The [subset](stronger-subset.json) and its [freeze record](stronger-subset-freeze.json) were saved before stronger search. The same engine/options searched these moves at1,500,000 requested nodes per position. This is a deliberately difficult subset, not another random sample.

Two different uses of the stronger evidence must be distinguished:

1. `stronger_window_decision` evaluates the stronger window itself, including its own earlier completed iterations.
2. `independent_stronger_confirmation` asks whether that stronger window corroborates the original baseline decision. It still requires the baseline window; a stronger award does not promote a baseline miss automatically, and contradictions can veto confirmation.

| Standalone stronger window,30 selected moves | TP | FN | FP | TN |
| --- | ---: | ---: | ---: | ---: |
| EC reference | 0 | 15 | 0 | 15 |
| Mute v2 | 2 | 13 | 14 | 1 |
| Proposed v3 | 2 | 13 | 3 | 12 |

For both Mute versions, three binary decisions change relative to their own baseline windows: `171711505152:69` and `185811812218:57` change from missed Brilliant to award; `187780685807:52` changes from extra award to no award. Using the stronger evidence only as independent confirmation produces **zero binary changes** to baseline awards. The `summaries.all_fresh` fields in the [v2 stronger artifact](comparison-stronger.json) and [v3 stronger artifact](comparison-v3-stronger.json) deliberately retain baseline totals; standalone stronger counts must be read from the subset's row-level `stronger_window_decision` fields. The stronger evidence does not validate v3 on unseen games.

The baseline contains912 saved position snapshots; summed per-snapshot elapsed time is650.728371seconds. The stronger run contains90 snapshots totaling96.159335seconds. These sums describe recorded search work, not total collection duration, total computer time, or token/API billing. Exact runtime can vary by machine.

## Completeness and dependence audit

The [cohort audit](cohort-audit.json) reports311 of318 primary moves with captured-board corroboration; seven rely on the required visible SAN/game/ply match. There are no unresolved identity mismatches, conflicting active fresh binary labels, missing primary PGNs or currently selected known-regression FEN matches. Repeated UI captures with contradictory Brilliant/non-Brilliant labels would exclude that move pending review; metadata enrichment revisions are separate from fresh captures.

There are319 selected fresh capture rows for318 primary moves. All319 have SAN, displayed evaluation, some coach text, ratings, date, time control and PGN clock metadata. Coach completeness is a different question:116 texts end in sentence punctuation,191 have an explicit capture-status field, and **zero are asserted verified complete by the audit**. Earlier captures may contain typewriter fragments, and some early extraction used DOM text content; extraction metadata is preserved. Neither nonempty text nor punctuation proves a complete visible explanation. Embedded raw text is retained without filling in missing words.

Six groups of repeated before-positions span13 primary moves; therefore these318 game/move pairs are not318 independent chess positions. Multiple moves also come from the same game and player. The [audit](cohort-audit.json) identifies those groups explicitly. Seven historical gallery/current-review disagreements are retained as secondary evidence, not counted as confirmed negative controls merely because the labels changed.

The optional [material features](material-features.json) describe a bounded capture-only probe across all squares, relative to raw physical pre-move material. It is capped at one second/100,000 combined calls per position; incomplete work is Unknown. Its stand-pat treatment and omitted quiet evasions can be incomplete in check. Checkmate is not a material bonus. Conditional lines are legal illustrations, not claims that an acceptance is forced or was played. These descriptive features are not the v3 implementation and are not substitutes for the full classifier replay.

## Public artifacts and reproduction

Games came from Chess.com's [documented Published Data API](https://www.chess.com/news/view/published-data-api), using selected-game monthly PGNs and relevant locally reused public archives. [Official PGN download guidance](https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game) describes the public export. The released artifacts contain no authenticated request metadata, cookies or whole monthly archives.

| Artifact | Scope |
| --- | --- |
| [primary-moves.json](primary-moves.json) |318 unique labeled game/move pairs and verified sampling categories; the numerical denominator |
| [selected-games.pgn](selected-games.pgn), [public-pgn-provenance.json](public-pgn-provenance.json) |287 complete games, including secondary observation games; hashes and public retrieval provenance; not153 primary games only |
| [observations-export.json](observations-export.json) |644 exported observation rows with embedded original fields and secondary evidence; not644 distinct primary moves |
| [corpus.sqlite3](corpus.sqlite3) |Publication-filtered database containing the153 primary games, their complete replayed positions and retained observations from those games; supports the collector without publishing the larger private cache |
| [analysis-baseline.json](analysis-baseline.json), [analysis-stronger.json](analysis-stronger.json) |Saved engine evidence and target/snapshot identities |
| [comparison-rules.json](comparison-rules.json), [comparison-v3.json](comparison-v3.json), [comparison-stronger.json](comparison-stronger.json), [comparison-v3-stronger.json](comparison-v3-stronger.json) |Policy replay and separate baseline/stronger interpretations |
| [analysis.py](analysis.py), [replay.mts](replay.mts), [replay-v3.mts](replay-v3.mts), [reference/](reference/README.md) |Collector, rule replay, exact source pins, runtime instructions and licenses |

The larger collection manifest's cached-game counts and original600 target are collection bookkeeping, not the released primary denominator. Metadata versions are audited separately from the644 exported active observation rows. The publication-filtered SQLite database reproduces exactly the318 primary game/ply keys used here.

The original `corpus.py` is retained as collection provenance. It enforces an immutable local source-path marker, so its collection CLI is not supported on the relocated publication database. The supported reproduction paths below use the ready SQLite input through `analysis.py`, or replay the saved JSON directly. The optional material-feature script has one publication-only path amendment to locate its included earlier verification fixture; [PUBLICATION.json](PUBLICATION.json) records the amendment and original digest.

Classification replay needs the saved engine JSON and pinned TypeScript sources, **not SQLite, a browser, Maia models or a running application**. From the study directory, with Node24, tsx4.23.15 and Chessops0.15.1 available to the copied reference folders:

```sh
node --import ./reference/current-v2/node_modules/tsx/dist/loader.mjs \
  ./replay.mts ./analysis-baseline.json ./analysis-stronger.json \
  ./comparison-rules-replayed.json

node --import ./reference/proposed-v3/node_modules/tsx/dist/loader.mjs \
  ./replay-v3.mts ./analysis-baseline.json ./analysis-stronger.json \
  ./comparison-v3-replayed.json
```

To collect new engine evidence, Python3 with python-chess and the recorded SF18 binary are also needed. The supplied SQLite database is the ready input for this path. Use a new output filename and set the installed binary path explicitly without editing the frozen collector:

```sh
python3 -c 'import analysis; analysis.ENGINE="/path/to/stockfish"; analysis.main()' \
  baseline --db ./corpus.sqlite3 --output ./analysis-baseline-reproduced.json

python3 -c 'import analysis; analysis.ENGINE="/path/to/stockfish"; analysis.main()' \
  stronger --db ./corpus.sqlite3 --subset ./stronger-subset.json \
  --output ./analysis-stronger-reproduced.json
```

[Reference runtime instructions](reference/README.md) explain dependency resolution and baseline-only replay. Changed engine/collector hashes prevent reuse of incompatible cached scores. Replay verifies pinned source hashes. Python and copied TypeScript material calculations agree on all compared rows.

These results estimate agreement conditional on deliberate sampling and fixed engine evidence. They do not establish population precision, Brilliant prevalence, awards per game, beginner behavior or a measured effect on fun. Chess.com's [published classification explanation](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) says player strength matters and does not disclose the complete classifier. This study proposes transparent Mute behavior rather than claiming to recover that unpublished formula.
