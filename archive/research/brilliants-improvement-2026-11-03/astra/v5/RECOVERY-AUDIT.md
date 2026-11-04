# Cross-square recovery audit

All1048 are now development. No new engine search, native edits or new classifier experiment was performed. The companion recovery-risk-pool.json contains every S-awarded case matching capture + positive immediate credit + unmoved offered piece:32 true awards and5 false awards. This is a candidate inspection pool, not a proposed sufficient veto.

## Two requested errors

171488501692:36 hxg6 captures a pawn (90) and leaves Nc4 offered. Bxc4 Qc5+ Kh1 Qxc4 returns the bishop value after a quiet checking relocation, restoring the pre-move material balance plus90. The actual PGN continued Bh6, so the supplied acceptance line is conditional, not the played game. A capture-only probe omits Qc5+.

173517772799:30 hxg5 captures a knight (300), leaving Ra8 offered. Bxa8 Ba6 clears the f8–a8 rook ray while attacking Rf1. White can legally move Rf1 (Rfe1/Rfd1/Rfc1/Rfb1), so Bxf1 is not forced in isolation: saving that rook permits Rxa8; saving Ba8 permits Bxf1 and a bishop recapture. The played game used Bg2 Bxf1 Bxf1; Rxf1 is another recapture, not the actual PGN. The relevant proof is the double threat and safe final material under every legal response. A capture-only probe omits quiet, nonchecking Ba6.

Neither example supports excluding pawn captures or all temporary material investments. A narrow candidate must prove the concrete recovery, not infer it from move type or the subsequently played continuation.

## Why the previous physical gate failed

Across all1048 S awards, simply vetoing existing three-ply debt<=100 removes120 true awards and5 false awards. Restricting to the32true/5false inspection pool still removes10 true awards and0 false awards. Both requested errors have positive debt in that probe (210 and200), precisely because their quiet recovery moves are absent. All five current-test extra awards also differ: Nb5 is quiet with debt410; Qd6 quiet with debt−290; Rxd7+ is a moved-offered-piece checking capture with debt200. One recovery rule need not explain every error.

The10 true awards lost by the restricted old debt gate are:

- 185868851860:32 Nxe3
- 186434170706:26 dxc4
- 174156500008:51 Rxd7
- 174184365826:77 Kxf3
- 174246361974:33 fxg6
- 174429457866:50 Nxe2
- 173487325950:52 Bxe3
- 174427252006:66 bxc3
- 174521237632:40 Rxd5
- 184980636738:94 Nxc3

Illustrative stored lines: Nxe3 offers the queen, then Nxc7 Nxc4+ Kh1 Nxd2 recovers elsewhere; dxc4 permits hxg6 Nxb2+ Kc3 Qxd1; fxg6 permits Nxe5 gxf7+ Nxf7 Rxf7. Genuine sacrifices therefore share immediate credit, an unmoved offered piece, cross-square recoup and even a net material gain. Several cached lines end in check, so raw endpoint arithmetic is not proof that the gain survives.

## Recommended single bounded experiment

Investigate a decision-scoped *banked capture with forced safe recovery* veto within that inspection pool, not a general debt requirement. For every qualifying profitable acceptance, require an explicitly legal quiet checking relocation or quiet double-threat relocation after which every legal opponent reply permits safe recovery to at least the pre-move material balance. The reply capture may occur on a different square; stabilize its exchange and resolve check rather than stop on a favorable raw leaf. Include the move's immediate capture/promotion credit exactly once. If any acceptance leaves unproved investment, any reply refutes recovery, a terminal mate invalidates the material interpretation, or the bounded proof is unknown, do not veto. Genuine direct mating continuations should remain explicit exceptions.

This is a narrow hypothesis explaining the omitted mechanisms, not evidence of zero collateral loss. Requiring quiet recovery distinguishes the observed error mechanism from the three checking-capture examples above, but genuine quiet deflection combinations can also satisfy it. Do not add exceptions keyed to those examples, piece names, role thresholds or observed labels. Audit all S positives that the exact probe removes, particularly the32-case structural pool, and report the entire loss list. No claim about fresh accuracy survives selecting this rule on these1048 cases.
