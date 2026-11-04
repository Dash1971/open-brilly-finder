"""Diagnostic feature matching of all eligible misses; not classifier validation."""
import json,hashlib,math,sys
from pathlib import Path
from collections import Counter
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parents[1]
TRAIN=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
PREDS=W/'research/brilliant-evaluation-consistency-2026-11-04/PREDICTIONS.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):(H/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def family(n):
    if n.endswith('_unknown') or n in ('window_complete','played_root_missing','prior_history_missing','before_roots') or n.endswith('_depth'):return 'coverage'
    if n.startswith('move_') or n.startswith('moved_role_'):return 'move'
    if n.startswith('offered_') or n.startswith('prior_offer_') or n=='already_vulnerable_same_square_count':return 'attribution'
    if n.startswith(('raw_material','ec_material')) or n in ('capture_promotion_credit','immediate_material_gain','phase'):return 'material'
    if n.startswith(('physical_','offer_exchange_')) or n in ('raw_offer','ec_sacrifice','mating_acceptance','checked_continuation','converted_material_or_endgame','avoidability','direct_stalemate_acceptance'):return 'offer'
    return 'evaluation'
def anchors(c):
    f=c['windows']['current']['features']
    return [f['ec_sacrifice'],f['move_capture'],f['move_check'],f['offered_piece_moved'],
            f['offered_role_n'] or f['offered_role_b'],f['offered_role_r'],f['offered_role_q']]
def main():
    proto=json.loads((H/'MATCH-PROTOCOL.json').read_text())
    assert not (H/'MATCHES.json').exists()
    assert sha(Path(__file__))==proto['script_sha256']
    assert all(sha(k)==v for k,v in proto['input_sha256'].items())
    d=json.loads(TRAIN.read_text());cs=d['cases'];names=d['predictors']
    pp={r['key']:r for r in json.loads(PREDS.read_text())};index={c['key']:i for i,c in enumerate(cs)}
    eligible=[i for i,c in enumerate(cs) if not pp[c['key']]['old_reasons']]
    misses=[i for i in eligible if cs[i]['truth'] and not pp[cs[i]['key']]['retuned_baseline']]
    ordinary=[i for i in eligible if not cs[i]['truth'] and cs[i]['negative_bucket']=='hard_ordinary']
    legacy=[i for i in eligible if not cs[i]['truth'] and cs[i]['negative_bucket']=='legacy_mixed']
    found=[i for i in eligible if pp[cs[i]['key']]['retuned_baseline'] and cs[i]['truth']]
    assert len(misses)==429 and len(ordinary)==226 and len(found)==452
    x=np.array([[[np.nan if c['windows'][w]['features'][n] is None else float(c['windows'][w]['features'][n])
                  for n in names] for w in ('current','previous')] for c in cs])
    scales=[]
    for j,n in enumerate(names):
        vals=x[eligible,:,j].ravel();vals=vals[np.isfinite(vals)]
        if not len(vals):scales.append(1.);continue
        lo,hi=np.quantile(vals,[.05,.95]);span=hi-lo
        if span==0:span=max(vals)-min(vals)
        scales.append(float(span) if span else 1.)
    families={f:[j for j,n in enumerate(names) if family(n)==f] for f in sorted({family(n) for n in names})}
    def compare(i,j):
        a,b=x[i],x[j];known=np.isfinite(a)&np.isfinite(b)
        dist=np.where(known,np.minimum(np.abs(np.nan_to_num(a)-np.nan_to_num(b))/scales,1),
                      np.isfinite(a)!=np.isfinite(b)).astype(float).mean(axis=0)
        fd={f:float(dist[js].mean()) for f,js in families.items()}
        return float(np.mean(list(fd.values()))),fd,dist
    def match(i,pool):
        pc=pp[cs[i]['key']]
        candidates=[j for j in pool if pp[cs[j]['key']]['outer_fold']==pc['outer_fold'] and cs[j]['group']!=cs[i]['group']]
        exact=[j for j in candidates if anchors(cs[j])==anchors(cs[i])]
        pool2=exact or candidates
        if not pool2:return None
        ranked=sorted((compare(i,j)[0],cs[j]['key'],j) for j in pool2)
        distance,key,j=ranked[0];_,fd,dist=compare(i,j)
        diffs=sorted(range(len(names)),key=lambda n:(-dist[n],names[n]))[:10]
        return dict(key=key,group=cs[j]['group'],distance=distance,exact_anchors=bool(exact),candidate_count=len(candidates),
                    exact_candidate_count=len(exact),family_distance=fd,score=pp[key]['score'],
                    original_award=pp[key]['retuned_baseline'],top_differences=[dict(feature=names[k],normalized_distance=float(dist[k]),
                    miss_current=cs[i]['windows']['current']['features'][names[k]],control_current=cs[j]['windows']['current']['features'][names[k]]) for k in diffs])
    rows=[]
    for i in misses:
        c=cs[i];p=pp[c['key']];gap=p['retuned_threshold']-p['score']
        rows.append(dict(key=c['key'],group=c['group'],fold=p['outer_fold'],score=p['score'],threshold=p['retuned_threshold'],
            score_shortfall=gap,score_band='near' if gap<=.025 else 'middle' if gap<=.10 else 'far',
            ec=bool(c['windows']['current']['features']['ec_sacrifice']),
            ordinary=match(i,ordinary),legacy_nonbrilliant=match(i,legacy),found_brilliant=match(i,found)))
    # Small descriptive panel: two nearest distinct-group pairs in each prespecified stratum.
    panel=[];used=set()
    for ec in (False,True):
        for band in ('near','middle','far'):
            available=[r for r in rows if r['ec']==ec and r['score_band']==band and r['ordinary']]
            available.sort(key=lambda r:(not r['ordinary']['exact_anchors'],r['ordinary']['distance'],r['key']))
            chosen=0
            for r in available:
                if r['group'] in used or r['ordinary']['group'] in used:continue
                panel.append(r);used.update([r['group'],r['ordinary']['group']]);chosen+=1
                if chosen==2:break
    def descriptives(ii):
        out={}
        for n in names:
            vals=[cs[i]['windows']['current']['features'][n] for i in ii]
            finite=[float(v) for v in vals if v is not None]
            out[n]=dict(known=len(finite),missing=len(vals)-len(finite),median=float(np.median(finite)) if finite else None,
                        q25=float(np.quantile(finite,.25)) if finite else None,q75=float(np.quantile(finite,.75)) if finite else None)
        return out
    summary=dict(cases=len(cs),misses=len(misses),hard_ordinary_pool=len(ordinary),legacy_pool=len(legacy),found_pool=len(found),
        ec_band_counts=dict(Counter(str(r['ec'])+':'+r['score_band'] for r in rows)),
        match_coverage={kind:dict(matched=sum(r[kind] is not None for r in rows),exact_anchors=sum(bool(r[kind] and r[kind]['exact_anchors']) for r in rows),
            distinct_controls=len({r[kind]['key'] for r in rows if r[kind]}),max_control_reuse=max(Counter(r[kind]['key'] for r in rows if r[kind]).values(),default=0),
            distance_quantiles=np.quantile([r[kind]['distance'] for r in rows if r[kind]],[0,.25,.5,.75,1]).tolist())
            for kind in ('ordinary','legacy_nonbrilliant','found_brilliant')},panel_pairs=len(panel),
        feature_families={f:[names[j] for j in js] for f,js in families.items()},scales=dict(zip(names,scales)),
        descriptive_current_features={'misses':descriptives(misses),'ordinary':descriptives(ordinary),'found':descriptives(found)},
        caveats=['Feature matching is descriptive, label-informed and not new validation.','Same outer-fold controls share the same fixed forest but are not matched on full boards.',
                 'All429 misses retained. If no exact semantic-anchor match exists, nearest same-fold fallback is flagged; no closeness claim.',
                 'Primary pool excludes193 legacy negatives of mixed label provenance and2 eligible easy errors; legacy comparisons retained separately.',
                 'Controls can be reused for429-case coverage;12-pair panel uses distinct groups. No pairwise independence or performance claim.',
                 'Equal-family Gower distance can still compress or miss important chess distinctions; nearest does not mean identical.'])
    write('MATCHES.json',dict(protocol_sha256=sha(H/'MATCH-PROTOCOL.json'),summary=summary,rows=rows))
    selected=[]
    for pair in panel:
        selected.append(dict(pair=pair,miss=cs[index[pair['key']]],ordinary=cs[index[pair['ordinary']['key']]]))
    write('PANEL.json',selected)
    print(json.dumps({k:summary[k] for k in ('misses','hard_ordinary_pool','ec_band_counts','match_coverage','panel_pairs')},indent=2))
if __name__=='__main__':main()
