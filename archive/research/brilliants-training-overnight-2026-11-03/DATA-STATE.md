# Data preparation — active overnight

Deadline: 2026-11-03 23:55:39 UTC (Nov4 08:55:39JST). Root owns coordination and engine GO. Overnight_collector_a owns UI A wave2 onward; root completed initial A11. Pilot_corpus owns UI B. Research_repo owns offline queues. Root owns the SOLE dataset.sqlite3 worker PID52372/session38764 (restart of identical worker after subagent process ended). Root runs the frozen Astra training-only engine adapter under root GO, no fit/live model. No public/app/PR work authorized by this collection task.

## Active queues

- queue-A.json:11 root nelsi/KNVB games,8training/3assessment.
- queue-B.json:9 Pilot Gotham games,8training/1assessment, from the unvisited Gothic positive-topup reserves (first already reviewed game excluded).
- queue-A-wave2.json:10 root games,7training/3assessment.
- queue-B-wave2.json:33 Pilot games,26training/7assessment.
- queue-A-wave3.json: 6 KNVB games, 4 training and 2 assessment, 738 legal plies.
- queue-B-wave4.json: 60 Hansen games, 51 training and 9 assessment, 4,812 legal plies.
- queue-B-wave5.json: 22 Hansen games, 19 training and 3 assessment, 1,654 legal plies.
- Total 151 unique assigned games. Do not mutate active queues; new nominations go to immutable wave files.
- One cached nominee 184420545054 lacks a cached PGN and was not queued.
- Root gallery metadata plus our KNVB All Types 91-card pass yielded six A-wave3 games. Our Hansen 276-card pass yielded 82 B-wave4/5 games; 22 used one documented public March2026 PGN download (URL/hash/time in original-pgn receipt). The interrupted Nelsi98 pass has no new nominations beyond assigned/reviewed games.
- Resource pause at 15:46 UTC: ALL research_repo browser tabs closed. Root stopped engine batch02 on pressure2; do not retry. Browser collection resumes only root GO. Approved maximum before the pause was two review tabs plus one gallery tab, gallery ≤300cards, pressure1/free≥35%; record in PLAN resource_amendments.
All games include official cached full PGN and every legal ply/SAN/UCI/before-afterFEN. Gallery labels remain historical nominations, not current truth. Game split was assigned before fresh labels with sha256('mute-overnight-2026-11-03-v1:'+gameID) integer modulo5==0 assessment, otherwise training.680 prior reviewed games excluded. ASSESSMENT-POSITION-EXCLUSIONS.json includes46194oldknownpositions plus full positions of newly reviewed109games. It governs ALL waves, including wave1 flags: individual assessment positions overlapping known old positions are excluded without changing game split. New training/assessment matching positions/examples also excluded from assessment. Assessment may be collected/validated but no model outputs/accuracy/fitting.

## Import

Historical manual command (DO NOT RUN while root worker active):

```sh
python3 research/brilliants-training-overnight-2026-11-03/import-verified.py
```

Importer waits for completion flags; reads collector-a/{ID}-export.pgn +checks.json +complete.json, or collector-b/{ID}.review-export.pgn +{ID}.json metadata with both completion booleans true. Pilot parsed.json alone is NOT authoritative. Root checks have nested observed fields; Pilot metadata embeds UI_verifications with piece CSS classes. Both validated against official full PGN, exact selected node/SAN and full after-board pieces. Export mainline must match official PGN in full.

NAG map validated in method-check:1Great,2Mistake,3Brilliant,4Blunder,6Inaccuracy,9Miss. Unknown NAG types remain unmapped/unknown. Every Brilliant must have an individual visible board check. Other export labels use the validated export method and per-game checks; rendered_board_verified is individual evidence, never asserted for all exports. Two unannotated hard controls require explicit UI labels. Empty NAG is UNKNOWN, never negative. Coach not required.

Known presentation normalization: selected SAN may include SVG cls-N CSS rules before SAN; strip ONLY those recognized rules plus surrounding whitespace for exact comparison, retain raw checks/source bytes unchanged. First game h6Miss had this CSS prefix, otherwise exact node+board.

Dataset tables: games(fullofficialPGN/reviewPGN/sourcehashes/headers/split), positions(allplies+FENcanonical+nags), observations(explicitNAG vs visibleUI withraw/evidence), labels(dedup game/ply with actual mover/account/rating, brilliance, negativebucket, split/dataset_use/example_key), quarantines, metadata. Same-position binary conflicts and changed completed sources are quarantined. Raw errors versus hardordinary(Great/Best/Excellent/Good/Interesting) counted separately; Book/Forced otherexplicit. No model eligibility/usefulness has been computed by importer. COUNTS.json updated after import. Assessment remains sealed from model evaluation.

## First engine batch frozen

ENGINE-BATCH-01.json SHA b0062507ec3230981023ca0ccef3ef920ccf2d5a7ca8869e11dd19ce88c2a77a.
10completedTRAININGgames,77targets:9Brilliants59hardordinary9deterministicerrors(onegame none),183unique p−2/p−1/p positions. Embedded PGNs; live DB is not an input. Includes raw file/queue/plan/parser/exclusion hashes and byte-exact parser/selector snapshots at batch-sources/01. Assessment PGNs/labels NOT in batch. Selection: first10 completed training games, allBrilliants+allhardordinary+1hashed error/game, no model outputs used. Root/Astra notified; root GO controls engine. Do not overwrite batch or start batch2 without root authorization.

ENGINE-BATCH-02.json SHA d54f46fa5e3845be0d9b8709ca8841253cf21be3239871384016b362b4c5fdcc: next 17 completed training games, 133 targets (20 Brilliant, 97 hard ordinary, 16 deterministic errors), 336 windows. Selection script now excludes every earlier frozen batch game, snapshots prior hashes, refuses overwrites. Root started then resource-stopped this batch; partial artifacts remain. Do not launch or retry engines from this agent.

Batch01 completed: 183 snapshots, 77 targets, source unchanged. Future batch prep is allowed when enough unassigned completed training games exist, but execution always requires root GO. Do not automatically loop or fit models.

Counters live in COUNTS.json. At 15:46:56UTC:49 games (40training/9assessment), 1,115 labels,54Brilliants,269hardordinary,788errors,4other;358 individual board checks;0conflicts. Reserved170 eligible+8 known-position exclusions; no predictions. Raw labels are not claims of feature usefulness.


## Active bounded import worker — 2026-11-03 16:13 UTC

Root explicitly authorized one study-only background process. Original PID50477/session50369 ended with its subagent. Root restarted identical worker as PID52372/session38764 at16:27:31UTC. Command: `python3 research/brilliants-training-overnight-2026-11-03/import-worker.py`. It is now the SOLE SQLite writer: do not run the importer manually while active. Every30seconds it checks completed-file markers; changed completed games trigger the existing importer, then `prepare-engine-batch.py --batch <next> --min-games 20` freezes each available next training batch. It never runs an engine or fits a model. Invalid/incomplete JSON is skipped until a completed artifact is ready. Raw exports remain unchanged.

Checkpoint `IMPORT-WORKER-STATE.json`; append log `import-worker.log`; launch receipt `IMPORT-WORKER-LAUNCH.json`. Stop by creating `research/brilliants-training-overnight-2026-11-03/STOP_IMPORT`; wait until checkpoint status=stopped before any other database writer. Fixed stop:2026-11-03T23:57:39Z, a120-second saved-data verification grace after collection deadline. No auto-restart.

At launch:82completedgames,1,979labels,88Brilliants,449hardordinary,603individualboardchecks,0conflicts. Sealed assessment remains unscored. Current counts are always in COUNTS.json.
