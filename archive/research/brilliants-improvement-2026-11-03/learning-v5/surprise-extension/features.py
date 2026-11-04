#!/usr/bin/env python3
"""Ten fixed shallow-vs-baseline descriptors, without new searches or label-based selection."""
import csv,hashlib,json,math,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;IMPROVE=BASE.parent;FINAL=IMPROVE.parent/'brilliants-final-2026-11-03'
def load(p):return json.loads(p.read_text())
def cp(line,color):return line.get('cp')*(1 if color else -1) if line and line.get('cp') is not None else None
def score(line,color):
 if not line:return None
 if line.get('mate') is not None:return (1000 if line['mate']>0 else -1000 if line['mate']<0 else 0)*(1 if color else -1)
 return max(-1000,min(1000,cp(line,color)))
def chance(s):return 100/(1+math.exp(-.00368208*s)) if s is not None else None
def first(window):return window['lines'][0] if window and window['lines'] else None
start=time.monotonic();data=load(BASE/'features.json');protocol=load(ROOT/'EXTENSION-PROTOCOL.json');shallow=load(IMPROVE/'surprise-v5/analysis-shallow.json');weak={f"{t['game_id']}:{t['ply']}":t for t in shallow['targets']};assert len(weak)==848;strong={}
for name in ('analysis-baseline.json','analysis-panel.json'):
 d=load(FINAL/name)
 for t in d['targets']:strong[f"{t['game_id']}:{t['ply']}"]=(t,d)
case_index={c['key']:c for c in data['cases']};missing=0;root_absent=0;checks=0
for row in data['window_rows']:
 t,d=strong[row['key']];w=weak.get(row['key']);which=row['window'];color=t['fen_before'].split()[1]=='w';bb=aa=strongbb=None
 if w:
  assert w['fen_before']==t['fen_before'] and w['fen_after']==t['fen_after'];ws=[shallow['snapshots'][i] for i in w['snapshot_ids']];ss=[d['snapshots'][i] for i in t['snapshot_ids']]
  assert ws[-2]['fen']==ss[-2]['fen'] and ws[-1]['fen']==ss[-1]['fen'];checks+=1
  bb=ws[-2].get(which);aa=ws[-1]['current'] if which=='previous' and ws[-1]['terminal'] else ws[-1].get(which);strongbb=ss[-2].get(which)
 complete=bool(bb and aa and bb['lines'] and aa['lines']);best=first(bb);after=first(aa);root=next((l for l in bb['lines'] if l['moves'] and l['moves'][0]==t['uci']),None) if bb else None;strongbest=first(strongbb);loss=chance(score(best,color))-chance(score(after,color)) if complete else None;weakcp=cp(after,color);strongcp=row['features']['after_cp']
 features={'weak_mapped_loss_pp':loss,'weak_played_root_present':bool(root) if bb else None,'weak_played_root_rank':next((i+1 for i,l in enumerate(bb['lines']) if l['moves'] and l['moves'][0]==t['uci']),None) if bb else None,'weak_same_root_gap_pp':chance(score(best,color))-chance(score(root,color)) if root else None,'weak_after_cp':weakcp,'strong_minus_weak_after_cp':strongcp-weakcp if strongcp is not None and weakcp is not None else None,'weak_minus_strong_loss_pp':loss-row['features']['mapped_loss_pp'] if loss is not None and row['features']['mapped_loss_pp'] is not None else None,'weak_best_differs_from_strong':best['moves'][0]!=strongbest['moves'][0] if best and strongbest and best['moves'] and strongbest['moves'] else None,'strong_minus_weak_before_depth':strongbb['depth']-bb['depth'] if strongbb and bb else None,'weak_window_missing':not complete}
 assert list(features)==protocol['new_predictors'];row['features'].update(features);case_index[row['key']]['windows'][which]['features'].update(features);missing+=not complete;root_absent+=root is None
new_names=data['predictors']+protocol['new_predictors'];data['predictors']=new_names;data['scope']='848unblindeddevelopment cases; authorized ten-feature shallow-vs-strong extension; same grouped folds and hard eligibility masks.'
(ROOT/'features.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
with (ROOT/'features.csv').open('w') as stream:
 out=csv.DictWriter(stream,fieldnames=['key','window','truth','eligible','group','fold']+new_names);out.writeheader()
 for r in data['window_rows']:out.writerow({**{n:r[n] for n in ('key','window','truth','eligible','group','fold')},**r['features']})
checks={'cases':len(data['cases']),'window_rows':len(data['window_rows']),'added_descriptors':len(protocol['new_predictors']),'before_after_FEN_matches':checks,'weak_window_missing':missing,'weak_played_root_unsearched_windows':root_absent,'all_group_folds_and_labels_unchanged':all(a['fold']==b['fold'] and a['group']==b['group'] and a['truth']==b['truth'] for a,b in zip(data['cases'],load(BASE/'features.json')['cases'])),'elapsed_seconds':round(time.monotonic()-start,3),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};(ROOT/'FEATURE-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
