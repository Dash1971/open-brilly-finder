# Repeat-award audit: useful precision component, insufficient solution

All 848 labeled cases are development evidence. This fixed hypothesis reduces false awards from 28 to 20 while losing three true awards, representing two distinct positions. It does not reach the requested future target of at most two false awards per 100 hard negatives and at least 90% balanced agreement. The historical 200-case checkpoint becomes 74 TP / 7 FP (83.5% agreement); this is now training evidence, not a new validation result.

## Exact fixed rule

Suppress a current confirmed frozen-v4 Brilliant only when it is a noncapture, nonpromotion, nonchecking move and one of the previous three own moves was itself a confirmed, full-window frozen-v4 Brilliant. That earlier move must cover ALL current qualifying offered pieces: each identical physical piece has remained unmoved, has never been captured/replaced, qualified against the earlier move's actual capture/promotion credit, and has exactly the same raw legal exchange loss after every intervening own move. Piece identity is checked against every intervening PGN move. Each structural proof has a 512-SEE-node bound; unknown evidence does not suppress. Earlier predictions use unsuppressed frozen-v4 classifications, not recursively modified badges, provisional awards, or Chess.com labels. Current and origin classifications use both saved completed engine windows.

This is a sequence-aware suppression experiment, not a change to the frozen v4 source or app. The structural prefilter and snapshot selection do not access observed labels. Labels were joined only for outcome assessment.

## Outcomes

| Development subset | Frozen v4 TP / FP | Repeat rule TP / FP |
|---|---:|---:|
| Old 618 | 246 / 15 | 243 / 10 |
| Historical 200 | 74 / 10 | 74 / 7 |
| Core 818 | 320 / 25 | 317 / 17 |
| Separate panel 30 | 2 / 3 | 2 / 3 |
| All 848 | 322 / 28 | 319 / 20 |

The initial matched 20 gives three false awards removed and no true losses, but the complete corpus disproves a zero-recall-cost interpretation. Of 848 cases, 88 were current quiet v4 awards; all relevant structural/origin checks completed, with zero structural-budget unknowns and zero missing relevant windows. Eleven changed case records correspond to ten distinct before-positions. The three true losses correspond to two distinct positions; duplicate Nb5 positions have agreeing labels.

## Every changed case

| Case | Move | Observed label | Confirmed v4 origin |
|---|---|---|---|
| 185789456944:21 | Rb1 | Good | 19 h4 |
| 186064974534:21 | Nb5 | Brilliant | 17 Rxf5 |
| 186065215864:21 | Nb5 | Brilliant | 17 Rxf5 |
| 187780685807:52 | Qh4 | Inaccuracy | 50 Rxf3 |
| 178708072359:59 | Qd2 | Great | 57 Rxb2 |
| 184420224234:79 | f7 | Best | 77 g6 |
| 184485503840:27 | Kb1 | Best | 25 h4 |
| 185769255732:61 | Qh6 | Brilliant | 59 Rxh5+ |
| 169827191694:67 | Rh1 | Best | 65 h6 |
| 173084454389:59 | Bc5 | Excellent | 57 Nxf6+ |
| 184514610842:73 | Re1 | Best | 69 Ng5 |

Re1's immediately preceding Qf4 is provisional Brilliant but withheld, so it does not qualify as an origin; the earlier Ng5 does. The other recent false Qh4 (187780686673:36) survives: its preceding Ng4 is classified Inaccuracy, even though the same Ra8 liability persists. This prevents merely inherited liability from being mistaken for a prior awarded sacrifice.

## True counterexamples and chess purpose

Both Nb5 records share the exact position. Rxf5 previously offered the rook on f5 with raw loss 500 after capture credit 300. The rook remains unmoved and exposed while Nc3-b5 creates a concrete new checking fork: after the legal acceptance ...exf5, Nc7+ legally attacks Ke8 and Ra8. This is a new tactical contribution by the moving knight, even though the sacrificed physical piece and its raw exchange loss are unchanged. The previous Rxf5 itself has a confirmed Chess.com Brilliant label in the existing data, so the false suppression cannot be blamed on a false prior predicted award.

Qh6 (185769255732:61) similarly follows a genuinely labeled Brilliant Rxh5+. The offered Rh5 retains raw loss 500; earlier capture credit was 90. Qg5-h6 renews mating geometry: ...gxh5 Qg7# is a verified legal mate sequence, and the new queen placement supplies direct Qh8#/Qg7# threats if Black does not respond. The saved engine evidence already gives mating lines before and after the move; another true award is nevertheless present. A blanket repeat-sacrifice exclusion loses it.

A generic exemption for a new substantive threat, fork, or pin is not established as a separator. False Rh1 also creates a real new tactical feature: Rf1-h1 absolutely pins Qh6 to Kh8. This pin was verified directly on the legal after-board. Thus renewed tactical purpose occurs on both sides of the labels. We have not tested or proposed another variant to exempt these examples.

## Evidence and implementation limits

Six matched-sample gaps and then one fixed completion of ten additional snapshots were collected at 300,000 nodes, one thread, 64 MB, using the existing SF18 collector and full PGN history. All 16 completed; recorded engine search time totals about 4.45 seconds. No baseline snapshot was replaced. The separate snapshot files include engine, collector, plan and runner hashes; audit-complete.json hashes its complete evidence inputs. No additional engine searches were launched. The engine slot was handed to the independent uniform-evidence task.

The exact audited frozen classifier hash is 3b8344b048290caea028cc586486910b2bdbc534e221ccdf45481dac438f4301. audit.mts performs the actual full-window native calls; summary.json contains paired counts and all changed FENs. Proofs use the native raw SEE semantics, including its ability to stop a same-square exchange while in check, for predicate parity.

A native implementation would require earlier completed classifier decisions and continuous physical-piece/offer history; three current-position snapshots alone are insufficient to recreate every prior decision. Missing history must leave the award unchanged. Predicted prior correctness cannot be guaranteed, and even correct prior awards suppress genuine new Brilliant continuations here. Stronger-analysis sensitivity already removes Bc5 independently, so its benefit must not be added twice.

The mechanism merits consideration as a bounded precision component only if losing these genuine renewed sacrifices is acceptable. Its observed eight-to-three error trade is favorable to the stated false-award priority, but temporal state complexity is not justified as a route to the 90% target by this evidence alone. No more sequence searches or rule variants are recommended from this fixed audit.
