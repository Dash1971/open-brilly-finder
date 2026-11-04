#!/usr/bin/env python3
"""Fixed external-policy comparison; no training, thresholds, or unknown-as-negative labels."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
SEED=20261104
BOOT=2000

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def ratio(n,d):return n/d if d else None

def metrics(meta,awards,indices=None):
    ids=list(range(len(meta))) if indices is None else list(indices)
    counts=Counter()
    for i in ids:
        truth=meta[i]['truth']; a=awards[i]
        if a is None:counts['unresolved_positive' if truth else 'unresolved_negative']+=1
        elif a:counts['TP' if truth else 'FP']+=1
        else:counts['FN_known' if truth else 'TN_known']+=1
    for name in ['TP','FP','FN_known','TN_known','unresolved_positive','unresolved_negative']:counts[name]+=0
    n=len(ids);p=sum(meta[i]['truth'] for i in ids);neg=n-p;un=counts['unresolved_positive']+counts['unresolved_negative'];tp=counts['TP'];fp=counts['FP']
    return {**dict(counts),'cases':n,'positives':p,'negatives':neg,'resolved':n-un,'unresolved':un,'coverage':ratio(n-un,n),
      'positive_coverage':ratio(p-counts['unresolved_positive'],p),'negative_coverage':ratio(neg-counts['unresolved_negative'],neg),
      'confirmed_awards':tp+fp,'precision_of_confirmed_awards':ratio(tp,tp+fp),'wrong_fraction_of_confirmed_awards':ratio(fp,tp+fp),
      'confirmed_recall_all_positives':ratio(tp,p),'recall_bounds_if_unresolved_completed':[ratio(tp,p),ratio(tp+counts['unresolved_positive'],p)],
      'resolved_only_recall':ratio(tp,p-counts['unresolved_positive'])}

def paired(meta,a,b):
    tests={
      'recovered_correct':lambda y,x,z:y and x is True and not z,
      'lost_correct_known':lambda y,x,z:y and x is False and z,
      'new_wrong':lambda y,x,z:not y and x is True and not z,
      'removed_wrong_known':lambda y,x,z:not y and x is False and z,
      'unresolved_baseline_correct':lambda y,x,z:y and x is None and z,
      'unresolved_baseline_wrong':lambda y,x,z:not y and x is None and z,
      'shared_correct':lambda y,x,z:y and x is True and z,
      'shared_wrong':lambda y,x,z:not y and x is True and z,
    }
    return {name:{'count':len(keys),'keys':keys} for name,fn in tests.items()
            for keys in [[m['key'] for m,x,z in zip(meta,a,b) if fn(m['truth'],x,z)]]}

def groupbootstrap(meta,a,b):
    groups=sorted({m['group'] for m in meta});gi={g:i for i,g in enumerate(groups)}
    # Only confirmed awards are counted. Unknown is not entered in any FN/TN cell.
    # The comparison is a lower-bound coverage-plus-detection result, not a fully resolved classifier estimate.
    matrix=np.zeros((len(groups),7),dtype=np.int64)
    for m,x,z in zip(meta,a,b):
        y=m['truth'];g=gi[m['group']]
        matrix[g]+=np.array([y,int(y and x is True),int(not y and x is True),int(y and z),int(not y and z),int(y and x is None),int(not y and x is None)])
    rng=np.random.default_rng(SEED);values=[]
    for _ in range(BOOT):
        v=matrix[rng.integers(0,len(groups),size=len(groups))].sum(axis=0)
        pos,tp,fp,btp,bfp,up,un=map(int,v)
        values.append([tp-btp,fp-bfp,(tp-btp)/pos if pos else np.nan,
          fp/(tp+fp)-bfp/(btp+bfp) if tp+fp and btp+bfp else np.nan,up,un])
    values=np.asarray(values)
    names=['confirmed_TP_delta','confirmed_FP_delta','confirmed_recall_all_positive_delta','wrong_fraction_of_confirmed_awards_delta','unresolved_positive','unresolved_negative']
    return {'samples':BOOT,'seed':SEED,'groups':len(groups),'method':'Paired group resampling of fixed observed decisions; unknowns remain unresolved, only true awards count. Does not model refitting, acquisition changes or hypothesis selection.',
      'percentile_95':{name:[float(x) for x in np.nanpercentile(values[:,i],[2.5,97.5])] for i,name in enumerate(names)}}

def main():
    if (HERE/'RESULTS.json').exists() or (HERE/'PAIRED-CASES.json').exists():raise RuntimeError('Refusing to overwrite completed evaluation')
    protocol=read(HERE/'PROTOCOL.json');meta=read(HERE/'LABELS-AND-GROUPS.json')
    assert sha(HERE/'LABELS-AND-GROUPS.json')==protocol['metadata_sha256']
    assert sha(HERE/'INPUTS.jsonl')==protocol['input_sha256']
    assert len(meta)==3724 and len({m['key'] for m in meta})==3724 and sum(m['truth'] for m in meta)==917
    groups=sorted({m['group'] for m in meta});assert len(groups)==972
    ordered=sorted(groups,key=lambda g:(hashlib.sha256(('mute-optimization-v1-outer:'+g).encode()).hexdigest(),g))
    folds={g:i%5 for i,g in enumerate(ordered)}
    assert all(folds[m['group']]==m['outer_fold'] for m in meta)
    baseline=[m['baseline_awards']['custom_retuned'] for m in meta];fixed=[m['baseline_awards']['custom_fixed'] for m in meta]
    assert (metrics(meta,baseline)['TP'],metrics(meta,baseline)['FP'])==(452,6)
    assert (metrics(meta,fixed)['TP'],metrics(meta,fixed)['FP'])==(436,6)
    assert sum(m['original_429_miss'] for m in meta)==429
    arms={};sources={};details={};raw_by_name={}
    for name,filename in [('wintr','WINTR-PREDICTIONS.jsonl'),('knights','KNIGHTS-PREDICTIONS.jsonl')]:
        path=HERE/filename;rows=[json.loads(line) for line in path.read_text().splitlines() if line]
        bykey={r['key']:r for r in rows};assert len(rows)==len(bykey)==len(meta) and set(bykey)=={m['key'] for m in meta}
        raw_by_name[name]=bykey;sources[filename]=sha(path)
        for row in rows:
            w=[row['windows'][name]['award'] for name in ['current','previous']]
            assert all(x is None or type(x) is bool for x in w)
            expected=False if False in w else True if all(x is True for x in w) else None
            assert row['award'] is expected
        for mode in ['both','current','previous']:
            key=name+'_'+mode
            awards=[bykey[m['key']]['award'] if mode=='both' else bykey[m['key']]['windows'][mode]['award'] for m in meta]
            arms[key]=awards
            known=[i for i,a in enumerate(awards) if a is not None]
            union=[True if b or a is True else a for b,a in zip(baseline,awards)]
            changes=paired(meta,awards,baseline);details[key]=changes
            subgroups={
              'original_429_misses':[i for i,m in enumerate(meta) if m['original_429_miss']],
              'eligible_ec_false':[i for i,m in enumerate(meta) if m['eligible'] and not m['ec_sacrifice']],
              'eligible_ec_true':[i for i,m in enumerate(meta) if m['eligible'] and m['ec_sacrifice']],
              'all_ec_false':[i for i,m in enumerate(meta) if not m['ec_sacrifice']],
              'hard_ordinary':[i for i,m in enumerate(meta) if m['negative_bucket']=='hard_ordinary'],
            }
            arms[key]={'awards':awards,'pooled':metrics(meta,awards),'resolved_only_matched_baseline':metrics(meta,baseline,known),
             'resolved_only_external':metrics(meta,awards,known),
             'per_fold':[{'fold':f,'external':metrics(meta,awards,[i for i,m in enumerate(meta) if m['outer_fold']==f]),
               'baseline':metrics(meta,baseline,[i for i,m in enumerate(meta) if m['outer_fold']==f])} for f in range(5)],
             'changes_vs_baseline':{k:v['count'] for k,v in changes.items()},
             'hypothetical_union':{'interpretation':'Descriptive only, not fitted, selected or deployed; baseline awards retained and confirmed external-only awards added. Unknown remains unknown when baseline rejects.',
              'pooled':metrics(meta,union),'added_correct':changes['recovered_correct']['count'],'added_wrong':changes['new_wrong']['count']},
             'subgroups':{k:{'external':metrics(meta,awards,ids),'baseline':metrics(meta,baseline,ids)} for k,ids in subgroups.items()},
             'bootstrap':groupbootstrap(meta,awards,baseline)}
    case_pairs=[]
    for i,m in enumerate(meta):
        row={**m,'external':{name:{mode:raw_by_name[name][m['key']]['award'] if mode=='both' else raw_by_name[name][m['key']]['windows'][mode]['award'] for mode in ['both','current','previous']} for name in raw_by_name}}
        case_pairs.append(row)
    for arm in arms.values():arm.pop('awards')
    reasons={name:{mode:dict(Counter(str(row['windows'][mode].get('reason') or row['windows'][mode].get('status')) for row in rows.values() if row['windows'][mode]['award'] is None)) for mode in ['current','previous']} for name,rows in raw_by_name.items()}
    result={'scope':protocol['scope'],'protocol_sha256':sha(HERE/'PROTOCOL.json'),'script_sha256':sha(Path(__file__)),'input_sha256':protocol['input_sha256'],'metadata_sha256':protocol['metadata_sha256'],'prediction_sha256':sources,
      'counts':{'cases':3724,'groups':972,'positives':917,'negatives':2807,'original_429_misses':429},
      'baseline':{'custom_retuned':metrics(meta,baseline),'custom_fixed':metrics(meta,fixed)},'arms':arms,'unresolved_reasons':reasons,
      'interpretation':'Known false means an explicit no-award decision. Unresolved positives/negatives are separate; they are not false/true negatives. Confirmed recall uses all917 positives and is a lower bound when unresolved. Baseline comparison on resolved subset is secondary; it is not fresh validation. Same outer groups, no training or inner cutoff selection.'}
    save(HERE/'PAIRED-CASES.json',{'changes':details,'cases':case_pairs});save(HERE/'RESULTS.json',result)
    print(json.dumps({'status':'complete','arms':{k:{'TP':v['pooled']['TP'],'FP':v['pooled']['FP'],'unresolved':v['pooled']['unresolved'],'added_correct':v['hypothetical_union']['added_correct'],'added_wrong':v['hypothetical_union']['added_wrong']} for k,v in arms.items()}}))
if __name__=='__main__':main()
