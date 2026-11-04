# Independent assessment of frozen v4's fresh 200-case test

V4 is a credible PR recommendation for the stated goal of recognizing more satisfying sacrifices while retaining a material filter. The fresh test supports a modest recall/quality tradeoff, **not improved independent-test precision or fewer false awards**. Keep the frozen algorithm unchanged; the remaining errors are evidence to disclose, not a reason to fit another exception to this test.

I checked the frozen results against the saved engine windows and inspected all ten v4 false awards and seven newly recognized Brilliants. No engine reruns, browsing, or policy changes were performed. The mechanism panel and stronger recheck were not used in this assessment because final paired outputs were not yet available.

| Fresh 200-case result | V3 | V4 |
| --- | ---: | ---: |
| Observed Brilliants recognized | 67 / 100 | 74 / 100 |
| Missed Brilliants | 33 | 26 |
| Extra awards on explicit non-Brilliants | 9 / 100 | 10 / 100 |
| Overall agreement | 79% | 82% |
| Precision within this selected sample | 67/76 = 88.16% | 74/84 = 88.10% |
| Predeclared FN + 3×FP cost | 60 | 56 |

The paired changes are seven newly matching awards and one new disagreement, with no existing matching award lost and no existing false award removed. This is not a Pareto improvement: one error dimension improved and the other worsened. Under the weighting fixed in PLAN.json before fresh labels, the tradeoff is favorable. Only eight decisions changed; the modest sample and shared-game/account structure do not establish a stable population improvement. Balanced, deliberately difficult controls do not estimate ordinary-game badge precision or frequency.

## What the changed examples establish

Newly recognized observed Brilliants include h6 (169827191694:65), Nxg6 (171118868402:33), Bf6 (172590636870:45), Be3+ (173049117092:40), Nxe2 (174429457866:50), Rxf7 (184431785024:65), and Rxg6 (185728906786:58). These include quiet threats and offers involving a different piece, supporting the purpose of recognizing more than obvious moved-piece sacrifices. Exact legal witnesses include h6 ...exd3 Qxg7#, Nxg6 ...hxg6 Rxe7#, and Rxg6 followed by either Qxg6 or hxg6 permitting Qxf2#.

The one new false award is **187780686673:36 Qh4**, observed as Great (!). It has a real poisoned rook offer: White can play Bxa8, but Black then has Qxh2#. The saved best-defense line instead starts Nf3 Qe1+ Nxe1 Bxc1. Its mover-relative after-score is +149 centipawns. This is the same substantive limitation already seen in development's Qb2/Qf6: a genuine, sound, newly created mating threat after acceptance does not guarantee a Brilliant label. It is not evidence that v4 simply discarded the ordinary-combination material filter, and it is not a justification for a named-move exception.

## What remains unresolved

The nine inherited false awards persist. They span several mechanisms:

- Rh1 (169827191694:67) continues a winning attack just after the newly recognized h6; its material can be recovered across squares.
- Rxh2 (174425603426:123) gives a rook to enable a passed pawn's promotion. A capture-only probe does not model the later quiet pawn push/promotion adequately.
- Qb5 (184481267900:67) has a genuine exchange cost after Nxa4 Qxa4 but is Excellent on Chess.com.
- Nxh6+ (178360672165:63) has a real knight offer and near-equal engine evaluation, but is Excellent.
- Qg6+ (186393990159:71) is a mating continuation with another mating option, yet observed Best. Conversely, several development Brilliants also have multiple mating options, so that fact alone is not a safe veto.
- Bc5, gxf4, Re1, and dxc4 supply further sound offer/compensation disagreements; the physical-material heuristic does not reproduce the site's editorial boundary.

Neither lower material-debt thresholds nor broader capture recovery alone can resolve these distinctions. The frozen checked-continuation suppression removed three development false awards but removed none of the fresh main-test false awards. Do not claim that component independently generalized from this test; the targeted mechanism panel may provide diagnostic evidence, reported separately.

V4's benefit is better recognition with approximately unchanged selected-sample precision. It has not demonstrated better ordinary-tactic rejection than v3 in the fresh test. It retains the EC/material-or-mate corroboration and legal-offer protections, so it is still materially more constrained than abandoning that guard. A specific claim that the original ordinary pawn-winning example remains rejected should cite its actual frozen-policy regression replay, not infer it from aggregate counts.

## Recommended reporting

“On 200 new, explicitly reviewed moves, the frozen rule recognized 74 of 100 Chess.com Brilliants, up from 67. It made ten extra awards instead of nine. Agreement rose from 79% to 82%, and the predeclared error score improved from 60 to 56. This supports a more generous badge without a material drop in precision in this selected test; it does not show fewer false awards or measure how much more fun the badge feels.”

Use the fresh result as the principal evidence for the recommendation. The combined 818-case numbers—v3 TP287/FP25 versus v4 TP320/FP25—are useful descriptive totals, but mix 618 development cases with 200 fresh cases. The combined equal false-award count must not obscure the fresh increase from nine to ten. Do not describe all 818 as untouched validation.

Publish the stronger recheck and the mechanism panel separately when complete. Do not selectively replace baseline outcomes with stronger results or fold a mechanism-enriched panel into the balanced main denominator. No claim of 99% agreement, universal superiority, improved independent-test precision, or measured enjoyment is supported.
