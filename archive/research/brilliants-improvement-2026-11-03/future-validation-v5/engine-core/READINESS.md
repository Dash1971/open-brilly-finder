# Frozen fresh-test core: prepared code, not started

No engine, extraction, scoring or metrics runs are authorized until root supplies the completed **200-identity core freeze and explicit GO**. Existing partial primary files are not inputs to this preparation.

The collector is the completed uniform-evidence collector with only the fresh-test paths, 300,000-node budget, exact200 selection and ten-minute worker wall safeguard adapted. Four fixed whole-game hash partitions preserve clear-hash/new-UCI-game boundaries and chronological full-PGN positions. Each target requests only unique positions p−2, p−1 and p; at most600 total. No temporal-comparator lookback is searched in this bank.

After GO, bind the explicit root-provided artifacts:

```sh
python3 prepare.py --primary ROOT_PROVIDED_PRIMARY --db ROOT_PROVIDED_DB --root-core-freeze ROOT_PROVIDED_FREEZE
```

Then launch at most four copies of the existing collector, using worker0 through3:

```sh
python3 analysis.py core --db ROOT_PROVIDED_DB --subset partition-0.json --output analysis-worker-0.json
```

The worker checkpoints each completed snapshot atomically, records actual current and prior completed MultiPV iterations, full engine options and source/selection hashes. It refuses existing output and has no automatic retry. A safeguard stop is reported for root's decision, with no silently repeated searches or budget increase. A missing prior iteration stays missing; only explicit terminal snapshots use the documented terminal convention.

After all four workers exit, `python3 merge.py` checks exact frozen-key coverage, legal roots, PGN/FEN identities, source/engine/partition hashes and actual prior-window coverage, then writes `analysis-core.json`. No partial outcome metrics are computed. After root clears scoring, `python3 replay-forest.py` uses the unchanged fixed forest extractor/model on the ordered saved windows and writes features/predictions with no label join or metrics. The original EC direct annotation is reported separately from any shared two-window EC comparator in root's evaluation. No threshold or model fitting occurs.

The frozen S comparator's label-independent structural-origin supplement is a **separate** bank, at most1200 missing positions at the same300k budget, after core completion and explicit root handoff. It does not warm or replace core searches. Astra has been notified and is standing by; its existing label-independent coverage/replay implementation can be adapted for these paths without rewriting its frozen source or freeze manifests. All earlier development origins and stronger-budget windows remain ineligible substitutions.

The final frozen model SHA is `44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7`. Extraction uses the unchanged `astra/v5/fresh-extractor/extractor.py` functions `extract_batch` and `score_fixed_forest`. The effective S source SHA is `16faa288afc2e18716cdc7135efa8275712cd3b12624e4f696f33f25f6b3fe29`. Neither source is changed here.
