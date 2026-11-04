# Research index

The goal is an open, rating-independent Brilliant-move classifier that agrees with Chess.com more often while keeping wrong awards low. The desired long-term target is 90% recall with fewer than 1% of awarded Brilliants wrong. The evidence below does not establish that this target has been reached or that it is attainable.

The selected, deployed Mute model remains the reference: its published combined independent tests found **112/200 Brilliants (56%)**, with **3 wrong awards among 115 awards (2.61%)**. The newest 200-move subset alone found 57/100 with 2 wrong. These are sampled test results, not measured site-wide deployment rates. Later candidates and external implementations are research comparisons, not automatically recommended replacements. Negative experiments and contradictions are retained so that others can avoid repeating an attractive but unsuccessful idea.

## Foundation and independently evaluated models

- [Selected Mute Selective model and exact algorithm](../studies/brilliant-moves/README.md): the 848-example, 64-tree model, 75 predictors, chess-quality gates, unknown handling and two-window award rule.
- [Original readable study](../studies/brilliant-moves/REPORT.md) and [methods](../studies/brilliant-moves/METHODS.md): across two independent 200-move tests, Mute found 112/200 Brilliants and made 3 wrong awards among 200 controls; En Croissant found 53/200 and also made 3 wrong awards.
- [Expanded-data overnight study](../studies/brilliant-training-2026-11-03/README.md): on the reserved 89-game comparison, the existing Mute model found 42/71 Brilliants with 2 wrong awards among 494 challenging ordinary moves. En Croissant found 18/71 with 3 wrong awards. The expanded-data forest found 37/71 with 0 wrong awards. Adding data did not establish a better replacement.

These independent-test numbers are not interchangeable with the reused development-set results below. See [Data and evaluation boundaries](DATA.md).

## November 4 sequence

Except where stated otherwise, model experiments use the same 3,724 moves, 917 positives, 2,807 negatives and 972 groups. Their usual reference is the original custom learner with inner-selected thresholds: **452 correct awards / 6 wrong**. The fixed-cutoff control is 436/6; the standard random forest reference is 473/7. Reports specify the exact comparator and whether a model was refitted, held fixed, or not used.

| Study | Question | Result and interpretation |
| --- | --- | --- |
| [Standard learners](../studies/brilliant-standard-learners-2026-11-04/REPORT.txt) | Would a standard learner improve on the custom forest using the same saved features? | Standard RF found 473 with 7 wrong, versus custom 452/6. No established replacement at the desired error tradeoff. |
| [Matched sacrifices](../studies/brilliant-matched-sacrifices-2026-11-04/REPORT.txt) | How do missed sacrifices compare with similar ordinary tactics? | Diagnostic investigation; rejected simple shortcuts and proposed a conditional response-gap feature. No accuracy gain established. |
| [Conditional response gap](../studies/brilliant-conditional-gap-2026-11-04/REPORT.txt) | Does dependence on a specific response after acceptance distinguish Brilliant? | Custom 424/7; standard RF 477/7. The small RF gain was uncertain and did not recover the motivating difficult subgroup. |
| [Review context and deeper analysis](../studies/brilliant-review-context-2026-11-04/REPORT.txt) | Do engine evaluation, review strength or settings explain matched labels? | Some evaluation differences, but deeper search and the tested settings did not remove the central Brilliant/ordinary distinctions. Diagnostic only. |
| [Acceptance trajectories](../studies/brilliant-acceptance-trajectory-2026-11-04/REPORT.txt) | Do lasting material debt, recovery timing, mate and draw outcomes help? | Custom 408/6; standard RF 472/8. No useful overall improvement. |
| [Focused mating offers](../studies/brilliant-mating-offers-2026-11-04/REPORT.txt) | Can a narrow sound-mating-offer treatment recognize a Legal's-mate-like queen offer? | Caught the motivating Ne5 example but introduced wrong awards in the labeled corpus. |
| [Nonmating material alternative](../studies/brilliant-nonmate-material-2026-11-04/REPORT.txt) | Does also winning material without mate distinguish ordinary tactics? | Verified the motivating Ne5 as Brilliant in the imported review. A fixed refinement added 3 correct and 0 wrong awards on reused data; a broader selector failed the error criterion. This small gain needed fresh validation. |
| [Fresh mating-offer test](../studies/brilliant-mating-prospective-2026-11-04/REPORT.txt) | Does that frozen candidate work on newly reviewed mating offers and controls? | Failed: 12 additional awards comprised 4 correct and 8 wrong. Seven Brilliants remained missed among the 12 controls. This targeted 24-game sample is distinct from the 3,724-move development set. |
| [Mating mechanisms](../studies/brilliant-mating-mechanisms-2026-11-04/REPORT.txt) | What separates the 4 correct awards, 8 wrong awards and 7 misses? | Contradictory mating/material patterns remained. No new rule or classifier trial. |
| [Voluntary material choices](../studies/brilliant-material-choices-2026-11-04/REPORT.txt) | What is actually given up relative to realistic alternatives in those 19 cases? | Material accounting clarified the chess but did not consistently separate Brilliant from Great/Best. Contradictions retained. |
| [Evaluation consistency](../studies/brilliant-evaluation-consistency-2026-11-04/REPORT.txt) | Can consistent evaluation fix misses with the forest held fixed? | 454/8 versus 452/6: four gains, two lost correct awards, two new wrong awards. Rejected. |
| [Forest miss diagnosis](../studies/brilliant-forest-miss-diagnosis-2026-11-04/REPORT.txt) | Why are 429 eligible Brilliants below cutoff? | Exact score reconstruction found strong dependence on En Croissant material features and preference for moved-piece captures. Most misses were below cutoff in both windows. Diagnostic, not a measured matching ceiling. |
| [Independent acceptance-mate feature](../studies/brilliant-independent-mate-2026-11-04/REPORT.txt) | Does recording mates independently of En Croissant fix an encoding gap? | Custom 449/6 versus 452/6; standard RF 462/7 versus 473/7. Correcting the representation did not improve the overall tradeoff. |
| [Sacrifice-compensation links](../studies/brilliant-compensation-links-2026-11-04/REPORT.txt) | Can piece identities, acceptance movement and compensating motifs capture missing information? | Produced legal relational descriptions and a specific fork hypothesis. It did not establish that these relations predict the labels. |
| [Accepting-piece fork plus check](../studies/brilliant-acceptor-fork-2026-11-04/REPORT.txt) | Does that relationship add value alongside check and the existing features? | Custom 413/6 versus 452/6; check-only 448/6. Standard RF 465/8 versus 473/7. Rejected. |
| [External source review](../studies/brilliant-external-repos-2026-11-04/REPORT.txt) | Do other open classifiers offer useful mechanisms or an established solution? | Reviewed five implementations. Found specific alternative evidence strategies but no convincing independent Chess.com precision/recall benchmark. |
| [Frozen external comparison](../studies/brilliant-external-comparison-2026-11-04/REPORT.txt) | Do unchanged Knight's Eye and WintrChess rules recover our misses safely? | Both-window Wintr: 287 correct / 20 wrong; Knight's Eye: 590 / 142. They recover different misses but add too many wrong awards. Knight has 34 positive and 22 ordinary cases unresolved; Wintr has 5 ordinary cases unresolved. |

## How to read an experiment

Start with its `REPORT.txt` or README, then inspect the frozen protocol, result JSON and per-case predictions. Verification files document which invariants were actually checked. A source hash records the exact artifact; it is not proof that the method is correct. Historical `STOPPED`, correction and failed-attempt records are part of the audit trail rather than results to erase.

Keep these distinctions explicit when building on the work:

- A semantic diagnosis can reveal missing information without demonstrating a predictive improvement.
- A few recovered examples do not compensate automatically for lost correct awards or additional wrong awards.
- A rule that passes reused development data can fail fresh targeted validation, as the mating-offer experiment did.
- A more generous external policy can increase recall while greatly worsening the wrong-award share.
- A missing engine proof is not a negative label, and a saved principal variation is not an exhaustive search of every response.

## Referenced external work

The source review and frozen comparison pin exact commits for [WintrChess](https://github.com/WintrCat/wintrchess-lib) and [Knight's Eye](https://github.com/knights-eye-chess/move-classifier). The review also covers [Chess-Review](https://github.com/T-Julsgaard/Chess-Review), [Felix's chess-game-review](https://github.com/FelixYUFENGSU/chess-game-review) and [Brilliant-Chess](https://github.com/wdeloo/Brilliant-Chess). Chess-Review credits Brilliant-Chess ancestry; Knight's Eye credits WintrChess's prose ideas. These are not five independent demonstrations of Chess.com equivalence.

The original selected-model study preserves [reference and attribution notes](../studies/brilliant-moves/reference/README.md), including En Croissant. This project is independent of Chess.com and those projects. Their code, documentation, policies and licenses should be credited separately from our benchmark conclusions.
