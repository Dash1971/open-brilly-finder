import json,runpy,contextlib,io,time
from pathlib import Path
R=Path('research/brilliants-improvement-2026-11-03');O=R/'astra/v5'
with contextlib.redirect_stdout(io.StringIO()):mod=runpy.run_path(str(O/'avoidability20.py'))
physical={r['key']:r for r in json.loads((O/'physical-818.json').read_text())};out=[];start=time.monotonic()
for cohort,path in [('old618',Path('mute-chess-research/studies/brilliant-moves/analysis-baseline.json')),('new200',R/'validation/analysis-baseline.json')]:
 data=json.loads(path.read_text())
 for t in data['targets']:
  key=f"{t['game_id']}:{t['ply']}";p=physical[key]
  out.append({'key':key,'cohort':cohort,'san':t['san'],'truth':p['truth'],'v4':p['v4'],'avoidability128':mod['avoid'](t,128),'avoidability512':mod['avoid'](t,512),'direct_stalemate_after_acceptance':mod['terminalproof'](t)})
result={'scope':'All818aredevelopment. Static all-piece offer avoidability. Unknown budget exhaustion is not unavoidable. No engine/policy scoring.','elapsed_seconds':time.monotonic()-start,'rows':out}
(O/'avoidability818.json').write_text(json.dumps(result,indent=2)+'\n')
print('n',len(out),'seconds',result['elapsed_seconds'])
for cohort in ['old618','new200']:
 for truth in [True,False]:
  rows=[x for x in out if x['cohort']==cohort and x['truth']==truth and x['v4']=='!!'];print(cohort,'TP' if truth else 'FP','awards',len(rows),'unavoidable',sum(x['avoidability512']['avoidable'] is False for x in rows),'unknown',sum(x['avoidability512']['avoidable'] is None for x in rows),'stalemate',sum(bool(x['direct_stalemate_after_acceptance']['proofs']) for x in rows))
for x in out:
 if x['v4']=='!!' and x['avoidability512']['avoidable'] is False:print(x['key'],x['san'],'TP' if x['truth'] else 'FP','stalemate',x['direct_stalemate_after_acceptance']['proofs'])
print('TOTAL UNKNOWN512',sum(x['avoidability512']['avoidable'] is None for x in out),'128',sum(x['avoidability128']['avoidable'] is None for x in out))
print('ALL STALEMATE',[x['key'] for x in out if x['direct_stalemate_after_acceptance']['proofs']])
