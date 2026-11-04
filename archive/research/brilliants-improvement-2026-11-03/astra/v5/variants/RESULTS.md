# Two private full-window variants

Exactly the two requested variants were replayed through the complete `classify` current/prior-window logic on all 848 now-development cases. No engine searches or application changes occurred. Frozen v4's source hash remains `3b8344b048290caea028cc586486910b2bdbc534e221ccdf45481dac438f4301`. Its replay reproduces core TP320/FP25 and panel TP2/FP3.

| Dataset (all development for v5) | V4 TP / FP | A TP / FP | B TP / FP |
| --- | ---: | ---: | ---: |
| Old 618 | 246 / 15 | 246 / 15 | 242 / 13 |
| Historical recent 200 | 74 / 10 | 74 / 9 | 73 / 7 |
| Core 818 | 320 / 25 | 320 / 24 | 315 / 20 |
| Mechanism panel 30 | 2 / 3 | 2 / 3 | 2 / 3 |
| All 848 | 322 / 28 | 322 / 27 | 317 / 23 |

A removes exactly one false award and no true awards: 187780686673:36 Qh4 changes from Brilliant to Great. B removes five false awards and five true awards relative to v4. The historical 200-case agreement is 82% for v4, 82.5% for A, and 83% for B. These are newly fitted development results, not new validation. Neither reaches the requested future target of at least 90% agreement with at most two false awards per 100 hard negatives.

## Variant A: same-piece attribution only on the added mating fallback

The original v4 mating-acceptance proof must still pass. Then the additional attribution proof must tie all of these to the same capture:

- Its victim is an offered nonpawn/nonking piece.
- Its legal exchange gain exceeds the current move's capture/promotion credit plus 100.
- It permits an exact legal mate-in-one reply.
- The offered victim moved on the sampled move; **or**, for an unmoved victim with real aligned history, the previous-own-position maximum raw exchange loss on that square was strictly lower than this acceptance's net gain, or this specific capture was not legal then.

Missing history cannot corroborate an unmoved victim. Standard-UCI castling rook movement counts as a moved victim. EC-backed awards and explicit winning-mate corroboration remain unchanged. The original v4 proof remains a conjunct so the new rule is a restriction even in cases where different budget traversal could otherwise discover a witness that v4 missed.

This preserves h6's Brilliant: after the preceding Qf7+, Black was checked and could not take Bd3; h6 therefore leaves a newly legal offer. It rejects Qh4's extra award: Ra8 was already legally capturable after Ng4, with the same raw exchange cost. The old Qb2/Qf6 false awards remain because their offers are genuinely attributable under this definition.

## Variant B: A plus proven absence of a non-offering escape

A complete 512-node legal-root proof that every move leaves some raw qualifying offer supplies an additional veto. No engine quality is assumed for alternatives. Exhaustion means unknown and supplies no veto.

The veto is disabled by an original direct mate-after-acceptance proof, a direct legal stalemate after acceptance, or a searched winning mate in the current evaluation window. The winning-mate exception is evaluated again in the confirming window. This does not bypass A's separate attribution requirement for the added corroboration fallback.

Relative to A, B removes these four additional false awards:

- 178708072359:59 Qd2
- 184128361014:30 Qd7
- 178360672165:63 Nxh6+
- 184481267900:67 Qb5

It also loses these five observed Brilliants:

- 183801511095:81 Rxe4
- 186072205082:28 Nxd5
- 186566789489:55 Qxf5+
- 185357789637:42 Rcd8
- 180010872764:65 Rxe4

These are substantive counterexamples, not budget failures: the native helper completes its proof. In particular, Rxe4 can deliberately convert an existing knight fork into a sound exchange sacrifice, and Qxf5+ uses a forcing queen deflection/fork. An unavoidable existing liability does not mean the played sacrifice lacks intent or merit.

## Verification and implementation scope

`offerProofs.ts` contains board-only helpers; it has no game IDs, labels, ratings, or lookup branches. `variantA.ts` and `variantB.ts` are private copies of frozen v4 with the two requested changes. `replay.mts` uses saved evidence and native material evaluation; it does not launch an engine. `results.json` includes every result, paired change, source hash, and timing. Full three-policy replay plus diagnostics took about 8.4 seconds.

Focused helper checks verified Qh4 rejection, h6 preservation, unknown-history rejection for an unmoved victim, preservation of a moved Ng6 offer without history, and no spurious stalemate. Completed native/Python avoidability proofs agree on every case where both return a definite answer. Their budget-unknown cases differ because Python enumerated UCI-sorted roots while native Chessops follows its existing move order. This explains the additional Nxd5 true-award loss compared with the earlier Python overlay: the native implementation completes a no-escape proof there, while Python exhausted its cap. No unknown is treated as unavoidable.

A is a small interpretable correction with no observed development recall cost. B is a genuine precision/recall tradeoff, not a free improvement. Either would require a newly frozen candidate and fresh test before claiming generalization.
