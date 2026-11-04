# V5 physical-investment and attribution research

## Conclusion

The new target is substantially harder than improving v4's recall. On the now-development 200-case set, v4 has 74 TP and 10 FP. Achieving at least 90% agreement with no more than two FP would require at least 82 TP with two FP: **at least eight additional Brilliants and eight fewer false awards**, without compensating new mistakes. The tested material and attribution mechanisms do not approach that combination. They should not be presented as a plausible near-complete solution merely because they explain individual errors.

All 818 core labels are development for these analyses. I did not use or wait for the mechanism panel's final labels. No engine searches, browser activity, application edits, or changes to frozen v4 occurred. The same-root-quality experiment belongs to pilot_corpus; its reported full-window result is no changed fresh awards and no removed fresh false awards. The work here addresses physical investment and attribution instead.

## Hypothesis 1: acceptance-conditioned three-ply physical investment

I implemented a fixed descriptive probe in `physical_probe.py` and saved all 818 results in `physical-818.json`.

For each existing qualifying legal piece capture, search three additional plies of captures and promotions. Search **all legal evasions when in check** and prohibit stand-pat in check; otherwise permit standing pat. Maximize/minimize physical material from the original mover's perspective. Compare the result with raw material before the sampled move, including its capture/promotion credit. Use the existing 90/300/300/500/1000 piece values. Keep checkmate as physical material, record terminal mates and checked horizon leaves separately, and never claim this is a full tactical proof. Per position cap: 10,000 nodes or 0.25 seconds. All 818 completed; 16,361 visited nodes total, maximum 138 per sampled position.

This addresses two real flaws of the old heuristic: comparing two optimized material positions can obscure the actual investment, and standing pat in check can invent a material outcome. It does **not** resolve the classifier boundary.

| Overlay on current v4 awards | Old 618 TP / FP retained | New 200 TP / FP retained |
| --- | ---: | ---: |
| Current v4 | 246 / 15 | 74 / 10 |
| Require >100 remaining physical debt after a qualifying acceptance | 176 / 11 | 50 / 7 |
| Same debt requirement, allowing winning-mate or exact mate-after-acceptance exceptions | 185 / 12 | 52 / 9 |

These are static-filter overlay counts, not a new classifier's full-window replay. Because the extra predicate is fixed by the board, the obvious recall damage already rules it out as a mandatory v5 gate. The candidate that preserves the existing mate exceptions removes **one fresh false award while discarding 22 fresh true awards**.

The 26 fresh misses also resist a simple physical rescue: 25 have a raw legal offer, but only seven have >100 three-ply debt. It is not simply a matter of recognizing more real material loss.

### Why fixed depth is not material proof

Some refund lines end with a check or a capture that can be answered beyond the horizon. Rh1's apparent refund is ...exd3 Rxh6+ gxh6 Qxe8+; Re1's is ...Qxh6 Nxf7+ Rxf7 Qxh6+. Neither terminal snapshot proves the material stays recovered. Exact final-square exchange stabilization or forced-evasion extension could improve the feature's chess validity, but cannot fix the large demonstrated overlap: genuine Brilliant combinations also recover their material, and several false awards genuinely spend it.

The probe also correctly does not invent quiet promotion preparation. After Rxh2 ...Kxh2, d7 and then d8=Q provide compensation, but the first pawn push is neither a capture nor an immediate promotion. Expanding to all quiet moves would become a tactical search with a substantially different cost and purpose. It would still not establish Chess.com's labeling preference.

## Hypothesis 2: new decision attribution, rather than a blanket novelty veto

A coherent narrower attribution hypothesis is: a quiet move that leaves all the same unmoved pieces offered at the same exchange loss, gains no immediate material, and adds no new mate-in-one-after-acceptance threat should not get a fresh sacrifice award.

This preserves the previously identified counterexamples Qc2 (moved offered queen), exd5 (immediate capture credit), Rg5 (moved offered rook), and Qxf8+ (moved offered queen). Nevertheless, testing the rest of the existing development data falsifies it again: it would remove seven old false awards but at least eight old true awards.

New counterexamples include:

- 183992910761:39 Ng4, Brilliant. The offered piece is unchanged; the moved knight attacks only pawns immediately. A higher-value-piece-attack test would miss the maneuver.
- 186038944608:35 f4, Brilliant. The move adds a pawn lever while maintaining the existing offer; there is no new literal mate witness.
- 186052437796:18 Nf6, Brilliant. Development while keeping an existing offer; immediate attacks target pawns.
- 186064974534:21 and 186065215864:21 Nb5, Brilliant. Same tactical position repeated in two games; the new knight jump does not move the offered piece.
- 185330168240:23 Nge2, Brilliant. The moved knight immediately attacks no enemy piece.
- 185357789637:42 Rcd8, Brilliant. A rook maneuver adds pressure while another piece stays offered.
- 185769255732:61 Qh6, Brilliant. A mating threat after acceptance already existed; simply demanding a new mate witness would reject it.

The correct notion is not merely “newly attacked piece,” “new exchange cost,” or “new immediate threat.” It is whether the move makes a meaningful new *compensating decision* in the position. That can involve quiet piece coordination. The existing three-FEN history plus static attack maps cannot reliably prove that distinction. Do not substitute a moved-piece, king-move, or pawn-move ban.

## Hypothesis 3: acceptance quality and compensation mechanism

The next high-leverage *measurement* is to distinguish a competitive acceptance from an outright tactical blunder, and determine whether the best defensive continuation actually pays a lasting investment or resolves an ordinary combination. This is a feature proposal, not a validated rule or a replacement threshold.

For every qualifying offered piece, collect:

1. The opponent's best reply score and the score of **that specific legal acceptance**, using matching root evidence in both complete iterations. Missing accepted roots remain unknown; the top two PVs cannot establish their exact value.
2. The legal best continuation after acceptance, with material trajectory and a stabilized end to any immediate exchange. Record mate, promotion compensation, cross-square recoup, and quiet strategic compensation separately.
3. An available non-offering alternative for the original mover, again with matched-root quality. This identifies a voluntary investment versus already committed or unavoidable loss; it is a feature, not an automatic veto, because an only-good-move sacrifice can still be Brilliant.

The current saved windows cover some of these branches but not enough to test this feature fairly. A bounded next investigation could use all ten fresh false awards plus ten matched genuine sacrifices, requesting only missing acceptance roots. This would test whether conditional tactical evidence adds a discriminating feature before paying for another large label collection. It should be specified in advance and performed by the parent within the agreed engine budget; I did not launch searches.

Important counterexamples already constrain the idea: current Great Qh4 (187780686673:36) has ...Bxa8 Qxh2#, while true Brilliant h6 (169827191694:65) has ...exd3 Qxg7#. “Acceptance loses to mate” cannot distinguish these. Conversely, Excellent Qb5 (184481267900:67) spends a real exchange after ...Nxa4 Qxa4, so “a competitive capture really loses material” will not alone suffice. These branch features must demonstrate a better separation; their plausibility is not evidence of 90% agreement.

## All ten fresh false awards: concrete mechanisms

| Case | Concrete finding | Implication |
| --- | --- | --- |
| 169827191694:67 Rh1 | Continues the attack after h6 ...Qxh6; ...exd3 permits a forcing cross-square recovery sequence | Inherited commitment and tactical recoup; finite horizon is unstable |
| 173084454389:59 Bc5 | ...Bxf6 permits both a material refund sequence and Rb8# | Mate exception preserves a CC Excellent false award |
| 174425603426:123 Rxh2 | Real rook investment, compensated by a passed pawn's quiet advance and promotion | Capture-only debt is incomplete; not a no-sacrifice case |
| 175936156661:48 gxf4 | Captures a knight while leaving Rd8; remaining modeled debt 110 | Real exchange investment after credit, not merely a pawn move |
| 178360672165:63 Nxh6+ | Real knight investment, debt 210; near-equal saved evaluation | Both soundness and real material cost can hold for CC Excellent |
| 184481267900:67 Qb5 | ...Nxa4 Qxa4 pays an exchange, debt 200 | Newly attacked rook plus genuine investment still not sufficient |
| 184514610842:73 Re1 | Existing Nh6 offer; cross-square refund can appear through ...Qxh6 Nxf7+ Rxf7 Qxh6+ | Board attribution and finite-horizon recoup both ambiguous |
| 185228493400:24 dxc4 | Different acceptances differ: Qxg5 permits full recoup, Bxg5 leaves modeled debt 120 | Any-versus-all acceptance aggregation changes the meaning of the feature |
| 186393990159:71 Qg6+ | Mating continuation, ...Kxf8 Qg8#, another mating move exists | Terminal physical material is not why the move is Best rather than Brilliant |
| 187780686673:36 Qh4 | Poisoned Ra8 offer, ...Bxa8 Qxh2#, observed Great | Genuine newly created tactical compensation is not a guarantee of Brilliant |

## Recommendation

Do not adopt the tested three-ply debt gate or broaden history suppression. Preserve the frozen v4 checkpoint. Investigate specific acceptance quality and stabilized compensation on a small matched set, then decide whether those features justify a distinct v5 hypothesis and a fresh test. A learned, auditable combination of meaningful features may eventually be more appropriate than adding hard exceptions, but no training infrastructure or new model was built here.

The existing evidence does not justify a promise of 90% agreement with two or fewer false awards per 100 hard negatives. Soundness, concrete offers, legal mating traps, physical sacrifice, and static novelty all show overlap between observed positive and negative labels. The next experiment must demonstrate new discriminatory information, rather than repackage those overlapping features.
