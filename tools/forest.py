# SPDX-License-Identifier: AGPL-3.0-only
"""Saved-feature inference for the frozen Mute Chess research forests.

The tree traversal and gates follow the archived native forest and grouped
learner experiment. This module does not extract features or analyze a FEN.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / 'studies/brilliant-training-2026-11-03/data/training.json'
STANDARD = ROOT / 'studies/brilliant-standard-learners-2026-11-04'
DIAGNOSIS = ROOT / 'studies/brilliant-forest-miss-diagnosis-2026-11-04'
ORIGINAL = ROOT / 'studies/brilliant-moves/reference/v5/native/noSweatBrilliantForestModel.json'


def read(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def window_score(model, features):
    vector = []
    for name in model['features']:
        missing = name.endswith('__missing')
        source = name[:-9] if missing else name
        if source not in features:
            raise ValueError('Missing predictor: ' + source)
        value = features[source]
        if value is not None and (not isinstance(value, (int, float, bool)) or not math.isfinite(value)):
            raise ValueError('Predictor must be finite numeric, boolean, or null: ' + source)
        vector.append(float(value is None) if missing else value)
    if not model['trees']:
        raise ValueError('Empty forest')
    total = 0.0
    for tree in model['trees']:
        node = tree
        while node['kind'] == 'split':
            value = vector[node['feature_index']]
            node = node['left' if value is None or value <= node['threshold'] else 'right']
        if node['kind'] != 'leaf' or not 0 <= node['raw_p'] <= 1:
            raise ValueError('Invalid leaf')
        total += node['raw_p'] / len(model['trees'])
    return total


def infer(model, case, threshold):
    """Use only features and recorded gates; labels/IDs do not affect inference."""
    scores = {w: window_score(model, case['windows'][w]['features']) for w in ('current', 'previous')}
    eligible = all(case['windows'][w]['eligible'] is True for w in scores)
    confidence = case.get('confidence_sufficient') is True
    physical_known = not any(case['windows'][w]['features']['physical_unknown'] for w in scores)
    return {
        'window_scores': scores,
        'minimum_window_score': min(scores.values()),
        'threshold': threshold,
        'gates': {'both_windows_eligible': eligible, 'confidence_sufficient': confidence,
                  'physical_evidence_known': physical_known},
        'award': eligible and confidence and physical_known and min(scores.values()) >= threshold,
    }
