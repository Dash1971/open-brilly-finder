# Small semantic-tree diagnostic

The two prespecified trees do **not** establish a path to 90% agreement with low false awards. All 848 cases are already unblinded development data. Five-fold grouped cross-validation is a diagnostic of this feature bank; it is not another independent test.

| Tree | Operating point | Grouped-CV agreement | Brilliant recall | Extra awards | Sample precision |
| --- | --- | ---: | ---: | ---: | ---: |
| depth3 | default_cost 5 | 79.4% | 62.0% | 18 /435 (4.1%) | 93.4% |
| depth3 | strict98 | 67.0% | 33.4% | 5 /435 (1.1%) | 96.5% |
| depth4 | default_cost 5 | 82.5% | 69.7% | 23 /435 (5.3%) | 92.6% |
| depth4 | strict98 | 74.6% | 49.6% | 7 /435 (1.6%) | 96.7% |

The strict points keep extra awards below 2% of the 435 sampled non-Brilliants, but recall falls to 33–50%. None achieves the desired combination of at least 90% agreement, at least 82% recall and low false awards. The full-data depth-four fit reaches 88.8% agreement at its default point; that is resubstitution, not cross-validation or evidence of generalization. Its strict full-data fit has 247 true awards and 2 false awards while missing 166 observed Brilliants. Those tradeoffs cannot be hidden behind precision alone.

## What was fixed before fitting

[PROTOCOL.json](PROTOCOL.json) fixes depth 3/depth 4, at least 15 distinct moves per leaf, negative-class cost 5 and two operating points. The default leaf decision compares weighted positive versus negative support. Strict 98 uses the **raw, unweighted fraction of positive window rows ≥0.98**, not a weighted or calibrated probability. No threshold grid, configuration winner or additional fit was selected after these results.

Cases are unioned by whole game and identical normalized four-field before-position. The 439 games form 434 connected groups; a fixed SHA-256 rule assigns those groups to five folds. Current and prior completed-window rows remain in the same group/fold. Thus dual-window duplication and repeated sampled positions cannot cross the training/test boundary. The 75 semantic descriptors expand to 150 numeric inputs with explicit null indicators. No game ID, ply, date, account, rating, cohort, gallery category, coach text, SAN/UCI string or square/FEN occupancy enters a split.

Training uses only eligible window rows: raw legal offer, two roots, mapped quality loss<=5 and mover after-score>=−100. Cases have equal total fitting weight over their eligible windows, then negative cases receive cost 5. Final awards require **both window predictions**, both original eligibility masks and confidence compatibility. This fixed architecture can theoretically recognize 394/413 observed Brilliants (95.4%); the simple trees do not approach that ceiling while keeping false awards low.

## What the trees notice

The full-data descriptive trees split on EC material margin, whether an offered piece moved, phase/material balance, prior-position evaluation improvement and whether the offer was already present on the same square. These are interpretable leads, not validated production rules. Both [depth-three](depth3-rules.txt) and [depth-four](depth4-rules.txt) trees expose every threshold and leaf’s raw class support, distinct moves, weighted support and decisions. The large gap between full-data and grouped-CV results, and strict-leaf instability across folds, warn against transplanting their exact thresholds into the app.

Physical material uses the recorded three-ply capture/promotion/check-evasion probe. It omits quiet moves outside check and preserves checked-horizon/mate limitations; no mate sentinel is treated as physical material. Thirty panel rows were filled with the same bounded kernel to avoid a missing-physical-feature flag identifying panel membership. The prior raw-vulnerability attribution uses legal same-square exchanges with a 512-node cap. Unknown proof states stay explicit.

One source-bank issue was caught before fitting: `same-root-results.json` contains 818 unique keys plus 30 stronger-budget repeats, not 848 unique panel-inclusive cases. Played-root presence, rank and gap were instead derived directly from the correct baseline current/prior snapshots. Unsearched roots stay null. The `mating_acceptance` field is the existing v4 **additional corroboration flag tested only when EC sacrifice is absent**, not an exhaustive mate-acceptance test; its inapplicable false state must not be interpreted as proof of no mate.

## Audit and reproduction

[features.json](features.json) and [features.csv](features.csv) contain 848 cases/1,696 linked window rows. [FEATURE-DEFINITIONS.json](FEATURE-DEFINITIONS.json) documents units and limitations. Identity fields in these files exist only for joins, grouping and review. [AUDIT.json](AUDIT.json) checks group isolation, feature allowlisting, leaf sizes and final award guards. [predictions.csv](predictions.csv), [RESULTS.json](RESULTS.json), full trees and fold trees expose every result.

`features.py` reuses saved evidence and the copied bounded [physical kernel](physical_kernel.py); `cart.py` implements the small study-local NumPy CART directly. Neither calls an engine, browser or service. Existing python-chess/NumPy dependencies are reused. Feature extraction peaked at 95 MB and fitting at 75 MB, under the 256 MB cap. No app or public report is changed.

```sh
python3 features.py
python3 cart.py
```

The commands regenerate the declared two configurations only. The separately authorized weak-versus-strong extension has its own frozen protocol and outputs under `surprise-extension/`; it does not replace these outcomes.
