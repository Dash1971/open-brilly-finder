#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Recount this study's published results, check the train/test split, and rescore the parity cases.
Python 3 standard library only."""
import csv, gzip, hashlib, json, math
from collections import Counter
from pathlib import Path
P = Path(__file__).resolve().parent
MODEL_SHA = '992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d'
SIX_ACCOUNT_CUTOFF = 0.8549045486915725      # 95.3% grouped cross-validation precision for the six-account model


def score(model, x):
    raw = model['baseline']
    for t in model['trees']:
        i = 0
        while not t['leaf'][i]:
            i = t['l'][i] if x[t['f'][i]] <= t['t'][i] else t['r'][i]
        raw += t['v'][i]
    return 1 / (1 + math.exp(-raw))


def count(rows, pred, review='chesscom_review_today'):
    a = [r for r in rows if pred(r)]
    false = [r for r in a if r['gallery_brilliant'] != '1']
    out = dict(awards=len(a), found=len(a) - len(false), false_vs_gallery=len(false))
    if rows and review in rows[0]:
        out['false_by_todays_review_too'] = sum(r[review] != 'brilliant' for r in false)
    return out


def main():
    blob = (P / 'model/mute-exchange-model.json').read_bytes()
    assert hashlib.sha256(blob).hexdigest() == MODEL_SHA, 'model file changed'
    model = json.loads(blob)
    out = {}

    # 1. the published split: training rows, held-out rows and excluded rows are disjoint by game
    cand = list(csv.DictReader(gzip.open(P / 'data/candidates.csv.gz', 'rt')))
    roles = Counter(r['role'] for r in cand)
    assert roles == {'training': 33037, 'held-out test': 1707, 'excluded: test game': 1397, 'excluded: position also in test': 402}, roles
    train = [r for r in cand if r['role'] == 'training']
    assert sum(r['training_label'] == '1' for r in train) == 7806
    test_games = {r['game_id'] for r in cand if r['role'] == 'held-out test'}
    assert len(test_games) == 337
    assert not test_games & {r['game_id'] for r in train}, 'a training row shares a game with the held-out test'
    assert all(r['game_id'] in test_games for r in cand if r['role'] == 'excluded: test game')
    test_keys = {(' '.join(r['fen_before'].split()[:4]), r['uci']) for r in cand if r['role'] == 'held-out test'}
    assert not test_keys & {(' '.join(r['fen_before'].split()[:4]), r['uci']) for r in train}, 'a training row repeats a held-out position and move'
    out['split'] = dict(roles, training_brilliants=7806, heldout_games=337)

    # 2. held-out games, native Stockfish 19 Fast evidence (and the research evidence alongside)
    rows = list(csv.DictReader(open(P / 'data/heldout-outcomes.csv')))
    assert {r['game_id'] for r in rows} <= test_games
    gallery = sum(r['gallery_brilliant'] == '1' for r in rows)
    assert gallery == 416
    out['heldout_337'] = dict(
        gallery_brilliants=gallery,
        mute_selective=count(rows, lambda r: r['mute_selective'] == '1'),
        mute_exchange_native=count(rows, lambda r: r['exchange_brilliant'] == '1'),
        mute_exchange_research_evidence=count(rows, lambda r: r['exchange_brilliant_research_evidence'] == '1'))
    assert out['heldout_337']['mute_selective'] == dict(awards=274, found=259, false_vs_gallery=15, false_by_todays_review_too=12)
    assert out['heldout_337']['mute_exchange_native'] == dict(awards=319, found=300, false_vs_gallery=19, false_by_todays_review_too=12)
    assert out['heldout_337']['mute_exchange_research_evidence'] == dict(awards=316, found=298, false_vs_gallery=18, false_by_todays_review_too=11)
    assert all((float(r['exchange_score'] or 0) >= model['cutoff']) == (r['exchange_brilliant'] == '1') for r in rows)

    # 3. all 1,000 games, native evidence, model trained on the six development accounts only
    big = list(csv.DictReader(gzip.open(P / 'data/native-1000-outcomes.csv.gz', 'rt')))
    assert len({r['game_id'] for r in big}) == 1000 and sum(r['gallery_brilliant'] == '1' for r in big) == 1234
    out['all_1000_six_account_model'] = dict(
        mute_selective=count(big, lambda r: r['mute_selective'] == '1'),
        mute_exchange=count(big, lambda r: float(r['exchange_score_six_account_model'] or 0) >= SIX_ACCOUNT_CUTOFF))
    assert out['all_1000_six_account_model']['mute_selective'] == dict(awards=812, found=774, false_vs_gallery=38)
    assert out['all_1000_six_account_model']['mute_exchange'] == dict(awards=934, found=876, false_vs_gallery=58)
    ranked = sorted(big, key=lambda r: -float(r['exchange_score_six_account_model'] or 0))
    found = false = at38 = 0
    for r in ranked:
        if r['gallery_brilliant'] == '1': found += 1
        else: false += 1
        if false <= 38: at38 = found
    assert at38 == 820, at38
    out['all_1000_six_account_model']['mute_exchange_found_at_38_false'] = at38

    # 4. parity cases rescored from their saved features
    fx = json.loads((P / 'model/parity-fixtures.json').read_text())
    for c in fx['cases']:
        assert abs(score(model, [float(c['features'][k]) for k in model['features']]) - c['score']) < 1e-9
    out['parity_cases_rescored'] = len(fx['cases'])
    print(json.dumps(dict(PASS=True, **out), indent=2))


if __name__ == '__main__':
    main()
