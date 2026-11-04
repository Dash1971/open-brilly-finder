# Optional mechanism challenge panel

This is a prelabel challenge panel for the already-frozen v4 candidate. It is separate from the main benchmark and does not estimate how frequently these mechanisms occur in ordinary play. No current Game Review labels, browser evidence, engine evaluations, ratings, or game outcomes were used to choose its cases. Every subsequently observed label must be retained; there are no Brilliant/non-Brilliant quotas or replacements based on a label or classifier result.

The bounded source supports **30 cases from 30 games**, rather than the optional maximum of40: five mating acceptances, five unchanged offers while in check, ten structural phase/material contexts, and ten cross-square material recoveries. The two five-case shortfalls remain unfilled. The source has only five eligible distinct games for each of those mechanisms; adding another case from a game would not supply another independent game.

## Eligible source and exclusions

The prepared corpus contains241 games:100 initially selected core games and141 ordered reserve games. The first eight reserves per account are protected for core replacements. Only the remaining101 reserve games were examined. Entire core games, all325 previously reviewed/development games, protected reserve games, and the extra games already opened by core collectors are excluded. The collectors coordinate before the identities are frozen.

Before and after positions must avoid all25,904 known canonical positions and all482 before/after positions of the core and reserve gallery candidates. Canonical identity is the first four fields of `python-chess`'s normalized FEN. Consequently, the challenge cases are other legal same-player moves in the eligible game histories; a historical gallery nomination alone is not treated as a fresh label. Full PGNs are replayed legally, and SAN, UCI, one-based ply, before/after FEN, prior own-move history, and PGN SHA256 are checked against the prepared database. No observations tables are read.

## Feature definitions

Material values match the frozen source: pawn90, knight/bishop300, rook500, queen1000, king0. Physical material totals do not use a checkmate sentinel. A qualifying raw piece offer is a legal, same-square exchange gain strictly greater than the material already credited on the original move plus100. Pawns and kings cannot be the offered victim; legal moves, en passant, and promotion gains are respected. A complete bounded copy of the source's local exchange calculation establishes the descriptor. It is a board feature, not an engine quality assessment.

* **Mating acceptance:** the exact frozen `hasMatingAcceptance` must return true. An additional bounded witness must establish a qualifying legal acceptance followed by a literal legal mate-in-one reply. Both moves are saved in UCI and ASCII SAN. Acceptance need not be forced; no longer mate is inferred.
* **Unchanged offer while in check:** the exact frozen `continuedOfferWhileInCheck` must return true. The mover begins in check, and every qualifying current offer is the same unmoved piece, on the same square, with equal legal exchange vulnerability after the preceding own move. The saved prior FEN is after that own move, two plies before the target. Current/prior exchange gains and piece identities are recorded.
* **Structural phase/material context:** a qualifying raw offer must exist, and the exact frozen `convertedMaterialOrEndgame` must hold: total phase is at most8 with knight/bishop1, rook2, queen4, or the mover already leads by at least300 physical material. The phase, material, and boundary result are saved. This does **not** establish a winning evaluation or safe winning alternative; that question requires later fixed-budget engine evidence. Cases stay in the panel even if that evidence does not confirm the intended context.
* **Cross-square material recovery:** after a qualifying acceptance, there must be a legal capture-only continuation in which the mover first restores at least the physical material balance from before the original move by capturing on another square. All moves and material totals are saved. If recovery first completes on the acceptance square, an unrelated later capture cannot qualify it. This is a conditional, potentially cooperative witness, not a forced or optimal continuation. Quiet responses and quiet compensation are outside this descriptor.

Each individual proof has a512-position cap. An exhausted proof supplies no usable witness and is unknown, not a negative label. The exact frozen helper and the separately saved witness may each perform a bounded proof; there is no unbounded game-tree search or Stockfish invocation. All4,432 examined raw-offer proofs completed within the cap.

## Deterministic choice and reproduction

The fixed seed is `mute-improvement-mechanism-v1`. Candidate priority is SHA256 of the UTF-8 string `seed:category:lowercaseAccount:gameID:oneBasedPly`. For each category/game, the lowest-hash eligible move is its representative. Ten slots per category are visited in round-robin category order from PLAN.json. A deterministic augmenting-path matching assigns distinct games to slots, using representative hash order. It maximizes filled slots within this bounded source without permitting multiple selected cases from one game. No account quotas were added to the optional panel.

`selection-input.json` preserves the legally derived, unlabeled board input and source/exclusion inventory. `select-panel.mts` imports the exact frozen source and writes the proposed selection; `validate-panel.py` independently replays the full PGNs and every saved conditional line with python-chess. It writes `panel-validated.json`. `panel-queue.json` and `PANEL-FREEZE.json` are created only after collector coordination and are the collection authority. Selection input, scripts, candidate source, and queue hashes are recorded in the freeze.

Run from the workspace root with the already-installed dependencies:

```sh
/Users/da/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --max-old-space-size=256 --import /private/tmp/mute-brilliants-native/node_modules/tsx/dist/loader.mjs research/brilliants-improvement-2026-11-03/validation/mechanism/select-panel.mts
python3 research/brilliants-improvement-2026-11-03/validation/mechanism/validate-panel.py
```

These scripts are study-specific and do not modify the database, classifier, application, or collection infrastructure. Rerunning proposal generation does not revise the frozen collection queue.
