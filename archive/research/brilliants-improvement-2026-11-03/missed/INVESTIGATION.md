# Why v3 misses89 observed Brilliants

This is a bounded exploratory investigation of the public618-case benchmark. **All618 cases are now development evidence.** The saved historical partition names do not make these experiments validation. No application code, public artifact, engine evidence or source labels were changed. No engines or browser sessions ran. Source is v3`ac298a0d69ab51808857b089063348f2adac1101`.

## Exact causes

| Disjoint reason | Misses |
| --- | ---: |
| Broader material corroboration only |53 |
| Safe-winning-alternative veto only |22 |
| Mapped quality loss>5pp only |7 |
| Both quality loss and safe-winning alternative |5 |
| Whole-window confirmation only |2 |
| **Total** |**89** |

The53 material-guard losses were awarded by v2. The other36 were also v2 misses. Overlapping counts among those 36 are 27 safe-alternative failures,12 quality failures and2 confirmation failures. None fails the legal piece-offer predicate, after-score−100cp floor or two-root availability. Relaxing those unrelated gates would not recover any of these 89.

The complete per-move source features are in`miss-features-initial.json`; aggregate facts are in`root-cause-summary.json`. The guards were evaluated from actual source and saved engine windows, not coach explanations.

## The safe-win veto is the main independent opportunity

Among22 safe-veto-only misses,11 have an explicit searched winning mate after the sacrifice. Five have a non-sacrificing centipawn alternative; six have a non-sacrificing mating alternative. Their failure is relevance, not soundness or lack of a concrete sacrifice.

Examples:

- **184752512081:53 Qf8+**: played line reaches mate; the evaluated safe alternative is+866cp. It is recovered by 900cp and the within50-of-best variant, but not 800cp.
- **185363189653:79 Qxc8**: played line reports mate8; the safe alternative is+740cp. All three variants recover it.
- **173235911852:53 Qxh6+**: played after-position is mate1; the before-position has a safe alternative reporting mate3. Every prescribed variant still rejects it because normalized mate scores are 1000. This is a useful counterexample to expecting a centipawn threshold alone to model “brilliant” relevance.
- **171711505152:69 Nxd8**: near-best mapped loss1.171pp, after+576cp, safe alternative+611cp.800/900 recover it; the within50-of-best variant does not because the safe alternative is the evaluated best move.

These are conditional engine lines, not assertions that the alternatives were played or that the available evidence proves a uniquely correct classification.

## Three prespecified complete-window experiments

Only the requested three variants were tested. Every other gate, the broader material guard and confidence logic remained unchanged. Each calls the actual copied TypeScript`classify()`over the full saved current/previous windows. Unchanged v3 parity passed all 618 symbol, provisional and withheld outputs. Material values were memoized without changing their calculation.

| Policy | TP | FP | FN | TN | Change versus v3 |
| --- | ---: | ---: | ---: | ---: | --- |
| Original v3 |220 |16 |89 |293 |— |
| A: safe threshold800cp |232 |18 |77 |291 |+12 detections,+2 false awards |
| B: safe threshold900cp |235 |18 |74 |291 |+15 detections,+2 false awards |
| C:≥600cp and within50cp of best |226 |17 |83 |292 |+6 detections,+1 false award |

No variant lost a true positive or removed an existing false award. Confidence still withholds two positives. These are exact full-policy replay results, not current-gate-only upper bounds. They do not justify selecting a threshold from the dataset and calling it validated.

`safe-alternative-experiments.json`contains all changed rows. The harness is`replay-experiments.mts`; source copies and fingerprints are in the three variant folders. A clean, private baseline copy supplies unchanged material evaluation and source credit. The replay took5.441seconds and peaked at 171,040KiB RSS. The published source directory has no dependency symlink, so a private unchanged copy was used to resolve the already installed Chessops runtime; no application source was modified.

### Counterexamples prevent a blanket relaxation

**175081315049:80 a3**is observed Best, not Brilliant. All three experiments newly award it. The safe alternative is+611cp, after-score+762cp and mapped loss−0.602pp. It is an endgame under the standard piece phase (phase 4), and the mover is already+360 physical material. A score-gap condition alone does not protect this case.

**185135318612:42 Rxd3**is observed Excellent.800/900 newly award it. The safe alternative is+603cp, after-score+589cp and loss0.465pp. Its phase is 19, but the mover is already+380 physical material. The within50-of-best version continues to reject it.

The physical values here are pawn90, minor300, rook500 and queen1000; they are pre-move board material, not the opportunity-based EC probe. Both false awards are already up at least a minor; the first is also an endgame. This supports investigating the parent's independently sourced phase/material relevance hypothesis rather than simply raising 600. Chess.com's [instructional guidance](https://www.chess.com/article/view/how-to-play-a-brilliant-move), supplied by the parent, distinguishes endgame uniqueness from multiple good opening/middlegame options and cautions against already having won substantial material. Phase8 and physical+300 are proposed operational approximations, not disclosed Chess.com constants. That candidate was not implemented or tested here. No case whitelist is proposed.

## Quality failures: distinguish genuine disagreement from evidence instability

All12 quality-failing positives still have after-scores between+283cp and+540cp. Five also have safe winning alternatives; changing quality alone cannot recover those five. The seven quality-only losses range from 5.987pp to 14.593pp. Those facts do not establish that the 5pp gate is wrong: they reflect disagreement with the observed label under this engine budget.

The most obvious evidence-quality example is **185897727454:25 Bxh7+**. Before depth17 scores the played root best at+590cp; the after-position at depth7 is+301cp, producing14.593pp loss. Its actual earlier iterations repeat this shallow discrepancy (before16,after6). The saved stronger run awards it, so this is an engine-budget sensitivity example, not proof of an unsound sacrifice.

A descriptive same-before-position root comparison would call its root loss0. However **186398857750:45 hxg6**, an observed non-Brilliant, is a counterexample to simply replacing the after-score comparison with that root score. Its cross-position loss is 5.771pp; same-before-root loss4.759pp. It has a legal offer, material corroboration, no safe veto and after-score+2cp. The descriptor therefore improves one known positive and also admits one known negative before any confidence evaluation. No additional quality-rule candidate was tested.

Recommendation: preserve the current soundness checks while investigating position-quality/forcing-line evidence and obtaining independent higher-budget confirmation for unstable cases. Do not lower the floor or globally widen loss tolerance merely to match all 12 labels.

## Confirmation failures are real score disagreement

Only two Brilliant provisional awards are withheld; no non-Brilliant provisional Brilliant is withheld in the baseline sample. Removing confirmation would look attractive on these unblinded cases but would discard the protection precisely where evidence is unstable.

- **184634890030:37 Qxh7+**: current loss−2.066pp passes. The actual prior window uses before+443cp and after+231cp, giving13.564pp loss. Independent saved stronger evidence releases this previously withheld award. This supports better confirmation evidence, not pretending the prior window agreed.
- **186007180386:89 b6**: current loss4.023pp passes; the prior window gives5.464pp (before+455cp,after+356cp). Both windows are present; this is a genuine threshold crossing, not missing data. Its higher-budget outcome is not supplied in the selected stronger subset.

`confirmation-history.json`records depths and scores. A tolerance/hysteresis change would be a new hypothesis requiring a new prespecified test; no such extra candidate was run.

## Guard-lost positives and known regressions

All53 guard-lost cases pass the other current v3 gates and were confirmed v2 awards. Examples include **169812683088:58 Rxe5** (near-zero loss, after0cp), **171636509910:68 Qxb6** (after0cp) and **171306702550:69 Qd8+** (loss3.028pp,after+393cp). Their common cause is false EC corroboration with no winning-mate exception. Winning-relevance changes cannot recover them; broader material/compensation investigation is a separate task. Disabling the guard would also restore many known false awards.

The unchanged legal-offer predicate continues to block owner Qf5+and Bf5 regressions. Ndxe5 continues to fail material corroboration for non-mating evidence; changing safe-alternative thresholds cannot itself bypass it. The published controls do not provide complete saved confirmation windows for these outside-sample positions, so no new full-window regression pass is claimed.

## Recommended next step

Use the phase/material counterexamples and the primary-source relevance guidance to formulate one coherent, source-frozen candidate. Keep full-window corroboration and the guard unless separate evidence justifies changing them. Evaluate all development trade-offs, then test the frozen candidate on genuinely unseen labeled games; historical reserved partitions in these 618 cases are no longer validation. Do not promise complete Chess.com replication or infer ordinary-game precision from this enriched set.
