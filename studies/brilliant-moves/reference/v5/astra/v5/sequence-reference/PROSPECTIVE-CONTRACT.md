# Prospective comparator contract and forest configuration audit

This prepares frozen research comparators only. No native port, fitting, threshold selection, new engine job or fresh-label evaluation was performed.

## S: corrected sequence comparator

Use corrected temporalProof.ts with baseline variantA.ts and its existing helpers/native core. The original manifest is retained; the effective executable manifest is source-freeze-castling-addendum.json, dated2026-11-03T09:48:31.491Z. Its temporal helper hash is16faa288afc2e18716cdc7135efa8275712cd3b12624e4f696f33f25f6b3fe29. Results are322TP19FP in848 development cases, unchanged by the castling correction.

For every target, supply the actual before/after positions and actual move, plus the continuous preceding six PGN plies. Compute earlier own-turn decisions with the same unsuppressed baseline A classifier and complete current/previous engine-iteration evidence used for target decisions. Never use prior observed labels, provisional badges or previously suppressed S results as origins. Do not substitute a prior after-position score for a completed prior move classification.

An award requires a confirmed current A Brilliant and no proved temporal veto. Current checks, captures, promotions and actual castling remain exempt from the temporal restriction. Continuous physical-piece identity, same raw liability, earlier capture-credit qualification, both specified forcing exceptions and the shared512-node limit are frozen. Unknown history or proof exhaustion cannot establish a veto. Missing prior classifier evidence cannot establish that prior origin. Report missing proof coverage separately; silently using incomplete origin windows would change how often S can suppress awards.

Fork novelty remains role-plus-destination, intentionally coarser than exact threat identity. Do not refine it based on fresh results. New legal mating acceptance must be tied to the same victim, currently profitable, absent from earlier legal moves, and followed by a legal literal mate. Existing acceptance/mate combinations alone do not qualify.

Freeze the engine configuration and evidence-completion rule before fresh labels. The established reference domain is SF18/300k, Threads1/Hash64, full PGN history and saved complete current/previous iterations. A uniform1.5m or different-engine run must be a separately declared configuration, with uniform matching prior windows and its own coverage accounting. Never mix300k origin evidence into a purported uniform stronger S result. The existing16-position stronger-origin list is conditional on baseline candidates, not universal prospective coverage.

## Forest: fixed full-data model, not the out-of-fold models

The prospective predictor is the saved forest-full.json, with its64 trees and fixed threshold5/6. Out-of-fold223TP2FP describes the development procedure; the full-data fitted forest is a different fitted artifact and has no prospective performance estimate yet. Its training247TP0FP result is not validation.

Read-only configuration checks passed: saved model protocol hash matches PROTOCOL.json; ordered feature names match the75 base predictors followed by their75 missing indicators. Exact artifact hashes are in forest-config-audit.json. For each of two engine-iteration windows, route missing values left, numeric values left at <=the stored threshold, read unweighted raw positive fraction at each leaf, and average across64 trees. Both window means must be>=5/6 AND both original window eligibility guards AND original case confidence must pass. Scores are not calibrated probabilities. Preserve Boolean/None/zero distinctions and exact feature ordering.

The original guards require two roots, raw offer, quality and after-floor per window, plus case confidence. They are not replaced by the forest score. The terminal-position reuse of current after-evidence in the previous window must match the existing extractor. Do not automatically borrow S's sequence rule or change EC/material gates: that would be a different candidate.

The existing features.py is a fixed848 research assembler, reading precomputed context, physical and avoidability artifacts by key. It is not yet a self-contained prospective extractor. New-game extraction must reproduce the same numerical and missingness semantics from legal positions and engine evidence; it must not rely on old lookup rows. This is the concrete preparation gap, not a reason to port75 features to native now. Labels may be stored for evaluation but never supplied to feature calculation or model prediction.

Depth, available roots, played-root absence, prior-history availability, capped physical probes and their missing indicators are part of the learned representation. SF19 or variable analysis budgets can shift these inputs. The observed configuration audit establishes artifact consistency, not cross-engine robustness or runtime extraction parity. Declare the intended engine domain before evaluation; do not infer99% production badge precision from this balanced, gallery-derived sample.

## Interpretation and stopping condition

Evaluate the fixed forest, corrected S and EC on the same untouched game/position-separated evidence. Keep representative gameplay and deliberately selected hard-negative results distinguishable. Report TP/FN/FP/TN, recall, false-positive rate, badge precision and overall agreement with their sampling context. Current evidence supports a precision-first forest validation, not a promise of90% agreement. No post-label tuning belongs to that validation; any changed model becomes a later development candidate.
