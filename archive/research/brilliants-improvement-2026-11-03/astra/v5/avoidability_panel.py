import json,runpy,contextlib,io
from pathlib import Path
O=Path('research/brilliants-improvement-2026-11-03/astra/v5')
with contextlib.redirect_stdout(io.StringIO()):m=runpy.run_path(str(O/'avoidability20.py'))
panel=json.loads(Path('research/brilliants-final-2026-11-03/panel-moves.json').read_text());core=json.loads((O/'avoidability818.json').read_text());rows=[]
for t in panel:
 rows.append({'key':f"{t['game_id']}:{t['ply']}",'cohort':'panel30','san':t['san'],'truth':t['fresh_label']=='!!','label':t['fresh_label'],'category':t['category'],'avoidability128':m['avoid'](t,128),'avoidability512':m['avoid'](t,512),'direct_stalemate_after_acceptance':m['terminalproof'](t)})
(O/'avoidability848.json').write_text(json.dumps({'scope':core['scope'],'rows':core['rows']+rows},indent=2)+'\n')
for truth in [True,False]:
 r=[x for x in rows if x['truth']==truth];print('PANEL',truth,len(r),'unavoidable',sum(x['avoidability512']['avoidable'] is False for x in r),'unknown',sum(x['avoidability512']['avoidable'] is None for x in r))
for x in rows:
 if x['avoidability512']['avoidable'] is not True:print(x)
print('stalemate',[(x['key'],x['direct_stalemate_after_acceptance']) for x in rows if x['direct_stalemate_after_acceptance']['proofs']])
