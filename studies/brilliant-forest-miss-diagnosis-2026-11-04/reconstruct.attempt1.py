"""One-shot forensic reconstruction of the five already evaluated outer forests.
No candidate selection, threshold selection, inner folds, or full-data fit.
"""
import os
for setting in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[setting] = '1'
import ast
import hashlib
import json
import math
import resource
import signal
import sys
import time
from pathlib import Path
sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
ORIGINAL = WORK / 'research/brilliant-standard-learners-2026-11-04'
START = time.monotonic()
FITS = 0
TREES = 0

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value * 1024

def guard():
    if time.monotonic() - START > 180 or rss() > 512 * 1024**2:
        raise RuntimeError('Reconstruction cap: 180 seconds / 512 MiB; no automatic retry')

def timeout_handler(*_):
    raise RuntimeError('Reconstruction wall deadline reached; no automatic retry')

def write(name, data):
    (HERE / name).write_text(json.dumps(data, allow_nan=False, separators=(',', ':')) + '\n')

def fold_map(groups, n, salt):
    ordered = sorted(set(groups), key=lambda g: (hashlib.sha256((salt + ':' + str(g)).encode()).hexdigest(), str(g)))
    return {g: i % n for i, g in enumerate(ordered)}

def main():
    global FITS, TREES
    assert not (HERE / 'FOREST-TRACE.json').exists() and not (HERE / 'RECONSTRUCTION-STOPPED.json').exists()
    protocol = json.loads((HERE / 'RECONSTRUCTION-PROTOCOL.json').read_text())
    assert sha(Path(__file__)) == protocol['script_sha256']
    for item in protocol['inputs']:
        assert sha(WORK / item['path']) == item['sha256'], item['path']
    assert np.__version__ == protocol['numpy_version']
    source = WORK / protocol['kernel_path']
    tree_ast = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'Tree')
    assert hashlib.sha256(ast.dump(tree_ast, include_attributes=False).encode()).hexdigest() == protocol['tree_ast_sha256']
    exec(compile(ast.Module(body=[tree_ast], type_ignores=[]), str(source), 'exec'), globals())
    data = json.loads((WORK / protocol['training_path']).read_text())
    cases, base = data['cases'], data['predictors']
    saved = json.loads((ORIGINAL / 'PREDICTIONS.json').read_text())
    assert len(cases) == len(saved) == 3724 and len(base) == 75
    assert [c['key'] for c in cases] == [r['key'] for r in saved]
    names = base + [n + '__missing' for n in base]
    windows = [c['windows'][w] for c in cases for w in ['current', 'previous']]
    assert all(set(w['features']) == set(base) for w in windows)
    x = np.array([[float(w['features'][n]) if w['features'][n] is not None else np.nan for n in base]
                  + [float(w['features'][n] is None) for n in base] for w in windows])
    assert not np.isinf(x).any()
    eligible = np.array([w['eligible'] for w in windows], dtype=bool)
    gates = eligible.reshape(-1, 2).all(axis=1) & np.array([c['confidence_sufficient'] for c in cases])
    gates &= ~np.array([any(w['features']['physical_unknown'] for w in c['windows'].values()) for c in cases])
    truth = np.array([c['truth'] for c in cases], dtype=bool)
    ids = np.repeat(np.arange(len(cases)), 2)
    y = np.repeat(truth, 2)
    group_order = sorted({c['group'] for c in cases})
    gi = {g: i for i, g in enumerate(group_order)}
    cg = np.array([gi[c['group']] for c in cases])
    groups = np.repeat(cg, 2)
    counts = np.bincount(ids[eligible], minlength=len(cases))
    weights = 1 / np.maximum(1, counts[ids])
    w = weights * np.where(y, 1, 5)
    outer_map = fold_map(group_order, 5, 'mute-optimization-v1-outer')
    outer = np.array([outer_map[c['group']] for c in cases])
    assert [int(f) for f in outer] == [r['outer_fold'] for r in saved]
    assert gates.tolist() == [r['eligible'] for r in saved]
    assert int(truth.sum()) == 917 and len(group_order) == 972
    all_cases = np.arange(len(cases))
    scores = np.full((len(cases), 2), np.nan)
    forests = []
    for fold in range(5):
        guard()
        ti, vi = all_cases[outer != fold], all_cases[outer == fold]
        assert not set(cg[ti]) & set(cg[vi])
        train = np.flatnonzero(eligible & np.repeat(np.isin(all_cases, ti), 2))
        test = np.ravel(np.column_stack([2 * vi, 2 * vi + 1]))
        train_codes = np.unique(cg[ti])
        pred = np.zeros(len(test))
        trees = []
        assert FITS < 5
        for number in range(64):
            guard()
            assert TREES < 320
            rng = np.random.default_rng(np.random.SeedSequence([20261103, 20, fold, number]))
            draws = rng.choice(train_codes, size=len(train_codes), replace=True)
            mult = np.bincount(draws, minlength=len(group_order))
            ix = np.repeat(train, mult[groups[train]])
            assert set(groups[ix]) <= set(train_codes)
            trainer = Tree(x, y, ids, w, names, groups, rng)
            model = trainer.fit(ix)
            pred += trainer.predict(model, test) / 64
            trees.append(model)
            TREES += 1
        scores[vi] = pred.reshape(-1, 2)
        forests.append({'fold': fold, 'features': names, 'trees': trees})
        FITS += 1
        print(json.dumps({'stage': 'original_outer_reconstructed', 'fold': fold, 'trees': TREES,
                          'elapsed_seconds': round(time.monotonic()-START, 3)}), flush=True)
    minimum = scores.min(axis=1)
    errors = np.abs(minimum - np.array([r['outer_scores']['custom'] for r in saved]))
    parity = {'cases': len(cases), 'tolerance': 1e-12, 'max_absolute_error': float(errors.max()),
              'all_cases_pass': bool(np.all(errors <= 1e-12))}
    assert parity['all_cases_pass'], 'Saved outer minimum-score parity failed; stop without interpretation'
    awarded = gates & (minimum >= 5/6)
    assert awarded.tolist() == [r['outer_awards']['custom_fixed'] for r in saved]
    print(json.dumps({'stage': 'all_3724_parity_passed', **parity}), flush=True)

    # Only after complete parity: inspect the fixed held-out decision paths.
    rows = []
    identity_error = 0.0
    for i, case in enumerate(cases):
        guard()
        wr = {}
        for offset, window in enumerate(['current', 'previous']):
            row = 2*i + offset
            contributions = np.zeros(len(base))
            root_sum = 0.0
            negative_fraction = distinct_moves = distinct_groups = pure = high = depth_sum = 0.0
            for tree in forests[int(outer[i])]['trees']:
                node = tree
                root_sum += (node['support'] if node['kind'] == 'split' else node)['raw_p'] / 64
                depth = 0
                while node['kind'] == 'split':
                    parent_p = node['support']['raw_p']
                    value = x[row, node['feature_index']]
                    child = node['left' if np.isnan(value) or value <= node['threshold'] else 'right']
                    child_p = (child['support'] if child['kind'] == 'split' else child)['raw_p']
                    contributions[node['feature_index'] % len(base)] += (child_p-parent_p) / 64
                    node = child
                    depth += 1
                negative_fraction += (1-node['raw_p']) / 64
                distinct_moves += node['distinct_moves'] / 64
                distinct_groups += node['distinct_groups'] / 64
                pure += int(node['raw_negative_windows'] == 0) / 64
                high += int(node['raw_p'] >= .9) / 64
                depth_sum += depth / 64
            score = float(scores[i, offset])
            reconstructed = root_sum + float(contributions.sum())
            identity_error = max(identity_error, abs(score-reconstructed))
            assert abs(score-reconstructed) <= 1e-12
            wr[window] = {'score': score, 'root_baseline_mean_raw_p': root_sum,
                'root_plus_path_contributions': reconstructed,
                'path_contributions_by_base_feature': {n: float(v) for n,v in zip(base, contributions) if v != 0},
                'leaf_statistics': {'mean_raw_negative_fraction': negative_fraction,
                    'mean_distinct_moves': distinct_moves, 'mean_distinct_groups': distinct_groups,
                    'fraction_pure_positive_trees': pure, 'fraction_raw_p_at_least_0_9_trees': high,
                    'mean_depth': depth_sum}}
        limiting = 'current' if scores[i, 0] <= scores[i, 1] else 'previous'
        negative = sorted(((n,v) for n,v in wr[limiting]['path_contributions_by_base_feature'].items() if v < 0),
                          key=lambda pair: (pair[1], pair[0]))[:5]
        rows.append({'key': case['key'], 'group': case['group'], 'outer_fold': int(outer[i]),
            'truth': bool(truth[i]), 'eligible': bool(gates[i]), 'awarded': bool(awarded[i]),
            'minimum_score': float(minimum[i]), 'limiting_window': limiting,
            'limiting_window_top5_negative_path_contributions': [{'feature': n, 'contribution': v} for n,v in negative],
            'windows': wr})
    counts_out = {'cases': len(cases), 'truth_positive': int(truth.sum()), 'eligible': int(gates.sum()),
        'eligible_truth_positive': int((gates & truth).sum()),
        'eligible_score_misses': int((gates & truth & ~awarded).sum()),
        'truth_positive_awarded': int((truth & awarded).sum()),
        'truth_negative_awarded': int((~truth & awarded).sum()),
        'ineligible_truth_positive': int((~gates & truth).sum())}
    assert counts_out['eligible_score_misses'] == 429
    guard()
    write('OUTER-TREES.json', {'protocol_sha256': sha(HERE/'RECONSTRUCTION-PROTOCOL.json'),
          'features': names, 'forests': forests})
    write('FOREST-TRACE.json', {'protocol_sha256': sha(HERE/'RECONSTRUCTION-PROTOCOL.json'),
        'script_sha256': sha(Path(__file__)), 'parity': parity, 'counts': counts_out,
        'interpretation': 'Associations along fixed decision paths, not causal feature influence. Split Gini uses negative class cost 5; reported node/leaf raw_p uses unweighted bootstrap window proportions. Missing indicators are combined with their base feature. Root mean + grouped path contributions equals the window score. Limiting window is current on ties. Leaf counts are distinct in-bag moves/groups; raw fractions retain bootstrap multiplicity.',
        'maximum_root_plus_contribution_identity_error': identity_error,
        'fits': FITS, 'trees': TREES, 'elapsed_seconds': time.monotonic()-START,
        'peak_rss_bytes': rss(), 'rows': rows})
    guard()
    print(json.dumps({'stage': 'trace_complete', 'counts': counts_out, 'identity_max_error': identity_error,
                      'elapsed_seconds': time.monotonic()-START, 'peak_rss_bytes': rss()}), flush=True)

if __name__ == '__main__':
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(180)
    try:
        main()
    except Exception as error:
        write('RECONSTRUCTION-STOPPED.json', {'reason': str(error), 'fits': FITS, 'trees': TREES,
              'elapsed_seconds': time.monotonic()-START, 'peak_rss_bytes': rss(), 'no_retry': True})
        raise
    finally:
        signal.alarm(0)
