# Frozen fresh-test results

The fixed candidates were evaluated on 200 new moves from 106 games: 100 explicitly Brilliant and 100 explicitly non-Brilliant, with 20 of each per account. The model/rules/threshold were fixed before these labels.

| Candidate | Recognized /100 | Extra awards /100 | Sample badge precision | Agreement |
| --- | ---: | ---: | ---: | ---: |
| forest | 55 | 1 | 98.21% | 77.0% |
| S | 78 | 5 | 93.98% | 86.5% |
| ec_direct | 26 | 2 | 92.86% | 62.0% |
| A | 78 | 6 | 92.86% | 86.0% |
| v4 | 78 | 6 | 92.86% | 86.0% |
| ec_confirmed | 26 | 2 | 92.86% | 62.0% |

The forest recognition rate is 55%; its sample badge precision is 55/56=98.21%. Its extra-control rate is 1/100=1%, not zero. The history rule trades more extra awards for more recognition. None reaches 90% agreement.

## Descriptive 95% Wilson intervals

- **forest:** recognition 55.00% (45.24–64.39%); extra-control rate 1.00% (0.18–5.45%); sample badge precision 98.21% (90.55–99.68%); agreement 77.00% (70.69–82.29%).
- **S:** recognition 78.00% (68.93–85.00%); extra-control rate 5.00% (2.15–11.18%); sample badge precision 93.98% (86.66–97.40%); agreement 86.50% (81.07–90.55%).
- **ec_direct:** recognition 26.00% (18.40–35.37%); extra-control rate 2.00% (0.55–7.00%); sample badge precision 92.86% (77.35–98.02%); agreement 62.00% (55.11–68.44%).

Wilson intervals treat moves as independent. Moves share games; these are descriptive binomial intervals, not game-cluster-adjusted uncertainty. Balanced/enriched controls do not estimate natural-game prevalence or deployment badge precision. Zero observed errors is point0 with a nonzero upper interval, never a universal guarantee.

## Missingness and limits

No physical-feature timeout, insufficient-confidence case or S proof unknown occurred. Four avoidability proofs are unknown in both windows and retain the frozen missing-value routing. Other None values describe alternate cp/mate fields, absent top-two played roots, absent safe alternatives and inapplicable no-offer material features; they are not all proof failures.

The extractor remains limited to the pinned SF18 / 300k evidence domain. Native SF19 is unvalidated. Full per-account metrics, Wilson intervals, labels, source URLs and all fixed feature/proof/decision traces are in [fresh-results.json](fresh-results.json); compact decisions are in [fresh-predictions.csv](fresh-predictions.csv). Source and identity checks are in [FINAL-AUDIT.json](FINAL-AUDIT.json).

The forest’s sole extra award is Hansen 37.Rxd7+ (game 172662051055, ply 73), currently labeled Excellent. No error-driven adjustment or additional search was performed.
