# A pawn-winning tactic that should not be Brilliant

**Targeted follow-up · November 3, 2026 · [Original pilot](../brilliant-moves-pilot-2026-11-03/REPORT.md)**

**Recommendation: collect a small set of contrasting tactical examples before changing the classifier.** We can reject the reported false positive with a stricter material filter, but the two simple filters examined here also reject four currently awarded Chess.com brilliants. That trade-off matters when the product goal is more satisfying awards.

This follow-up reviews [Mute Chess issue #229](https://github.com/Dash1971/mute-chess/issues/229). It adds one targeted current Chess.com observation and a retrospective screen of the saved pilot. The completed pilot's 40-move sample, counts and engine evidence are unchanged. No application rules, search budgets or deployments changed. There is no classification PR yet.

## The reported move is now a confirmed comparison negative

We opened [L1lChap–nelsi, 14...Ndxe5](https://www.chess.com/analysis/game/live/186311900336/review?move=27) in the logged-in Chrome session. The current Game Review display explicitly said **“Ndxe5 is excellent”**, with White evaluation **−3.13**. The coach text was: “With this move, the bishop comes under sudden pressure.” The Explain control displayed the following continuation:

```text
14...Ndxe5 15.Nxe5 Nxe5 16.fxe5 Rxd3
```

Black trades two knights for White's knight and bishop and wins a pawn. The material recovered on d3 is invisible to the current offer test, which follows exchanges on e5. The owner's expected rejection is therefore supported by an explicitly observed current Chess.com non-Brilliant label. See the separate [review record](ndxe5-review.json). Settings were not exposed; no deeper rerun was requested. An observed review display is not proof of an independent fresh engine calculation.

## A surprisingly close positive example

The completed pilot includes [GothamChess's 9...Nxd5](https://www.chess.com/analysis/game/live/186305472636?move=17), explicitly **Brilliant** in the current review display. One legal acceptance line is:

```text
9...Nxd5 10.Nxd5 Bxd5 11.cxd5 Bxg5
```

Black trades a knight and bishop for White's knight and bishop and wins a pawn. Material is recovered on g5 after exchanges on d5. Every move in this illustrative line was legally checked from the stored PGN position; it is not asserted to be the continuation played in the game.

| Example | Exchange square | Later recovery | Net material gain | Current Chess.com display |
| --- | --- | --- | --- | --- |
| nelsi, 14...Ndxe5 | e5 | ...Rxd3 | One pawn | **Excellent** |
| GothamChess, 9...Nxd5 | d5 | ...Bxg5 | One pawn | **Brilliant** |

The accounting is similar. These two examples alone do not tell us which other features produce the different labels. They do show why “material recovered elsewhere means never Brilliant” is too broad if we want to preserve these observed Chess.com awards. A deliberately stricter Mute policy is possible, but should be presented as a product choice with known losses.

## Two simple fixes, both with the same cost

We screened two possible necessary conditions using the saved pilot positions:

1. **Require the existing legal offer and EC's net-material sacrifice predicate.** This rejects Ndxe5 and Hansen's gallery/current-review disagreement, Qxe4.
2. **Force acceptance and follow captures across all squares.** Start from a specific legal capture of a non-pawn offer that passes the existing exchange/credit test. After forcing that capture, run capture-only material minimax across all squares. Compare against the mover's **raw material before the move**, avoiding EC's foregone-gain problem. Require at least one qualifying acceptance to leave a material deficit exceeding 100 units. Mate receives its physical material value, not an artificial material bonus.

Both gates reject the known false positives and preserve the previously inspected Ju Wenjun Bb2 example. Both also reject the same four current Chess.com brilliants that Mute v2 currently awards:

| Account | Move | Game / ply |
| --- | --- | --- |
| hansen | 31.Nd7 | 183990510823 / 61 |
| KNVB | 24.Nf3 | 186059216760 / 47 |
| GothamChess | 9...Nxd5 | 186305472636 / 18 |
| nelsi | 8.Bh6 | 186405804254 / 15 |

That is **four of the 17 current true awards** from the pilot. This is a necessary-gate screen, not a full modified-policy evaluation: alternative-root relevance and whole-window behavior were not recomputed with replacement predicates. We therefore do not publish a new classifier accuracy figure or claim these are the only possible changes.

The [probe](probe.py) uses saved FENs only, no network or engine. It completed in about 0.013 seconds on this run: 393 capture-search calls and 206 same-square exchange calls. [Results](probe-results.json) include exact inputs' hashes, every screened move and the legal Gotham continuation. Install `python-chess` and run `python3 probe.py` from this directory to reproduce the screen; the sibling published pilot provides the saved inputs. The [known positive input](known-positive.json) records its earlier source. Probe controls retain their original provenance; the newer Ndxe5 review is deliberately a separate observation.

The capture-only probe is an exploratory heuristic. It allows either side to stop exchanging, even when check would require a response, and omits quiet defensive moves. It is not complete chess search, proof of forced recovery or production-ready rejection logic. Any future implementation must handle check evasions, mating compensation, promotions, en passant and incomplete searches honestly, and fit the existing worker responsiveness constraints. The inspected pilot is now development evidence for these hypotheses, not an untouched test set.

## The smallest useful next study

Recommend a **two-hour preparation-inclusive cap**, aiming for **30 explicitly Brilliant and 30 explicitly non-Brilliant new moves**, with evidence quality and the deadline taking priority over count. Focus on matched examples of temporary offers, cross-square recoupment, pawn-winning combinations, defended pieces, quiet tactical replies and genuine material investments. Avoid filling the controls with obvious opening mistakes or terminal mates. Capture current labels, coach explanations, full PGNs, ratings and time controls; keep historical gallery labels separate.

Keep the owner cases and inspected pilot as development regressions. Reserve complete new games before tuning, freeze a candidate rule before looking at its test outcomes, and compare at more than one fixed engine budget. Alongside Chess.com labels, make the intended Mute judgment explicit: reference-label agreement and the owner's preference are related but separate objectives.

This targeted collection is more useful for the reported failure than immediately scaling to all 3,519 gallery entries. It is a recommended next budget, **not a started or authorized additional study**. A later PR should explain the general distinction it implements, reject Ndxe5 without hard-coding its position, report any accepted loss of genuine awards, and preserve Mobile Maia, native metrics, imported annotations and confirmation safeguards.
