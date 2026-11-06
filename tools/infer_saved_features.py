#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Infer a forest award from already-extracted feature windows; no engine needed."""
import argparse
import json
from pathlib import Path
from forest import ORIGINAL, STANDARD, TRAINING, infer, read, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--case-key', help='Read one case from the included 3,724-case dataset')
    source.add_argument('--features-json', type=Path, help='JSON case with windows and recorded gates')
    parser.add_argument('--model', choices=['original848', 'experimental3724', 'selective20261106'], default='original848')
    args = parser.parse_args()
    if args.features_json:
        case = read(args.features_json)
    else:
        dataset = Path(__file__).resolve().parents[1] / 'studies/brilliant-selective-2026-11-06/data/feature-cases.json.gz' if args.model == 'selective20261106' else TRAINING
        case = next((c for c in read(dataset)['cases'] if c['key'] == args.case_key), None)
        if case is None:
            parser.error('Case key is not in the included dataset')
    if args.model == 'original848':
        path, threshold = ORIGINAL, 5 / 6
        description = 'Original 848-case full-fit forest; saved-feature inference, not a held-out estimate'
    elif args.model == 'selective20261106':
        path = Path(__file__).resolve().parents[1] / 'studies/brilliant-selective-2026-11-06/reference/native/ui/analyse/src/noSweatBrilliantForestModel.json'
        assert sha256(path) == '1a7150fbe52f440922d94d3ae2af337383d63f370b52d0379aeee22d581d056c'
        threshold = 0.83
        description = 'Frozen updated Mute Selective full-fit model; saved-feature inference, not fresh-game validation'
    else:
        path = STANDARD / 'selected-model.json'
        freeze = read(STANDARD / 'MODEL-FREEZE.json')
        assert freeze['selected']['kind'] == 'custom'
        assert sha256(path) == freeze['model_sha256']
        threshold = freeze['selected']['threshold']
        description = 'Experimental 3,724-case full-fit model; not a promoted release or held-out estimate'
    result = infer(read(path), case, threshold)
    result.update(model=args.model, model_sha256=sha256(path), scope=description,
                  case_key=case.get('key'), caveat='Requires precomputed features and eligibility/confidence gates. This is not a FEN-to-Brilliant classifier.')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
