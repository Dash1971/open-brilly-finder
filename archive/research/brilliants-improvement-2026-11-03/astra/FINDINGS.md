# Independent classifier error analysis

All 618 published cases are development evidence here. This is descriptive error analysis, not a new validation result or an application change. No engine, browser, installation, or source-policy changes were made. The saved baseline engine lines are the only engine evidence used.

I inspected all 16 v3 false awards and all 53 true awards lost from v2 to v3, plus all 61 false awards removed by that guard to check proposed recovery mechanisms. `error-features.json` contains these 130 cases, their actual last seven played plies, legal offered-piece identity/history, immediate capture/promotion credit, raw physical-material probes, EC material scores, and first ten plies of the two saved reply PVs. Python's copied material probe remains heuristic: stand-pat in check and omitted quiet evasions can distort outcomes; reported lines are conditional, not forced. All probes completed under their one-second/100,000-call per-position cap; summed probe time was approximately 0.08 seconds.

## Most promising: corroborate poisoned acceptance with a literal mate witness

The existing mate exception only sees the opponent's best defense. A sacrifice can be sound precisely because accepting loses to mate while declining avoids mate. Requiring the after-position's best-line mate misses that mechanism.

Specific candidate: retain the existing legal offer, soundness, safe-alternative and confirmation gates. Permit the EC corroboration gate to pass if **at least one qualifying legal acceptance of an offered piece permits a legal mate-in-one reply**. The acceptance must already exceed current capture/promotion credit plus 100 in the existing legal-offer test. Save the exact two-move proof. This is bounded legal move enumeration, not a new engine search.

Among the v2/v3 disagreements this feature appears in **11 of the 53 lost true awards and 2 of the 61 removed false awards**. One pair of positive games has the identical Ne5 position, so 11 cases are not 11 independent motifs. These are feature counts, not a full confidence-window policy replay or a prospective prediction.

Examples:

- 185741429132:55 Ng6+: ...Rxg6 Rxe8#; the best defense is ...Kg8 with finite evaluation, so v3's current mate exception does not activate.
- 186312822844:27 Qh5: ...Qxd3 Qxh7#; original position evaluates near equality, but accepting the bishop loses immediately.
- 185214494356:53 Rf8: ...Qxf8 Qxg6#.
- 186371637568:13 and 186371786706:13 Ne5: ...Bxd1 Bxf7#.

Counterexamples prevent calling this a solved boundary:

- 186389789789:54 Qb2 is CC Best: ...Rxc8 Qxg2# also satisfies the witness.
- 187173495367:42 Qf6 is CC Great (!): ...Bxd5, ...Rxd5, or ...exd5 each permits ...Qxb2#.

I recommend this as the first frozen candidate to replay. Do not immediately extend to arbitrary mate depth or acceptance-engine scoring: first measure the simple interpretable feature. New evidence should deliberately include both awarded and non-awarded poisoned offers, including attacks already supported by a rook or bishop, and should deduplicate tactical positions across games.

## Narrow false-award hypothesis: forced check-evasion continuation

Eleven of the 16 false awards have every current offered piece already similarly losable after the previous own move. But inherited offers also occur among true Brilliants, so the blanket novelty veto remains falsified.

A narrower candidate is to suppress an award when the player **is in check**, every qualifying offered piece **stays on its square**, and each has the **same positive legal same-square exchange loss** as after the previous own move. This describes continuing an existing sacrifice while answering a check, not creating the sacrifice decision. Compare raw exchange vulnerability, not the previous move's credited `hasPieceOffer`: earlier captures can mask continuity.

On the current v3 awarded set, only five moves begin in check:

- 185741429132:59 Kh1, CC Best: unchanged Ng6 loss 210 and Re6 loss 410; preceding own Rxe6 captured 500.
- 184405419484:29 Ke2, CC Best: unchanged Be4 loss 300.
- 185392726850:63 Kh1, CC Best: unchanged Rg7 loss 500.
- 186007180386:99 Be2, CC Best: Bg1 becomes newly capturable; this hypothesis would not suppress it.
- 185744987064:76 Nxe6, CC Brilliant: the moved knight creates a new offer; this hypothesis would retain it.

Thus the feature identifies three current false awards and no current true awards. That is promising but thin: the sample contains only one awarded Brilliant check evasion, and gallery sampling does not establish that quiet king/check-evasion sacrifices are absent. Seek fresh explicit-label check-evasion cases with inherited offers before adopting this as a universal veto. Do not substitute a king-move ban.

Existing previous/before/after FEN windows provide the required state without more engine searches. First-move or two-position windows must have explicit unknown history, not an invented predecessor. Castling and promotion identity need handling if generalized beyond the observed cases.

## Lower-priority: physical debt rescue with decision novelty

EC compares two optimized material-search values, not physical material actually owned before the move. As a result it sometimes misses offers where a material liability already existed or acceptance permits a mate that the heuristic handles oddly.

An acceptance-conditioned raw physical debt greater than 100 occurs in **21/53 lost positives**, but also **19/61 removed false positives**. Requiring that the *same offered piece* was not already legally losable by more than 100 after the previous own move leaves **20 positives / 11 false positives**. This is a weak exchange at v3's current precision and should not be adopted as a broad escape hatch.

Useful examples:

- 185758528940:38 Nh5 leaves Nh2 offered: physical cost 300 after ...Rxh2, whereas EC before/after are -300/+300 and report no incremental sacrifice.
- 185780133400:27 Ne6: physical cost 300 after ...fxe6, yet EC before/after 90/0 report no sacrifice.
- Counterexample 185705662220:45 Qb1, CC Excellent: newly exposes Ra1 to ...Bxa1 Qxa1 for a real 200 loss. It passes both debt and novelty, while v3 correctly rejects it.
- Within the same game, 186312822844:27 Qh5 is Brilliant and 29.Nxf7 is Best; both carry physical debt 210. Qh5 has the immediate mate witness above, while Nxf7's relevant acceptances do not. Thresholding debt alone cannot resolve that difference.

The 32 other lost true awards have no net debt >100 under this physical probe. They include queen deflections, cross-square material recovery and exchanges: 171306702550:69 Qd8+ Rxd8 Rxa7 immediately trades queens at equal material; 185705662220:35 Rxd3 Nxd3 Nxb6 wins material elsewhere; 186221189079:60 Nc3 Nxc3 Qxc7 restores material. Chess.com sometimes awards these and sometimes labels similar recoveries Excellent. No uniform material-loss definition can recover all of them while rejecting all ordinary combinations.

If this avenue is pursued, the next evidence should characterize the **specific acceptance and compensation mechanism** (forced mate, long-term positional compensation, deflection followed by material recoup) rather than sweep debt thresholds. Small, explicitly matched positive/negative cases are more informative than more copies of familiar sacrifice openings. Existing after-position top-two PVs often omit the offered acceptance; a later bounded search of those missing acceptance branches could establish tactical truth, but cannot itself prove Chess.com's unpublished labeling preference.

## All 16 remaining false awards

| Game:ply | Move / observed label | Material/history finding |
| --- | --- | --- |
| 181378701223:25 | Ng5 / Best | Inherited Ra1 exchange loss 200 |
| 185741429132:59 | Kh1 / Best | Check evasion; inherited Ng6/Re6 losses 210/410 |
| 185789456944:21 | Rb1 / Good | Inherited Bg5 loss 210 |
| 185966790779:67 | Qxf7+ / Best | New queen offer; ...Qxf7 Nxf7 Kxf7 sacrifices a knight into a winning pawn ending |
| 186032403160:57 | Qe4 / Best | Inherited Re1 exchange loss 200; saved main line leads to repeated checks |
| 187780685807:52 | Qh4 / Inaccuracy | Inherited Rf3 loss 410; stored engine quality disagrees with CC; stronger saved study withheld this award |
| 165566275946:19 | Qxb7 / Best | Inherited Rh1 loss 500; taking a bishop credits 300, leaving real exchange debt 200 |
| 178708072359:59 | Qd2 / Great | Inherited Rb2 loss 500; long forcing material sequence in saved best line |
| 183800911053:48 | Rxe4 / Inaccuracy | New exchange offer, debt 200; mapped loss 4.815 lies just inside five-point gate |
| 184128361014:30 | Qd7 / Good | New Rb8 exchange offer plus inherited Bg2 offer; one recovers material, the other can lose it |
| 184405419484:29 | Ke2 / Best | Check evasion; inherited Be4 loss 300 |
| 184420224234:79 | f7 / Best | Inherited Bg1 loss 300; ...Rxg1 f8=Q uses promotion compensation beyond capture-only probe |
| 184485503840:27 | Kb1 / Best | Inherited Bg5 loss 210 |
| 184618492488:55 | Qe8+ / Best | New legal Nf5 acceptance after check; saved line finds drawing perpetual/recoup |
| 185392726850:63 | Kh1 / Best | Check evasion; inherited Rg7 offer; already winning mating attack |
| 186007180386:99 | Be2 / Best | Check evasion; newly accessible Bg1; best defense still loses to mate |

Priority: replay the mate-witness rescue first, separately measure the narrow check-evasion suppression, then freeze any combined candidate before fresh labels. Keep physical-debt rescue diagnostic unless new evidence separates its many counterexamples. These features do not justify promises of near-perfect reproduction of Chess.com.

## Complete feature handoff

`all-618-mate-history-features.json` contains compact features for all 618 development cases; `mate_history_features.py` reproduces it from the published baseline. There are zero unknowns and zero raw-offer mismatches with the published TypeScript feature. Total descriptive board-feature generation took about 0.27 seconds in Python (not a production latency benchmark).

The exact legal mate witness occurs in 43 Brilliant cases and four non-Brilliant cases overall. The two additional negatives are 185774962202:37 Qg6 and 174480720608:115 e7; v2 already rejects them. Requiring *all* qualifying captures of at least one offered piece to permit mate in one changes the potential disagreement recovery from 11 true/2 false to 10 true/2 false: Ng6+ is lost and neither false case is removed. Requiring all acceptances of all offered pieces yields the same result here.

Neither Qb2 nor Qf6 can be removed by coherent new-threat attribution: the moved queen relinquishes its defense of Bc8/Nd5, changing raw exchange loss from zero to positive, while newly creating the mating reply. Neither previous-own-move position has a nonpawn capture followed by mate in one. They are genuine counterexamples to the proposed mate rescue's perfect specificity.

For the qualifying current acceptance branches only, enumerating every legal mate reply would inspect at most 151 child positions per target (99th percentile 97; total 18,150 across 618), counting the acceptance child plus every legal reply. This excludes same-square exchange-search nodes, prior-history probes and any extra legality-generation overhead. Thus it supports feasibility of a small mate-reply enumeration but is not a bound on total classifier work.
