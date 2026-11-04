# Decision-scoped corroboration variants C and D

Both requested variants were implemented and replayed through actual current/prior complete-window classification on all 848 now-development cases. No additional candidates or threshold grid were tried. Frozen v4 and application source remain unchanged. Its native replay again reproduces core TP320/FP25 and panel TP2/FP3.

| Dataset (now development) | V4 TP / FP | C TP / FP | D TP / FP |
| --- | ---: | ---: | ---: |
| Old 618 | 246 / 15 | 240 / 24 | 236 / 20 |
| Historical recent 200 | 74 / 10 | 80 / 12 | 78 / 8 |
| Core 818 | 320 / 25 | 320 / 36 | 314 / 28 |
| Mechanism panel 30 | 2 / 3 | 2 / 7 | 2 / 5 |
| All 848 | 322 / 28 | 322 / 43 | 316 / 33 |

**C is worse overall: it gains no net true awards and adds fifteen net false awards across 848. D is also worse overall: it loses six net true awards and adds five net false awards.** The historical recent-200 agreement rises from 82% to 84% for C and 85% for D, but these are selected development results and neither approaches the required false-award rate. C has twelve and D eight extra awards per 100 hard negatives, versus the desired maximum two.

## Exact implementation

C requires at least one fully proven attributed raw piece offer globally. An acceptance qualifies only if its same-square net exchange gain exceeds current capture/promotion credit plus 100. Its victim must have moved on the sampled move, or—with real aligned preceding-own-position history—have strictly greater raw vulnerability than before, or be subject to a newly legal specific capture. Attribution, quiet-value evidence and mate evidence refer to the same qualifying acceptance/victim. Unknown history cannot invent novelty for an unmoved piece.

Corroboration is then EC sacrifice, an explicit winning mate in the evaluated window, an attributed exact mate-after-acceptance witness, or the requested quiet condition: the move is neither a capture nor a promotion and either moves the offered piece or offers a piece valued at least as highly as the moving piece. Values are unchanged; king value remains zero, with no king-type ban. En passant counts as a capture. Castling rook movement counts as movement of the offered rook. The whole proof shares 512 visited positions; exhaustion preserves only already completed existential proofs. Further mate work is skipped once EC or the quiet proof already supplies sufficient corroboration.

D adds the complete static avoidability veto, with the same original direct-mate, explicit-winning-mate and direct-stalemate exceptions as B. Unknown avoidability supplies no veto. Explicit winning mate is tested separately in each completed evaluation window. All original soundness, floor, phase-aware alternative and confidence gates remain intact. The EC comparator and negative quality labels are unchanged.

## Paired changes

| Dataset | Variant | Newly matched Brilliants | Lost Brilliants | Added false awards | Removed false awards |
| --- | --- | ---: | ---: | ---: | ---: |
| Old 618 | C | 5 | 11 | 17 | 8 |
| Old 618 | D | 4 | 14 | 14 | 9 |
| Recent 200 | C | 7 | 1 | 6 | 4 |
| Recent 200 | D | 6 | 2 | 4 | 6 |
| Panel 30 | C | 0 | 0 | 4 | 0 |
| Panel 30 | D | 0 | 0 | 2 | 0 |
| All 848 | C | 12 | 12 | 27 | 12 |
| All 848 | D | 10 | 16 | 20 | 15 |

## Why the causal hypothesis fails

The quiet/capturing distinction does not separate actual investment from ordinary combinations. A combination can begin with a quiet offered piece and recover material on the next move just as directly as a capturing sacrifice does.

Concrete newly admitted false awards under C include:

- **184131911424:102 Rb2+**, CC Excellent: the offered rook moves, but ...Kxb2 Kxd3 recovers the material on another square. The quiet-move exemption admits an ordinary exchange mechanism.
- **184430456986:28 Bg4**, CC Best: the bishop move leaves the more valuable rook offered; ...Nxa8 Bxd1 wins material elsewhere. The relative-piece-value rule does not prevent cross-square recoup.
- **184727349064:54 Bh5**, CC Excellent: ...Qxh5 Qxa1 recovers material. In the same game, **46...Nc4 is Brilliant** and also permits cross-square recovery after ...dxc4. Both are recovered by C. Their different labels cannot be reconstructed merely from whether the first move captures or the offered piece moves.
- **174183730932:58 Rd8**, CC Best: ...Rxc7 Rxd3 and later recovery again make the broader material guard relevant even though the original move is quiet.
- **174472144890:56 Kd7**, CC Great, and **185225502512:86 Kd5**, CC Excellent: newly attributed higher-value offers satisfy the stated king-value-zero rule, but their labels remain non-Brilliant. This is evidence against the complete model, not a proposal to add a special king ban.

The seven recent true recoveries are Be6+, Bg8+, Nc4 in two games, Rh3+, Ne2+, and Rf2+. Several also recover material across squares. Thus simply restoring the cross-square material veto would surrender precisely the additional recognition this hypothesis sought.

The global attribution requirement also discards genuine Brilliant decisions that maintain an existing liability. C loses exd5 (169826869102:49), Ng4, f4, Nf6, repeated Nb5 positions, Nge2 and Rcd8 among the older examples. Its recent lost Brilliant is **174184365826:77 Kxf3**: the existing queen liability is compensated by an imminent promotion after ...Rxb6 c8=Q. The move can be a meaningful new decision without making that offered piece newly vulnerable.

D removes some newly admitted quiet false awards, but also loses genuine sacrifices and fails to restore overall performance. The panel adds four false awards under C and two under D, without recovering either of its missed Brilliants. That is further adverse evidence for this particular causal model.

## Fixed capture regression and scope

The original **186311900336:28 Ndxe5** regression was checked directly: EC corroboration remains false, there is no exact mate-after-acceptance witness, the moved knight is attributable, and **quiet corroboration is false because Ndxe5 captures**. Its broader material protection is therefore retained. This local success does not offset the new quiet-combination false awards.

Files: `variantC.ts`, `variantD.ts`, `offerDecisionProofs.ts`, `replay-CD.mts`, `results-CD.json`, and `check-CD.mts`. The results retain every paired output and source hash. Diagnostics named `decisionWithoutEcEarlyExit` expose all board-based corroboration options; actual classification short-circuits unnecessary proof work when EC has already corroborated an attributed offer. Full three-policy replay plus diagnostics took about 8.2 seconds. No new engine evidence was created.

Recommendation: do not promote C or D. These results show quantitatively that the proposed structural exemption is insufficient, rather than suggesting another threshold adjustment. No further variants were tried pending parent review.
