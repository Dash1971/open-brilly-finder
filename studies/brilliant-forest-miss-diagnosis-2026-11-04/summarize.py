"""Descriptive summaries of frozen paths and matching; no classifier changes."""
import json,hashlib,sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parents[1]
TRAIN=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    cs={c['key']:c for c in json.loads(TRAIN.read_text())['cases']}
    trace=json.loads((H/'FOREST-TRACE.json').read_text());tr={r['key']:r for r in trace['rows']}
    matched=json.loads((H/'MATCHES.json').read_text());matches=matched['rows']
    trees=json.loads((H/'OUTER-TREES.json').read_text());names=trees['features']
    def ec(k):return bool(cs[k]['windows']['current']['features']['ec_sacrifice'])
    misses=[r['key'] for r in matches]
    found=[r['key'] for r in tr.values() if r['truth'] and r['awarded']]
    ordinary=[k for k,c in cs.items() if not c['truth'] and tr[k]['eligible'] and c['negative_bucket']=='hard_ordinary']
    def describe(keys):
        rows=[tr[k] for k in keys];low=[r['windows'][r['limiting_window']] for r in rows]
        contrib={n:float(np.mean([r['path_contributions_by_base_feature'].get(n,0) for r in low])) for n in names[:75]}
        leaf={n:float(np.mean([r['leaf_statistics'][n] for r in low])) for n in low[0]['leaf_statistics']} if low else {}
        scores=[r['minimum_score'] for r in rows]
        return dict(n=len(keys),median_score=float(np.median(scores)) if scores else None,
                    q10_q90=np.quantile(scores,[.1,.9]).tolist() if scores else [],
                    both_windows_below_cutoff=sum(all(w['score']<r['saved_custom_retuned_threshold'] for w in r['windows'].values()) for r in rows),
                    mean_leaf_statistics=leaf,mean_path_contributions=contrib,
                    top_negative_feature_appearances=dict(Counter(x['feature'] for r in rows for x in r['limiting_window_top5_negative_path_contributions']).most_common(12)))
    # Resolve terminal leaf paths; compares corresponding windows under the same fold forest.
    def route(k,w,t):
        f=cs[k]['windows'][w]['features'];vals=[f[n] for n in names[:75]]+[f[n] is None for n in names[:75]]
        path='';node=t
        while node['kind']=='split':
            v=vals[node['feature_index']];left=v is None or v<=node['threshold'];path+='L' if left else 'R';node=node['left' if left else 'right']
        return path
    cache={}
    def paths(k):
        if k not in cache:
            forest=trees['forests'][tr[k]['outer_fold']]
            if isinstance(forest,dict):forest=forest['trees']
            cache[k]=[route(k,w,t) for w in ('current','previous') for t in forest]
        return cache[k]
    pairs=[]
    for r in matches:
        m=r['ordinary'];assert tr[r['key']]['outer_fold']==tr[m['key']]['outer_fold']
        a,b=paths(r['key']),paths(m['key']);shared=sum(x==y for x,y in zip(a,b))/len(a)
        diffs={n:float(np.mean([tr[r['key']]['windows'][w]['path_contributions_by_base_feature'].get(n,0)-
                                tr[m['key']]['windows'][w]['path_contributions_by_base_feature'].get(n,0) for w in ('current','previous')])) for n in names[:75]}
        pairs.append(dict(miss=r['key'],ordinary=m['key'],exact_anchors=m['exact_anchors'],distance=m['distance'],
                          same_leaf_fraction=shared,score_difference=r['score']-m['score'],
                          top_positive_path_differences=sorted(diffs.items(),key=lambda x:-x[1])[:5],
                          top_negative_path_differences=sorted(diffs.items(),key=lambda x:x[1])[:5]))
    out=dict(scope='Descriptive path and pair summaries only; no performance claim, no rules, no feature interventions.',
        inputs={str(p):sha(p) for p in [TRAIN,H/'FOREST-TRACE.json',H/'MATCHES.json',H/'OUTER-TREES.json']},
        script_sha256=sha(Path(__file__)),groups={n:describe(keys) for n,keys in [('misses',misses),('found',found),('hard_ordinary',ordinary),
                        ('miss_ec_false',[k for k in misses if not ec(k)]),('miss_ec_true',[k for k in misses if ec(k)])]},
        ec_eligible_counts={str(v):dict(positive=sum(c['truth'] and tr[k]['eligible'] and ec(k)==v for k,c in cs.items()),
                                      awarded=sum(tr[k]['truth'] and tr[k]['awarded'] and ec(k)==v for k in cs)) for v in (False,True)},
        pair_summary=dict(n=len(pairs),median_same_leaf_fraction=float(np.median([p['same_leaf_fraction'] for p in pairs])),
                          exact_anchor_median_same_leaf_fraction=float(np.median([p['same_leaf_fraction'] for p in pairs if p['exact_anchors']])),
                          all128_leaves_same=sum(p['same_leaf_fraction']==1 for p in pairs),
                          median_score_difference=float(np.median([p['score_difference'] for p in pairs]))),pairs=pairs)
    (H/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(groups={n:{k:d[k] for k in ('n','median_score','both_windows_below_cutoff')} for n,d in out['groups'].items()},
                         ec_counts=out['ec_eligible_counts'],pair_summary=out['pair_summary']),indent=2))
if __name__=='__main__':main()
