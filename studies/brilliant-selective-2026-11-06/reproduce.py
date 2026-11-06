#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Recount this study's published move decisions without engines or fitting."""
from pathlib import Path
import csv,gzip,json,hashlib
P=Path(__file__).resolve().parent

def recount(filename,variants,primary_only=False):
    counts={v:dict(TP=0,FN=0,FP=0,TN=0) for v in variants}
    keys=set()
    with gzip.open(P/'data'/filename,'rt',newline='') as f:
        for r in csv.DictReader(f):
            if primary_only and r['primary']!='True':continue
            k=(r['game_id'],r['ply'])
            assert k not in keys,k
            keys.add(k);truth=r['truth']=='True'
            for v in variants:
                pred=r[v] in ('True','!!')
                counts[v][('TP' if pred else 'FN') if truth else ('FP' if pred else 'TN')]+=1
    return counts

def main():
    development=recount('development-all-scored-moves.csv.gz',['production','pr285','reference_a','reference_b','finalist_a','finalist_b','finalist_c'])
    fresh=recount('witty-all-own-move-outcomes.csv.gz',['production','pr285','selective'],True)
    expected=json.loads((P/'data/development-final-report.json').read_text())['aggregate']
    expected_fresh=json.loads((P/'data/fresh-results.json').read_text())['counts']['primary']
    for got,want in [(development,expected),(fresh,expected_fresh)]:
        for v,c in got.items():assert c=={k:want[v][k] for k in c},(v,c,want[v])
    model=P/'reference/native/ui/analyse/src/noSweatBrilliantForestModel.json'
    assert hashlib.sha256(model.read_bytes()).hexdigest()=='1a7150fbe52f440922d94d3ae2af337383d63f370b52d0379aeee22d581d056c'
    print(json.dumps({'PASS':True,'development':development,'fresh':fresh},indent=2))
if __name__=='__main__':main()
