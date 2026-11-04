# Frozen collection adapters

These four scripts are study-specific additions. They do not modify any predictor, native source, earlier public data or engine budget. No fresh engine or panel-board discovery has run during preparation. They require root-frozen inputs and an explicit GO after current browser collection is complete. Main/panel labels must never enter the board-screening or origin-selection functions.

## Main core and supplement

Run `adapter/sf18-collect.py core DATABASE PRIMARY_QUEUE OUTPUT`. PRIMARY_QUEUE is the final200 root-verified unique move rows (array, or targets array). Only game_id/ply and optional identity fields select/check positions; observed labels are not used. The collector reads full PGNs from the frozen readonly SQLite games table. It searches chronological p−2,p−1,p windows with the original collector's byte-identical packed()/search() functions:300k nodes,Threads1,Hash64,MultiPV min(2,legal roots), clean hash/game session per game, full PGN history. It omits the old redundant Python material diagnostic because native paired replay computes the fixed EC material predicate from the FEN itself; no engine behavior changes.

After the entire core completes, run `adapter/prepare-supplement.mts CORE DATABASE SUPPLEMENT_QUEUE`. It selects all three possible earlier own-turn windows for confirmed quiet baseA candidates, excluding checks, captures, promotions and actual castling as the frozen temporal proof does. It uses no observed labels or previous displayed badges. This deliberately completes all potentially relevant origins rather than selecting only known suppressions. Freeze that output before searches. Run `sf18-collect.py supplement DATABASE SUPPLEMENT_QUEUE OUTPUT` as a separate process/clean stream. Any overlapping core snapshot is rejected. The paired replay receives both banks and reports missing origin windows explicitly.

Maximum unique snapshots:600core and1200supplement. Each stream is fixed to600seconds of recorded engine work and600seconds wall time; no automatic retries, partial-bank substitution or budget increases. Outputs are checkpointed atomically and marked incomplete on failure/cap. If either cap prevents complete coverage, stop and disclose it rather than quietly weakening the history rule.

## Guard-panel discovery and activation freeze

The pool input is exactly500 distinct games in pilot's frozen hash order after excluding all main/reserve games and previously examined games/positions. Each candidate's before AND after canonical first-four-FEN fields must also be absent from the approved46,194-position exclusion artifact, whose hash is bound by the frozen pool. Shared opening positions do not exclude an entire game. Each game row supplies game_id,account,ordering_hash,pgn,pgn_sha256 and source_link. PGN metadata/NAGs/current labels are not predictors. The board parser uses legal mainline moves only.

`adapter/discover-panel.mts POOL CANDIDATE_QUEUE` scans that fixed order and chronological plies, retaining at most300 candidates. It calls the unchanged native existingOfferRecovery proof using explicit placeholder roots solely to enumerate board-qualified acceptances; no engine score, baseline classifier or observed label is read. These are NOT actual v7 activations. Unknown proof results are retained as diagnostic counts and cannot pass the prefilter. No pool expansion or post-label replacement is permitted.

Run `sf18-collect.py panel POOL CANDIDATE_QUEUE OUTPUT` after root GO: at most900core snapshots, same SF18 settings,600seconds recorded/wall cap. Every candidate is a nonchecking capture and therefore exempt from the temporal continuation veto; exact v6/v7 decisions need their core three-position windows but no earlier-origin bank.

`adapter/freeze-panel-activations.mts PANEL_CORE CANDIDATE_QUEUE ACTIVATION_FREEZE` requires complete matching evidence. It scores both frozen policies, preserves all candidate outcomes, and freezes the first30 distinct-game actual v6-Brilliant/v7-recovery-veto activations in original candidate order. CURRENT CHESS.COM LABELS FOR THIS PANEL ARE COLLECTED ONLY AFTER THAT FILE IS FROZEN. If fewer activate, report the actual count. The panel never enlarges the main200 denominator and cannot justify retuning.

## Root authorization binding

SF18-GO.json contains browsers_closed:true and streams.core/supplement/panel objects with authorized:true, source_sha256,queue_sha256,collector_sha256. Only the stream being run must be bound. Discovery also requires panel_discovery:true,panel_pool_sha256,panel_discovery_sha256. Creating a GO file is owned by root; preparation alone grants no run permission. Collection hashes and exact source/search parity checks are recorded in COLLECTION-FREEZE.json.

No multiworker orchestration, release changes, installations or engine implementation were added. The earlier SOURCE/ADAPTER freezes remain unchanged. Check source and adapter manifests before beginning fresh work; new files are additionally covered by COLLECTION-FREEZE.json. Node commands use the previously frozen TSX configuration/runtime. Python uses the already installed python-chess dependency directory.
