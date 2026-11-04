# Latest: memory mitigation checkpoint

Chrome access was restored successfully. Collection is now held for the user's memory concern, not a browser-authentication failure. The newly opened research tab was closed; no collectors or engine jobs are active. All107 validated new moves remain saved. Read MEMORY-HOLD.json first, then the detailed checkpoint below.

# Private collection resume checkpoint

**PRIVATE WORKING NOTE — do not publish or copy into the reader report.**

Saved offline on 2026-11-03 at 04:58:42UTC after the Chrome extension/provider connection interrupted. All recorded evidence has been imported, exported and validated. All UI collectors are stopped pending the owner's browser reconnect. No additional-study Stockfish analysis or new policy evaluation has run.

## Exact saved totals

| Account | Primary Brilliant | Primary non-Brilliant | Brilliant remaining | Non-Brilliant remaining |
| --- | ---: | ---: | ---: | ---: |
| KNVB |20 |19 |10 |11 |
| hansen |30 |30 |0 |0 |
| nelsi |2 |2 |28 |28 |
| GothamChess |2 |2 |28 |28 |
| Hikaru |0 |0 |30 |30 |
| **Total** |**54** |**53** |**96** |**97** |

The new study contains **107 unique primary game/move pairs from 50 games**. Its target is 300, not yet completed. All107 have captured-board corroboration. There are no pending PGNs, source-game/ply/SAN/board mismatches, conflicting active fresh binary labels, selected prior-FEN matches, repeated sampled positions or cross-partition position overlaps at this checkpoint.

Evidence files contain110 fresh capture rows: KNVB40, Hansen62, Nelsi4 and Gotham4. Three rows are secondary rather than quota entries. Hansen's historical Rook target171728719428:106 currently displayed Excellent; its systematic reserve171575524144:59 Bxe6 displayed Brilliant. The failed historical label remains secondary, and the reserve brings Hansen to 30/30. Negative candidates that displayed Brilliant also remain secondary. No negative is inferred from gallery absence.

Coach quality is separate from label identity:103/107 primary captures contain some text,95 explicitly record verified-visible-complete text, eight contain partial/unverified text, and four have no captured coach text. Raw text and status fields remain unchanged. Some punctuated text remains unverified. The labels/SAN/board evidence is still valid.

The corpus contains 307 cached public games and 261 active observation rows, with 263 stored raw versions and two metadata enrichments. These are collection/cache counts, not primary sample denominators. The original 318-move study is immutable. Its153 primary games and all other prior explicitly reviewed/development games are excluded here; the frozen exclusion list contains 179 game IDs, and the normalized prior-position set contains 724 before/after FENs.

## Root's interrupted KNVB pair: finish its negative first

The root CUA timeout saved the positive before its kernel reset:

- Game **185704945098**, ply **23**, SAN **Qh5**, Knight Sacrifice gallery category.
- Current observed label **Brilliant**, selected primary positive; captured at **04:53:54.898UTC**.
- Review URL: `https://www.chess.com/analysis/game/live/185704945098/review?move=22`.
- There is **no saved primary negative for this pair**. Do not repeat or skip the positive merely because its key is already used.

`root-collector-resume.json` contains the saved target, used keys and the next eight unobserved control candidates in the frozen priority order. The first candidate is **Ne5 at one-based ply17**, game185704945098, URL`https://www.chess.com/analysis/game/live/185704945098/review?move=16`. Its local descriptor is quiet attacked/defended piece, not a raw-v2 offer. **Its Chess.com classification is UNKNOWN until selected visibly.** If it displays Brilliant, preserve it secondary and try the next candidate. The next candidates are ply35 Ng5 and ply63 Rg6. Use the JSON/PGN identities as authority.

After saving an explicit non-Brilliant control, KNVB will be20/20. Resume unused KNVB targets from the disk queue, checking complete pairs rather than only a set of visited positives. Cap the account at 30/30 unless an explicitly recorded PLAN fallback amendment changes its allocation.

## Browser recovery and helper reconstruction

The last Chrome inventory reported browser ID **1**, profileD. Root's owned research tab was reported with suffix **129**; collector2's last full tab ID was **245638143**. Both were still open when API access failed; neither was closed through the broken provider. Treat those IDs, handles and all persistent browser bindings as **stale until reconnect and fresh inventory**. Do not close user tabs or restart applications.

Root attempted a fresh normal binding to Chrome ID1 and a rebind of an existing tab; both failed with the debugger-unattached/connection-interrupted error. The owner was asked to reconnect the Chrome extension. Do not keep retrying or create replacement research tabs while waiting. Once the owner confirms readiness, read the fresh runtime/browser documentation, inventory Chrome again, then claim the existing owned tab by its newly verified identity. Re-check the actual URL and DOM.

**Root's CUA JavaScript globals were lost in the kernel reset.** Reconstruct from disk: queue, evidence, used keys, complete-pair progress, filesystem handle and helper references. Pass**every **helper dependency explicitly: tab, target, role, store, filesystem, take/helper reference. Use distinct persistent binding prefixes for each collector. Do not depend on closed-over globals, nearest/stale tab handles or a previous account's store.

`ui-take-visible.js` and `ui-pair-candidates.js` retain the helper source. Browser execution requires permitted**literal function definitions** in the CUA runtime; file-text`eval`was disallowed. Do not attempt to execute a loaded file string as browser code. Initialize `galleryKeys` from **all**entries in the new account's `*-candidate-pool.json`, not merely its selected30. Those are historical candidates, not assumed current labels; avoid using their moves as planned negative controls.

Some games do not expose the review panel just because the URL contains`/review`. Inspect the rendered page and use its observed**Game Review**button when it opens Analysis, or the observed**Start Review**button when the summary requires starting ordinary review. Wait for visible feedback, then verify game ID, one-based ply, SAN, explicit label and board classes. Do not infer a result from a coach sentence, an empty panel or a timeout. A source query`move=N`must match ply`N+1`.

For coach completeness, read visible`innerText`only. Empty hidden placeholder elements may persist. The working helper counts pending hidden characters without reading/retaining their hidden future strings; zero pending characters plus stable visible text and ending punctuation can support`coach_completeness: verified_visible_complete`. Otherwise save partial/absent text honestly. Save every observed move before advancing.

## Collector ownership and resources

- **Root:** finish KNVB's pending negative, complete KNVB, then coordinate the remaining Nelsi/Hikaru work. Nelsi already has two complete saved pairs; do not recollect them.
- **research_repo/collector2:** Hansen is finished. Gotham has two complete pairs; next target is 185700879910:55 Qe7, URL`https://www.chess.com/analysis/game/live/185700879910/review?move=54`. That page supplied no recorded label before interruption. See`collector2-resume.json`.
- **pilot_method/collector3:** resource trial saved Nelsi2/2 and stopped. Its checkpoint is`nelsi-ui-checkpoint.json`; the last reported tab245638147 was to be closed on the resource handoff. Verify fresh inventory rather than assuming its current state. No one else should touch collector2's Gotham assignment.

All five target queues and hard-negative banks are prepared. No Node or engine worker remains running. The one approved raw-v2 descriptor job processed5361 cases, computed2050 missing predicates, took140ms of computation and peaked at approximately124.6MiB RSS with a256MiB Node heap cap; it exited. Hansen's reserve reused existing descriptors rather than starting another predicate job.

Root owns memory monitoring. The latest operating decision is **two collectors**after the third-collector trial caused excessive swap growth. A stable warning with decreasing swap allowed bounded collector2 trials as an explicit amendment; it does not grant an automatic third collector. Measure at batch boundaries and respect root's clearance. No engine runs during collection. Use one owned tab per active collector and the existing recovery procedure only.

## Data ownership, caps and checkpoints

The corpus agent owns`corpus.sqlite3`writes; root/collectors write their own evidence JSON only. Import saved review batches, then export/validate. `manifest.json`, `primary-moves.json`, `cohort-audit.json`, `observations-export.json`, PGN/provenance and partition-specific primary files are current at this checkpoint. `browser-block-checkpoint.json`contains the exact machine-readable audit.

Hard limits are**150 current Brilliants +150 explicit non-Brilliants,300 primary moves total**. Per-account30/class is initially allocated in`quota-allocations.json`. Preserve failed candidates secondary; use systematic unused gallery reserves with duplicate/prior-FEN checks. Nelsi and Hikaru currently have exactly 30 validated cached candidates each and no validated reserve; use PLAN's fixed-order fallback only after exhaustion is explicit, recording the allocation amendment rather than relaxing identity/exclusion rules. Fallback account order is KNVB,GothamChess,Hikaru,nelsi,hansen.

Whole-game partition assignment is SHA256(`mute-extra300:`+gameID) modulo3: zero is`reserved_validation`, the rest`discovery`. The rule author may receive only`primary-discovery-moves.json`until the new candidate source is frozen. `primary-reserved_validation-moves.json`is not for early scoring. Repeated positions and cross-partition overlap remain separately audited. No reserved-game performance metrics have been produced.

## Editorial and comparator requirements for the eventual public work

The final reader report should be **one unified visual, data-driven study**. If the new 300 finish, its combined core is 618 distinct game/move labels,309 Brilliant/309 non-Brilliant. **Do not claim618 or a completed new 300 now.** Actual completed combined evidence is 425 moves at this checkpoint; that is a private progress fact, not a public results narrative. Count actual unique primary games/moves and position dependence. Keep the older retrospective development versus new prospective/reserved validation distinction technically explicit in methods.

The reader story should lead with measured agreement with Chess.com and a fair En Croissant peer comparison, supported by figures and chess examples. Avoid collection chronology, count-increase storytelling, chat context, PR iteration numbers, memory/browser/tooling history, unmeasured99%claims, and unsupported claims to beat every open-source project. See`EDITORIAL.json`. No new combined public results until all 300 additional labels are validated and the frozen-policy replay is complete.

The latest official stable EC release was verified as **v0.15.1**, published2026-09-05, commit**4932c9231517f6fd75e5a97902b207c7dc82e61f**. Its`src/utils/score.ts`and`src-tauri/src/chess.rs`are byte-identical to the frozen6f2d2628 reference;`ec-latest-stable-check.json`records the Git blob proof. This does not assert identical application/evidence-collection behavior. The fair EC headline comparator is its **direct raw annotation**, not an undisclosed Mobile Maia/shared-window confidence filter. Publish shared-confirmation results separately. On the original 318, raw EC had45 true positives versus44 confirmed, with two false positives for both; verify raw metrics in the final replay. Mobile Maia remains unchanged.

Frozen baseline source pins remain v2`b3585f2`, v3`ac298a0`, EC`6f2d2628`with latest-stable equivalence proof. Saved source provenance and reproduction inputs belong in the technical appendix. Any newly tuned candidate must be frozen before reserved scoring. No application change or publication is authorized by this resume checkpoint.
