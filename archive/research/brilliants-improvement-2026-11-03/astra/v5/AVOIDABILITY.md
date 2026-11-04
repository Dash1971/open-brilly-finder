# Voluntary static avoidability: initial 20 and complete 848

I first tested the ten recent false awards against ten distinct, feature-matched true awards, including the requested Qh4/h6 pair. The small test looked promising enough to expand: at the shared 512-node budget, all ten true awards had a legal alternative with no raw qualifying piece offer, while two false awards had no such alternative.

The complete development set then revealed important true-positive counterexamples. This feature has some diagnostic value but is not a reliable definition of whether a sacrifice was voluntary.

## Exact feature

Enumerate every legal root from the before-position in UCI order. For each, apply the existing raw legal-offer test with the move's capture/promotion credit. A rescue succeeds only when **no** nonpawn/nonking piece has a qualifying legal exchange loss. Saving one piece while hanging another does not count. No engine quality is assigned to the rescue; it can be a terrible chess move. A checking move that temporarily makes captures illegal also counts, so this is immediate static avoidability, not proof of durable material safety.

Every candidate-position check and recursive legal same-square exchange node shares one per-position budget. Run fixed caps of 128 and 512 separately. Exhaustion is UNKNOWN, never “unavoidable.” At 512, all 818 core cases completed or explicitly returned unknown in about 1.4 seconds total; the additional 30 panel cases were then appended.

The direct-stalemate exception independently checks each qualifying piece acceptance: does the original mover immediately have no legal moves and no check after that capture? This is exact legal stalemate, not a material heuristic or an inferred future draw. It uses its own shared 512-node budget. **No such witness occurred in any of the 848 cases.** This does not invalidate the known crazy-rook motif; it means that exception cannot rescue the actual counterexamples below.

## Results

| Current v4 awards | True awards | False awards | Proven unavoidable true awards | Proven unavoidable false awards |
| --- | ---: | ---: | ---: | ---: |
| Old 618 | 246 | 15 | 5 | 3 |
| Recent 200 | 74 | 10 | 2 | 2 |
| Combined core | 320 | 25 | 7 | 5 |

A mandatory avoidability gate would therefore remove five core false awards and seven true awards. In the recent 200 it would remove two of each. These are static overlays, not a new full-window policy replay.

There are ten UNKNOWN cases among the 818 core at budget 512, including four old v4 true awards; they must not be rejected. At 128 there are 135 core UNKNOWNs. The initial twenty at 128 had four unknown false awards, demonstrating why exhaustion cannot be treated as proof of forced loss.

The 30-case mechanism panel contains four observed Brilliants and 26 other labels. One Brilliant (169812573512:56 Rxc6) and nine non-Brilliants are proven unavoidable; one negative is unknown. These are feature counts, not v4 false-award removals. Several unavoidable negatives are forced/check-evasion cases that existing gates may already reject. Across all 848, there are eleven unknowns at 512.

A mate exception changes the tradeoff but does not eliminate counterexamples. Allowing either a current searched winning mate or a literal mating reply after acceptance would preserve three of the seven rejected core true awards, but also preserve Be2's false award. The provisional static overlay then removes four true awards and four false awards; in the recent set it removes two false awards and one true award. Winning-mate exceptions would need their usual complete-window replay before quoting final policy counts.

## Exact counterexamples and mechanisms

The two recent false awards correctly identified as unavoidable are:

- **178360672165:63 Nxh6+**, CC Excellent: all 42 legal roots leave an offer. The knight on f7 is attacked by Rc7, while Bh4 attacks Rf2. Moving one vulnerable piece can leave the other available. The played checking capture converts that existing double threat into a knight investment.
- **184481267900:67 Qb5**, CC Excellent: all 39 legal roots leave an offer. Nb2 forks Qd3 and Ra4; saving the queen leaves the exchange available through ...Nxa4 Qxa4.

But real Brilliants also convert unavoidable losses into meaningful sacrifices:

- **180010872764:65 Rxe4**, CC Brilliant: all 43 roots leave an offer, no immediate mate/stalemate exception. Ne4 forks Qf2 and Rg3. White deliberately sacrifices the e1 rook for that knight, choosing a better investment instead of simply paying the fork. The absence of a zero-liability alternative does not make the exchange sacrifice accidental.
- **186566789489:55 Qxf5+**, CC Brilliant: all 41 roots leave an offer, no mate/stalemate exception. The forcing line ...Qxf5 Nd6+ wins the queen back. Static avoidability treats a genuine forcing deflection as already committed material loss.
- **185357789637:42 Rcd8**, CC Brilliant: all 34 roots leave an offer, no mate/stalemate exception. Bd1 is attacked by Rd2; the rook maneuver supports ...Rxd1 after White accepts, coordinating compensation while other liabilities remain. This also defeats a refinement that exempts only captures of the attacking piece.
- **183801511095:81 Rxe4**, CC Brilliant: all 33 legal roots leave an offer, again without a mate/stalemate exception.
- **185728906786:58 Rxg6**, CC Brilliant: all three legal roots leave an offer; accepting the rook permits ...Qxf2#. A mate-after-acceptance exception would preserve this case.
- **169812573512:56 Rxc6**, panel Brilliant: all 37 roots leave an offer, no direct stalemate. This is an additional out-of-core counterexample, not an example used to select the initial twenty.

## Requested Qh4 versus h6 comparison

- **187780686673:36 Qh4**, CC Great: Black can avoid all raw offers with **Rb8**. Ra8 was already vulnerable to Bb7 after the preceding own move Ng4. Qh4 keeps that rook available while newly adding the conditional ...Bxa8 Qxh2# threat.
- **169827191694:65 h6**, CC Brilliant: White can avoid all raw offers with **Be2**. The preceding own move Qf7+ put Black in check, so ...exd3 was NOT legal then: the prior raw exchange loss on d3 is zero. After ...Kh8, h6 is White's first opportunity to leave the bishop legally offered (current loss 210), adding ...exd3 Qxg7#.

Both are avoidable and add mating compensation, so avoidability does not distinguish them. Correctly aligned legal history DOES distinguish this pair: Qh4 repeats a legally available 200-cost rook offer, while h6 makes a 210-cost bishop offer newly legal compared with the preceding own move. This supports inspecting a narrower attribution feature, but the many existing inherited-offer Brilliants still falsify a blanket novelty veto. Rescue-move engine scores were not assumed or searched.

## Recommendation

Retain avoidability as a descriptive feature and, if desired, a separately replayed precision-oriented candidate with its measured true-positive cost. Do not label an unavoidable offer “not a sacrifice.” The counterexamples show that converting a fork or existing liability into a purposeful exchange/deflection is itself a source of Brilliant moves.

This mechanism does not meet the required 90% agreement / at most two false awards per 100 hard negatives. Even the mate-exempt overlay leaves eight recent false awards and only 73 recognized Brilliants; additional independent information would still be required.

Artifacts: `avoidability20.json`, `avoidability818.json`, and `avoidability848.json`; corresponding bounded scripts are in this directory. Frozen v4 and application source remain unchanged.
