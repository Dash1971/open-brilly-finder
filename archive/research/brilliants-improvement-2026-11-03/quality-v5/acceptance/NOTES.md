# Conditional acceptance and escape evidence

The bounded run completed **20 matched development cases,21 qualifying acceptance branches, and18 restricted-before searches**:39 engine positions in8.948seconds of recorded search time. No case had more than three qualifying acceptances, so acceptance coverage is complete within the declared raw-exchange definition. Two cases have no raw-nonoffering legal root and therefore require no restricted-before search. The engine exited; there were no larger-budget search retries.

SF18 binary SHA256 is `ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374`. Every nonterminal search requested300,000nodes, one thread and64MB hash. Acceptance positions use MultiPV2; restricted-before searches use MultiPV1 over **all** legal raw-nonoffering roots. The global caps were80 positions and60seconds of recorded search. An initial database-path preflight error was corrected before an engine was opened; only one engine run generated evidence.

`branch-input.json` fixes the exact20 identities selected in Astra's `avoidability20.json`. Label fields are not consulted by branch preparation or passed to scoring. The frozen v4 raw-offer source is pinned by hash. Legal nonpawn acceptances qualify when capture value plus promotion gain minus the best legal same-square recapture gain exceeds the original move's material credit plus100. Acceptances are sorted by UCI; all21 fit the three-per-case cap. All before-position legal roots are independently checked with the exact frozen raw-offer predicate to establish the restricted search set.

Every branch starts from the full legal PGN move stack, not an isolated FEN. The original target and opponent acceptance are appended to that history. The result records the game/ply/FEN, PGN hash, starting FEN, full prefix UCI, engine options, source/input/script hashes, and conditional PVs of at most20plies. Hash is cleared once per case, and all branches within that case share its engine session; this ordering is recorded. Cached baseline before/after windows are retained separately from new searches. Restricted-root and cached unrestricted-root scores have different depth/search history and are not a same-root quality certificate.

## What the branches show

| Descriptor, any acceptance/selected PV | Ten false awards | Ten matched true Brilliants |
|---|---:|---:|
| Searched winning mate after acceptance |4|3|
| PV restores pre-original-move physical material |5|7|
| Queen captured on PV |3|4|
| Promotion on PV |1|1|
| No raw-nonoffering legal root exists |2|0|
| Restricted escape within existing5pp of saved before score |4|5|
| Restricted escape at existing600 boundary |1|0|

There is no clean mate/refund/escape-quality separator in this sample. The two cases with no raw-nonoffering legal roots are false awards **178360672165:63 Nxh6+** and **184481267900:67 Qb5**. That is an interesting structural descriptor in this matched sample, not a validated general veto. Only **169827191694:67 Rh1** has a restricted nonoffering escape above600; the existing prior-winning diagnostic already identifies it.

The requested pair remains a counterexample to a simple adequate-escape rule. False **187780686673:36 Qh4** permits `Bxa8 Qxh2#`; its best raw-nonoffering escape scores+8 against saved before+149, a12.645pp mapped difference. True **169827191694:65 h6** permits `exd3 Qxg7#`; its best escape scores+478 against saved before+775, a9.229pp difference. Neither escape is within the existing5pp quality boundary. Rejecting all offers that cannot be avoided without such a loss would reject both cases.

False **173084454389:59 Bc5** is another strong counterexample: accepting with `Bxf6` permits `Rb8#`, while the best raw-nonoffering escape scores−334 against saved before+755. Its Brilliant disagreement is not explained by an adequate escape to a nonoffering root. The paired true **172590636870:45 Bf6** also permits mate-in-one after acceptance; its best nonoffering escape is+597 against a saved winning mate. Literal mate after accepting an offer is insufficient to distinguish the labels.

Promotion compensation occurs in both classes: false **174425603426:123 Rxh2** has a PV containing `Kxh2 d7 ... d8=Q`, while true **184777814198:66 b3** has promotion later in the selected acceptance PV. These lines are useful examples of compensation missed by a capture-only material probe, but they are conditional engine continuations rather than forced legal witnesses.

`acceptance-results.json` preserves all current/previous exact completed snapshots and full physical PV event paths: mover-relative material, captures, queen captures, promotions, cross-square captures, and restoration flags. `acceptance-summary.json` joins the already-known labels **after** scoring to supply the table and per-case comparisons. A PV refund is not proof of recovery against every reply, and absence of a refund within20plies is unknown rather than proof that compensation does not exist. No classifier was fitted, source changed, or prospective performance claimed from these20 cases.
