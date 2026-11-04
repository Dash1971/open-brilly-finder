# Open Brilly Finder

Open research, code, models and labeled chess data for **Chess.com-style Brilliant move classification**. This project grew out of [Mute Chess](https://github.com/Dash1971/mute-chess). The aim is to find more good piece sacrifices while keeping undeserved Brilliant awards rare, without changing classification according to player rating.

**Current recommendation: retain the production Mute Selective model.** Its published independent tests found **112 of 200 Chess.com Brilliants (56%)**, with **3 wrong awards** among 200 ordinary controls. The newer half of that test found **57 of 100 (57%)**. The deployed model has not been replaced by the experiments in this repository.

More training data, different learners, tactical features and two external classifiers did not establish a better production replacement. Some experiments produced modest development gains; others found many more Brilliants at an unacceptable cost in wrong awards. All of those results—including failures, contradictions and missing evidence—are retained. Work is paused as of **November 4, 2026**; this is a starting point for future researchers, not a claim that the problem is solved or that 56% is an upper limit.

## Comparison: the production model and En Croissant

**Independent test set: 400 selected moves from 215 games**, containing 200 Chess.com Brilliants and 200 explicitly ordinary moves. These games were not used to fit the production model.

| Implementation | Brilliants found | Recall | Wrong awards | Wrong share of all awards |
|---|---:|---:|---:|---:|
| **Production Mute Selective** | **112 / 200** | **56.0%** | **3** | **2.61%** |
| En Croissant reference | 53 / 200 | 26.5% | 3 | 5.36% |

On the newer 200-move subset, Mute Selective found **57/100 with 2 wrong awards**; En Croissant found **27/100 with 1 wrong award**. The separate experimental **History Rule** found **78/100 but made 13 wrong awards** on that same subset.

[Published report](studies/brilliant-moves/REPORT.md) · [Exact model and algorithm](studies/brilliant-moves/README.md) · [Methods and sampling limits](studies/brilliant-moves/METHODS.md)

**Another independent reserved-game comparison**, collected during the expanded-data work, contained 71 Brilliants, 494 hard ordinary moves and 89 additional clear errors from 89 reserved games:

| Implementation | Brilliants found | Recall | Wrong awards on 494 ordinary controls | Wrong share of awards |
|---|---:|---:|---:|---:|
| **Production Mute Selective** | **42 / 71** | **59.2%** | 2 | 4.55% |
| Expanded-data experimental forest | 37 / 71 | 52.1% | **0** | 0% observed |
| En Croissant reference | 18 / 71 | 25.4% | 3 | 14.29% |

All three rejected the 89 additional clear errors. Zero observed errors is not a guarantee of zero population error. This separate test supports retaining the production model: the expanded-data forest traded five correct awards for two fewer errors. [Study and frozen results](studies/brilliant-training-2026-11-03/README.md)

### What the percentages mean

- **Recall:** correctly awarded Brilliants / all Chess.com Brilliants in the test.
- **Wrong share of awards:** wrong awards / all awards. This is the project's target error measure: eventually fewer than 1% of awarded Brilliants should be wrong.
- **Ordinary-move false-positive rate:** wrong awards / ordinary controls. This is a different denominator. For example, the first table's 3/200 = 1.5% ordinary-move false-positive rate, while 3/115 = 2.61% of Mute's awards were wrong.

These are deliberately selected research samples. Their class mix affects the wrong-award share; none is a site-wide precision estimate. Do not pool the different tests or interpret a later development percentage as deterioration of the unchanged production model.

## Comparison: WintrChess, Knight's Eye and our experimental code

**Development dataset: 3,724 moves—917 Brilliants and 2,807 ordinary moves—in 972 game/position groups.** Learned methods use the same five grouped outer folds, keeping aliases, repeated positions and both engine windows together. Cutoff/model selection uses inner training folds. External policies are fixed, learn nothing from these labels, and are scored in the same groups. The primary award requires both saved engine windows to agree; single-window results are retained in the detailed reports.

**The forest rows below are development procedures fitted within folds, not the frozen production model scored on new games. The 49.3% number does not replace the production model's published 56–57% result.** The external classifiers were not tested on the independent sets above in this comparison.

| Implementation / experiment | Correct awards / 917 | Recall | Wrong awards | Wrong share of confirmed awards |
|---|---:|---:|---:|---:|
| Mute forest procedure, fixed `5/6` cutoff | 436 | 47.5% | 6 | 1.36% |
| Mute forest procedure, inner-selected cutoff (comparison baseline) | 452 | 49.3% | 6 | 1.31% |
| Standard random forest, existing features | 473 | 51.6% | 7 | 1.46% |
| Histogram gradient boosting | 329 | 35.9% | 4 | 1.20% |
| **WintrChess, frozen upstream rules** | **287** | **31.3%** | **20** | **6.51%** |
| **Knight's Eye, frozen upstream rules** | **590** | **64.3%** | **142** | **19.40%** |
| Mute forest + conditional reply gap | 424 | 46.2% | 7 | 1.62% |
| Standard random forest + conditional reply gap | 477 | 52.0% | 7 | 1.45% |
| Inner-selected learner procedure with reply-gap candidates | 465 | 50.7% | 5 | 1.06% |
| Mute forest + material recovery trajectories | 408 | 44.5% | 6 | 1.45% |
| Mute forest + independently recorded acceptance mate | 449 | 49.0% | 6 | 1.32% |
| Mute forest + accepting-piece fork and reply check | 413 | 45.0% | 6 | 1.43% |

WintrChess left **5 ordinary cases unresolved**. Knight's Eye left **56 cases unresolved: 34 Brilliants and 22 ordinary moves**. They are not counted as confirmed negatives. Knight's Eye's confirmed recall is therefore a lower bound; even if all its unresolved positives were awarded, recall would be 68.0%, while its 142 confirmed wrong awards remain. Recorded single-window results reach the same practical conclusion.

There are small numerical development gains—particularly the reply-gap learner-selection procedure—but repeated reuse of these examples, uncertainty in the rare-error counts and the absence of fresh prospective confirmation prevent treating them as a validated production upgrade. The aim is not simply to maximize recall or choose the best-looking table cell after the fact.

### Would adding external awards help?

Relative to the 452-correct/6-wrong development baseline:

| Frozen external classifier | Missed Brilliants it recovers | Additional wrong awards | Result if all its awards were added to the baseline |
|---|---:|---:|---|
| WintrChess | 88 | 19 | 540 correct / 25 wrong |
| Knight's Eye | 256 | 141 | 708 correct / 147 wrong |

Neither union was deployed. Knight's Eye supplies different detections, but its extra awards are far too error-prone for our goal. WintrChess also fails the required balance. This compares the pinned **WintrChess library**, whose README says it is not the live website's classifier, and the pinned **Knight's Eye policy**, not every possible version or configuration of those projects.

[External comparison report](studies/brilliant-external-comparison-2026-11-04/REPORT.txt) · [Per-case additions and errors](studies/brilliant-external-comparison-2026-11-04/PAIRED-CASES.json) · [All metrics, folds and uncertainty](studies/brilliant-external-comparison-2026-11-04/RESULTS.json) · [Independent verification](studies/brilliant-external-comparison-2026-11-04/VERIFICATION.json)

Additional experiments include evaluation consistency, mating-offer rules, alternatives to sacrificing, material recovery without mate, review-engine settings, and sacrifice/compensation relationships. A frozen mating-offer rule was tested on 24 fresh targeted cases: its 12 extra awards contained only **4 correct and 8 wrong**. These negative results and the contradictory chess examples are preserved in the [research index](docs/RESEARCH-INDEX.md).

## Run the offline quickstart

Python 3.10+ and its standard library are sufficient:

```sh
git clone https://github.com/Dash1971/open-brilly-finder.git
cd open-brilly-finder
python3 tools/reproduce_results.py
python3 tools/reproduce_results.py --verify-forest
python3 tools/infer_saved_features.py --case-key 183200302081:135
```

The first command recomputes the external comparison from saved decisions. The second **actually runs the five archived held-out forests on all 3,724 saved feature cases**, checking every score against the recorded predictions. The third runs the original 848-case fitted forest on one saved feature example. It is inference, not a new accuracy test. [Commands, model roles and dependencies](tools/README.md) · [Recorded reproduction check](docs/REPRODUCTION-CHECK.json)

This is a research codebase, not a finished FEN-only library. Classification uses engine evidence, legal-board analysis and move history. The [portable original feature extractor](studies/brilliant-moves/reference/v5/README.md) and [native TypeScript implementation](studies/brilliant-moves/reference/v5/native/noSweatBrilliantForest.ts) are included. New engine collection requires compatible Stockfish and the documented budgets. Historical experimental scripts retain original machine paths; their presence is not a claim that every archival script runs unchanged after cloning.

## Repository map

- [`studies/brilliant-moves/`](studies/brilliant-moves/): production-model family, readable/native code, frozen model, historical independent tests and original En Croissant comparisons.
- [`studies/brilliant-training-2026-11-03/`](studies/brilliant-training-2026-11-03/): expanded corpus, PGNs, 3,724-case feature dataset, saved engine evidence, training experiments and reserved-game evaluation.
- [`studies/`](studies/): all subsequent bounded studies, their code, inputs, protocols, predictions and failed candidates, including the Ne5 queen-offer investigation.
- [`archive/research/`](archive/research/): earlier working research, including additional experiments, source snapshots and data. It preserves historical paths and superseded interpretations; use the index and current summary to distinguish final conclusions.
- [`tools/`](tools/): small portable offline reproduction and inference entry points.
- [`SOURCE-MANIFEST.json`](SOURCE-MANIFEST.json): original relative paths, byte hashes, file sizes and explicit exclusions. Scientific results are copied without rewriting their original freeze hashes.

[Data provenance and limits](docs/DATA.md) · [Research index](docs/RESEARCH-INDEX.md) · [Attribution](THIRD_PARTY.md)

## Related work and attribution

We studied and credit [En Croissant](https://github.com/franciscoBSalgueiro/en-croissant), [WintrChess](https://github.com/WintrCat/wintrchess-lib), [Knight's Eye](https://github.com/knights-eye-chess/move-classifier), [Chess-Review](https://github.com/T-Julsgaard/Chess-Review), [Brilliant-Chess](https://github.com/wdeloo/Brilliant-Chess), and [Felix's chess-game-review](https://github.com/FelixYUFENGSU/chess-game-review). Their policies and test suites provided useful comparisons, not proof that Chess.com's private algorithm has been reverse engineered. The [source review](studies/brilliant-external-repos-2026-11-04/REPORT.txt) records specific mechanisms, limitations and pinned versions.

The original work comes from [Mute Chess](https://github.com/Dash1971/mute-chess) and [Mute Chess Research](https://github.com/Dash1971/mute-chess-research). Code and research retain **AGPL-3.0-only** terms where applicable; third-party code, images and game/evidence material retain their own provenance and notices. See [LICENSE](LICENSE), [THIRD_PARTY.md](THIRD_PARTY.md) and each study's attribution. This project is independent of Chess.com, Lichess and the compared projects. Research and repository preparation used OpenAI Codex assistance.
