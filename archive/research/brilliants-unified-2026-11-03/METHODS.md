# Methods and reproducible evidence

This appendix defines the benchmark, its validation boundaries and the exact classifiers. The core contains **618 distinct game/move pairs from 299 games: 309 observed Chess.com Brilliants and 309 explicitly classified non-Brilliants**. [SUMMARY.json](SUMMARY.json) is the authority for final counts and metrics. Combined results describe agreement on this selected benchmark. Prospective and reserved-game results are reported separately.

## Selection, labels and identity

Candidates come from nelsi, hansen, KNVB, GothamChess and Hikaru. Positive sampling uses their one-year Queen, Rook, Bishop and Knight Sacrifice galleries, rotating categories where available. A category describes offered material, not necessarily the moving piece. Current labels must be read explicitly in Game Review; a historical gallery label alone is insufficient. Systematic unused reserves replace changed labels, with the rejected observation retained as secondary evidence.

Controls are same-player moves in the selected games. Selection favors raw-v2 legal piece offers, then quiet attacked/defended pieces, recaptures/exchanges, other captures and other quiet moves, with proximity to the target and ply breaking ties. This deliberately enriches difficult cases. Book, Good, Excellent, Miss, Inaccuracy, Mistake and Blunder are legitimate explicitly observed non-Brilliant labels. Unknown labels and absent gallery membership never become negatives. A control displaying Brilliant is secondary and systematically replaced. Full-sample counts remain fixed; apparent-offer and non-Book subgroups are additional analyses, not exclusions chosen afterward to improve results.

“Observed review” means the classification displayed at the recorded capture time. It does not prove an independent Chess.com recalculation then, nor establish a permanent label. Review configuration was not exposed; no stronger Chess.com rerun was requested. Chess.com's [published classification explanation](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) describes rating-sensitive criteria without disclosing the complete formula.

Identity requires the correct live/daily game type, numeric game ID, source URL, one-based ply and visible SAN matching legal full-PGN replay. A URL query `move=N` must match ply `N+1`. Captured board pieces corroborate the after-position; contradictions block inclusion. `611/618` have this additional corroboration. Seven development observations lack it but retain explicit SAN/game/ply identity. Full PGNs preserve history, castling/en-passant rights, dates, ratings, time controls and available clocks; FENs are derived views. Recorded player/opponent ratings span 397–3500; time controls range from ultrabullet to daily chess. One primary game is daily (`994221268`), and its two observations use the verified daily namespace. Most moves come from short time controls. Ratings are preserved, not pooled into a single assumed player strength.

Coach explanations are optional evidence, **not algorithm inputs**. Raw extraction and completeness flags remain available: `218` verified visible-complete, `396` partial/unverified, and `4` absent, among the 618 unique primary moves. Secondary captures are not counted in these totals. Typewriter fragments and older DOM-text-content captures are not silently completed. Punctuation alone does not establish completeness. Conflicting active fresh binary labels exclude the move pending review; metadata revisions are separate from new captures. The JSON export contains 963 active observation rows; the SQLite database retains 992 rows including 29 superseded metadata records. Its `active_observations` view keeps the latest stored row for each game/ply/source type/capture time/source link/account group. These counts do not change the 618 primary labeled moves.

The supplemental pawn-winning examples are outside all benchmark metrics. The [Excellent observation](../brilliant-moves-followup-2026-11-03/ndxe5-review.json) and [Brilliant reference](../brilliant-moves-followup-2026-11-03/known-positive.json) retain their source evidence; [illustrative-cases.json](illustrative-cases.json) records the legal variations. Qf5+ and Bf5 regression expectations are owner judgments without confirmed Chess.com labels, and are never counted as negative controls.

## Development, prospective checks and reserved validation

The dataset distinguishes 318 development-reference moves from 300 prospective moves. The frozen Mute v3 source was chosen using development evidence and was unchanged using prospective labels. Thus development and combined metrics are retrospective descriptions for this candidate; all 300 prospective moves also check an already frozen policy.

Prospective games exclude 179 previously reviewed/development game IDs and 724 normalized prior before/after positions. Normalization uses python-chess FEN output and compares its first four fields; move counters do not distinguish positions. Prospective positive selection also avoids repeated before-position-plus-move identities across games. The 299 primary games and 618 game/ply keys are deduplicated; raw gallery rows, secondary captures and cached games are not extra benchmark cases.

Prospective partitions are fixed by whole game: interpret SHA-256 of `"mute-extra300:" + gameID` as an integer; remainder zero modulo 3 is reserved validation, otherwise discovery. All moves from a game stay together. The rule author is restricted to development/discovery evidence until candidate source freeze. Original development partition names do not make those observations untouched tests for a rule selected using them.

The [final candidate freeze](FINAL-CANDIDATE-FREEZE.json) additionally fixes **label-independent validation hygiene before prospective policy scoring**: remove a reserved game from the strict validation subset if any sampled before/after position, normalized to four FEN fields, also occurs in development evidence, including the 318 reference moves and prospective discovery moves. Exclusion is by entire game, without examining whether a policy succeeds. It does not delete labels from the 618-case combined benchmark.

The final audit records `48` reserved games, `0` overlap-excluded games, and `101` retained validation moves (`51` Brilliant/`50` non-Brilliant). Repeated-position groups and remaining cross-partition overlap are `six repeated-before-position groups, all confined to development; no sampled before/after position shared across development and retained validation`. Moves share games, positions and players; they are not 618 independent trials.

## Source pins and the fair EC comparator

Mute v3 is frozen at [`ac298a0d69ab51808857b089063348f2adac1101`](https://github.com/Dash1971/mute-chess/tree/ac298a0d69ab51808857b089063348f2adac1101). V2 is [`b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12`](https://github.com/Dash1971/mute-chess/tree/b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12). Copied classifier/core bodies retain exact source hashes, import-shim provenance and licenses in [reference/](reference/). No application checkout or Maia inference is needed for rule replay.

The EC peer is **direct raw annotation** from latest stable [v0.15.1](https://github.com/franciscoBSalgueiro/en-croissant/releases/tag/v0.15.1), commit `4932c9231517f6fd75e5a97902b207c7dc82e61f`. Its scoring file`src/utils/score.ts` and material file`src-tauri/src/chess.rs` are byte-identical to the pinned `6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53` reference. [The proof](ec-latest-stable-check.json) records Git blobs`85ed17d99740dec954aed301f408ef8ff68968d0` and `0eccc73e0d69a14a25fa06bd914ceebf5367e413`. This establishes classifier-code equivalence, not identical application search behavior.

The independent EC scoring oracle comes from the documented [Mobile Maia preview reference](https://github.com/Dash1971/maia-chess-android-preview/tree/8563954429c2fb53ce0fe0e16c73c5d8a73ccfe0), with its existing adaptations recorded. Mobile Maia remains unchanged. EC with Mute/Mobile Maia-style shared-window confirmation is a separate appendix result; it is not silently substituted for direct EC in the headline comparison. V2 is the unguarded Mute comparator; the reader report presents its recognition/false-award tradeoff explicitly.

## Exact rules

Scores are normalized to the mover. Centipawns are clamped to±1000; signed mate scores map to those bounds. The common heuristic is `W(cp)=100/(1+exp(-0.00368208*cp))`. It is not a calibrated outcome probability, Maia move likelihood, native game accuracy or Chess.com's Expected Points Model.

EC returns Blunder for mapped loss above 20 points, Mistake above 10 and Dubious above 5. Brilliant requires at least two evaluated roots, the played first-choice move, a best-versus-second mapped gap strictly greater than 10 points, and the EC sacrifice predicate. Other EC annotation rules remain unchanged.

That predicate is nonterminal after-position plus `M(before) > -M(after) +100`. Its material evaluator considers every legal root, then capture-only continuation search. Values are pawn90, knight300, bishop300, rook500 and queen1000. This broader probe can notice recovery on other squares, but remains a heuristic: stand-pat can be used in check, quiet evasions and other quiet continuations are omitted, and checkmate uses a nonphysical sentinel. Foregone gains can also distort its notion of a sacrifice. It is neither a proof of uncompensated material loss nor complete tactical search. Python/copied-TypeScript parity differences are `0`.

Mute v3 preserves negative move-quality labels and requires seven conditions for a confirmed Brilliant:

1. At least two evaluated roots in the before-position.
2. Mapped loss at most5 points.
3. After-position score at least−100 centipawns for the mover.
4. A concrete legal offer of a non-pawn/non-king piece.
5. EC material corroboration **or an explicit searched winning mate** for the mover.
6. No other evaluated root at≥+600 centipawns that lacks the raw legal offer.
7. Compatible whole-window corroboration of the provisional standout.

The played move need not be uniquely best or the first evaluated root. For condition4, legal same-square captures/recaptures allow either side to stop. The opponent's best exchange gain must exceed `max(0, raw mover material after - raw mover material before)+100`, crediting immediate captures/promotions. Pins and legality matter. Pawn-only and delayed offers do not qualify; this local test misses recoup on other squares.

Condition5 is exactly `ecSacrifice || (after.mate !== undefined && normalized(after,mover)>0)`. A centipawn score of+1000 does **not** activate the exception; neither does`mate:0`, a missing mate score or a losing mate. This avoids interpreting the EC mate sentinel as physical material. Condition6 deliberately uses the **unchanged raw legal-offer predicate** for alternatives, not whether those alternatives would pass the new guard or receive a final v3 badge.

For condition7, actual earlier complete iteration windows must agree, or compatible independent evidence must be no shallower. Quality/terminal consistency and the complete decision window are checked; copying a final score does not create confirmation. The EC/mate guard is checked again in the corroborating window. Contradictory or incomplete evidence withholds the standout. Raw eligibility and final awards remain distinct. Sacrifice-derived EC Brilliant/Interesting labels are cleared when the legal offer fails. A rejected EC Brilliant can fall back to Interesting only with EC sacrifice true and mover after-score strictly above−200; other original labels retain their defined semantics.

V3 uses existing evaluation windows and material probes; it adds no production Stockfish requests. Stronger research searches do not alter the application budget.

## Engine evidence and stronger sensitivity checks

Every policy receives the same saved SF18 evidence: one thread,64MB hash,300,000 requested nodes per position, full PGN history, and preceding/before/after windows. The Stockfish binary SHA-256 is `ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374`. Overlapping windows reuse identity-checked snapshots. Terminal positions need no engine search.

Only complete same-depth MultiPV iterations with distinct legal roots are accepted; two roots are requested where available. Actual preceding completed iterations supply corroboration. Hash/session boundaries and cached continuation history are retained in source provenance. These budgets do not reproduce Chess.com's engine settings or Mute's browser review configuration.

Stronger evidence uses 1,500,000 nodes per position on at most30 preselected v2 disagreements per input cohort: up to 15 false awards and15 misses, ordered by SHA-256 of `gameID+":"+ply `, with unused capacity filled deterministically. Subsets are frozen before stronger searches. The combined recheck count is at most60, comprising two targeted disagreement subsets rather than unseen validation cases.

Standalone stronger-window decisions and stronger evidence used merely to confirm baseline decisions are different outputs. Neither silently replaces baseline scores or combined totals. Read row-level `stronger_window_decision` and `independent_stronger_confirmation` separately; summary baseline fields may intentionally retain original outcomes.

The targeted set contains **60 moves (30 Brilliant/30 non-Brilliant)** and 178 saved position windows. Every stronger target has complete same-depth windows; Python/TypeScript material differences are zero. These deliberately selected v2 failures are much harder than the full benchmark and are not another accuracy estimate for ordinary games.

| Policy | Baseline TP / FN / FP / TN on these 60 | Standalone stronger TP / FN / FP / TN | Binary award changes |
| --- | --- | --- | ---: |
| EC direct | 0 / 30 / 1 / 29 | 1 / 29 / 1 / 29 | 1 |
| Mute v2 | 0 / 30 / 30 / 0 | 4 / 26 / 28 / 2 | 6 |
| Mute v3 | 0 / 30 / 8 / 22 | 4 / 26 / 7 / 23 | 5 |

Using the stronger window **only to corroborate baseline decisions** changes two v2 awards: it vetoes `183799110991:66 Rxc3` and releases the previously withheld provisional award for `184634890030:37 Qxh7+`. V3 changes only the latter; EC shared-window confirmation changes none. Those outputs are not the standalone stronger classifier above. See [sensitivity-summary.json](sensitivity-summary.json) for every changed case and input hashes.

Saved per-snapshot search time sums to **871.510 seconds** over 1,775 baseline snapshots and **183.179 seconds** over 178 stronger snapshots, about **17.58 minutes of recorded search work** combined. These are engine-search durations, not elapsed study time, browser time or monetary cost. No token/billing ledger was captured, so no dollar estimate is asserted.


## Metrics, subgroups and reproducibility

TP/FN refer to observed Brilliants; FP/TN to observed non-Brilliants. Withheld is no award. Detection is `TP/(TP+FN)`; extra awards among controls are `FP/(FP+TN)`; agreement is `(TP+TN)/N`. Balanced agreement averages detection and specificity; it equals agreement on the 309/309 core but need not on a validation subset.

### Combined challenge set: 618 moves, 309 per class

| Classifier | TP | FN | FP | TN | Agreement | Detection | Extra awards |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| En Croissant: direct | 84 | 225 | 6 | 303 | 62.6% | 27.2% | 1.9% |
| EC + shared-window confirmation | 81 | 228 | 6 | 303 | 62.1% | 26.2% | 1.9% |
| Mute v2: legal offers | 273 | 36 | 77 | 232 | 81.7% | 88.3% | 24.9% |
| Mute v3: material guard | 220 | 89 | 16 | 293 | 83.0% | 71.2% | 5.2% |

The v3 guard removes 61 v2 extra awards while losing 53 v2 true awards. Its selected-sample positive predictive value is 220/236 = 93.2%, versus 84/90 = 93.3% for direct EC and 273/350 = 78.0% for v2. **93.2% is not overall agreement**; it depends on this artificially balanced case mix. The overall agreement is 513/618 = 83.0%.

### Prospective fixed-policy checks: 300 moves, 150 per class

| Classifier | TP | FN | FP | TN | Agreement | Detection | Extra awards |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| En Croissant: direct | 39 | 111 | 4 | 146 | 61.7% | 26.0% | 2.7% |
| EC + shared-window confirmation | 37 | 113 | 4 | 146 | 61.0% | 24.7% | 2.7% |
| Mute v2: legal offers | 130 | 20 | 35 | 115 | 81.7% | 86.7% | 23.3% |
| Mute v3: material guard | 103 | 47 | 10 | 140 | 81.0% | 68.7% | 6.7% |

All 300 were labeled after candidate freeze, with no candidate tuning. They include the reserved validation subset below, so these results are not independent replications of each other. V3 agreement is slightly lower than v2 here (81.0% versus 81.7%), while reducing extra awards from 35 to 10.

### Reserved validation: 101 moves, 48 games, 51 Brilliant / 50 non-Brilliant

| Classifier | TP | FN | FP | TN | Agreement | Detection | Extra awards |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| En Croissant: direct | 15 | 36 | 0 | 50 | 64.4% | 29.4% | 0.0% |
| EC + shared-window confirmation | 14 | 37 | 0 | 50 | 63.4% | 27.5% | 0.0% |
| Mute v2: legal offers | 44 | 7 | 11 | 39 | 82.2% | 86.3% | 22.0% |
| Mute v3: material guard | 31 | 20 | 4 | 46 | 76.2% | 60.8% | 8.0% |

V3 trades 13 recognized Brilliants for seven fewer extra awards relative to v2. Its lower overall agreement on this subset is reported alongside the improvement in false awards; the candidate is a precision-oriented recommendation, not an unqualified maximizer of agreement. The reserved sample is modest and shares the same five accounts as development. It is a game holdout, not an untouched player holdout.

### Challenge subgroups

Of the 309 negative controls, **163 have a raw legal piece offer**. Extra awards in this harder subgroup are EC 6/163 (3.7%), v2 77/163 (47.2%), and v3 16/163 (9.8%). The remaining 146 controls receive no Brilliant under any of these policies.

Excluding the four Book controls leaves 614 moves: 309 Brilliant and 305 non-Brilliant. TP/FN are unchanged; TN becomes 299 for EC, 228 for v2 and 289 for v3. FP stays 6, 77 and 16 respectively. Book moves do not explain the difference.

| Account | Moves | Brilliant / non-Brilliant | EC direct TP / FP | Mute v3 TP / FP | EC / v3 agreement |
| --- | ---: | ---: | ---: | ---: | ---: |
| GothamChess | 80 | 40 / 40 | 9 / 1 | 28 / 5 | 60.0% / 78.8% |
| Hikaru | 180 | 90 / 90 | 28 / 2 | 65 / 5 | 64.4% / 83.3% |
| KNVB | 60 | 30 / 30 | 7 / 0 | 20 / 2 | 61.7% / 80.0% |
| hansen | 118 | 59 / 59 | 22 / 1 | 42 / 3 | 67.8% / 83.1% |
| nelsi | 180 | 90 / 90 | 18 / 2 | 65 / 1 | 58.9% / 85.6% |

The complete per-account results, including v2 and EC confirmation, are in [SUMMARY.json](SUMMARY.json). Category membership can overlap; gallery categories are selection metadata rather than independent test groups.


Because sampling is balanced and enriched, these are conditional agreement measures, not natural Brilliant prevalence, ordinary-game false-award frequency, calibrated population precision or measured enjoyment. Five established accounts with varying game ratings and time controls do not establish beginner behavior or superiority to untested open-source implementations.

The public inputs are [primary-moves.json](primary-moves.json) with 618 labeled keys, [selected-games.pgn](selected-games.pgn)/[provenance](public-pgn-provenance.json) with 299 complete primary games, publication-filtered[corpus.sqlite3](corpus.sqlite3) with their full positions/observations, and one merged[analysis-baseline.json](analysis-baseline.json). [SUMMARY.json](SUMMARY.json), [comparison-v2.json](comparison-v2.json), [comparison-v3.json](comparison-v3.json) and `[moves.csv](moves.csv)` expose individual outcomes and denominators. Raw capture evidence, completeness, exclusions, source freezes and validation hygiene accompany the release. Monthly archives, cookies and raw HTTP metadata do not.

Saved-input rule replay requires Node24, tsx and Chessops0.15.1 resolvable beside the pinned references. It needs neither a browser, SQLite nor an engine. From the study directory, an empty optional stronger argument replays baseline evidence into a new output:

```sh
node --import ./reference/current-v2/node_modules/tsx/dist/loader.mjs \
  ./replay.mts ./analysis-baseline.json "" ./comparison-v2-replayed.json
node --import ./reference/proposed-v3/node_modules/tsx/dist/loader.mjs \
  ./replay-v3.mts ./analysis-baseline.json "" ./comparison-v3-replayed.json
```

Python3/python-chess, the public SQLite and recorded SF18 binary additionally support new engine runs through the supplied collector. Preserve original outputs and write new files. Replay of identical saved inputs and pinned rule bodies is exact; new engine runs can differ because of session/hash history, cached resumptions and engine execution. Such differences must be reported rather than forcing a desired label. Source hashes and retained GPL/AGPL notices remain authoritative. The helper scripts are bounded study tools, not application infrastructure.
