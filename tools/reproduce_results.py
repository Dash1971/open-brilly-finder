#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Offline replay of recorded benchmark decisions, optionally recomputing OOF forest scores."""
import argparse
import hashlib
import json
from pathlib import Path
from forest import ROOT, TRAINING, STANDARD, DIAGNOSIS, infer, read, sha256

EXTERNAL = ROOT / 'studies/brilliant-external-comparison-2026-11-04'
EXPECTED = {'forest': (452, 6, 0), 'wintr_both': (287, 20, 5), 'knights_both': (590, 142, 56)}


def metric(truth, awards):
    counts = {'TP': 0, 'FP': 0, 'FN_known': 0, 'TN_known': 0, 'unresolved_positive': 0, 'unresolved_negative': 0}
    for y, a in zip(truth, awards):
        assert type(y) is bool and (a is None or type(a) is bool)
        name = ('unresolved_positive' if y else 'unresolved_negative') if a is None else ('TP' if y else 'FP') if a else ('FN_known' if y else 'TN_known')
        counts[name] += 1
    counts.update(confirmed_recall=counts['TP'] / sum(truth),
                  wrong_share_of_confirmed_awards=counts['FP'] / (counts['TP'] + counts['FP']))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-forest', action='store_true', help='Also recompute all 3,724 held-out custom forest scores using archived fold models')
    args = parser.parse_args()
    protocol = read(EXTERNAL / 'PROTOCOL.json')
    assert sha256(EXTERNAL / 'LABELS-AND-GROUPS.json') == protocol['metadata_sha256']
    verification = read(EXTERNAL / 'VERIFICATION.json')
    meta = read(EXTERNAL / 'LABELS-AND-GROUPS.json')
    assert len(meta) == len({m['key'] for m in meta}) == 3724
    truth = [m['truth'] for m in meta]
    assert sum(truth) == 917
    groups = sorted({m['group'] for m in meta})
    assert len(groups) == 972
    ordered = sorted(groups, key=lambda g: (hashlib.sha256(('mute-optimization-v1-outer:' + g).encode()).hexdigest(), g))
    folds = {g: i % 5 for i, g in enumerate(ordered)}
    assert all(folds[m['group']] == m['outer_fold'] for m in meta)
    baseline = [m['baseline_awards']['custom_retuned'] for m in meta]
    metrics = {'forest': metric(truth, baseline)}
    details = {}
    for name, file in [('wintr', 'WINTR-PREDICTIONS.jsonl'), ('knights', 'KNIGHTS-PREDICTIONS.jsonl')]:
        path = EXTERNAL / file
        assert sha256(path) == verification['outputs_sha256'][file]
        with path.open(encoding='utf-8') as stream:
            rows = [json.loads(line) for line in stream]
        by_key = {r['key']: r for r in rows}
        assert len(rows) == len(by_key) == 3724 and set(by_key) == {m['key'] for m in meta}
        for row in rows:
            values = [row['windows'][w]['award'] for w in ('current', 'previous')]
            expected = False if False in values else True if values == [True, True] else None
            assert row['award'] is expected
        awards = [by_key[m['key']]['award'] for m in meta]
        metrics[name + '_both'] = metric(truth, awards)
        details[name] = {
            'additional_correct': sum(y and a is True and not b for y, a, b in zip(truth, awards, baseline)),
            'additional_wrong': sum(not y and a is True and not b for y, a, b in zip(truth, awards, baseline)),
            'folds': [{**{'fold': f}, **metric([truth[i] for i, m in enumerate(meta) if m['outer_fold'] == f],
                                             [awards[i] for i, m in enumerate(meta) if m['outer_fold'] == f])} for f in range(5)],
        }
    for name, (tp, fp, unresolved) in EXPECTED.items():
        m = metrics[name]
        assert (m['TP'], m['FP'], m['unresolved_positive'] + m['unresolved_negative']) == (tp, fp, unresolved)
    assert (details['wintr']['additional_correct'], details['wintr']['additional_wrong']) == (88, 19)
    assert (details['knights']['additional_correct'], details['knights']['additional_wrong']) == (256, 141)
    result = {'status': 'pass', 'cases': 3724, 'groups': 972, 'positive': 917, 'negative': 2807,
              'metrics': metrics, 'additional_awards_and_folds': details,
              'scope': 'Offline verification of saved decisions. External classifiers and engines are not executed. Unknowns remain separate from false/true negatives.'}
    if args.verify_forest:
        training = read(TRAINING)
        assert sha256(TRAINING) == read(STANDARD / 'PROTOCOL.json')['input_sha256']
        assert len(training['predictors']) == 75
        cases = {c['key']: c for c in training['cases']}
        predictions = {p['key']: p for p in read(STANDARD / 'PREDICTIONS.json')}
        stored = read(DIAGNOSIS / 'OUTER-TREES.json')
        models = {f['fold']: f for f in stored['forests']}
        assert set(models) == set(range(5)) and all(len(m['trees']) == 64 and len(m['features']) == 150 for m in models.values())
        thresholds = {f['fold']: f['inner_selection']['points']['custom_retuned']['threshold'] for f in read(STANDARD / 'RESULTS.json')['outer_folds']}
        largest_difference = 0.0
        awards, fixed = [], []
        game_group, position_group = {}, {}
        for m in meta:
            c = cases[m['key']]
            assert c['truth'] == m['truth'] and c['group'] == m['group']
            for key in c.get('aliases', []) + [c['key']]:
                assert game_group.setdefault(key.rsplit(':', 1)[0], c['group']) == c['group']
            assert position_group.setdefault(' '.join(c['fen_before'].split()[:4]), c['group']) == c['group']
            fold = m['outer_fold']
            out = infer(models[fold], c, thresholds[fold])
            difference = abs(out['minimum_window_score'] - predictions[m['key']]['outer_scores']['custom'])
            largest_difference = max(largest_difference, difference)
            assert difference < 1e-12 and out['award'] == m['baseline_awards']['custom_retuned']
            awards.append(out['award'])
            fixed.append(all(out['gates'].values()) and out['minimum_window_score'] >= 5 / 6)
        custom, fixed_metrics = metric(truth, awards), metric(truth, fixed)
        assert (custom['TP'], custom['FP']) == (452, 6)
        assert (fixed_metrics['TP'], fixed_metrics['FP']) == (436, 6)
        result['recomputed_held_out_forest'] = {'max_score_difference': largest_difference, 'custom_retuned': custom, 'custom_fixed': fixed_metrics,
              'scope': 'Each case uses its archived held-out fold model and its inner-selected fold cutoff. No model is retrained.'}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
