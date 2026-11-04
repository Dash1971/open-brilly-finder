import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
P=Path('research/brilliants-improvement-2026-11-03/astra/v5/repeat-award');db=sqlite3.connect('research/brilliants-final-2026-11-03/corpus.sqlite3');db.row_factory=sqlite3.Row
V={1:90,2:300,3:300,4:500,5:1000,6:0}
class Budget:
 def __init__(self):self.n=0
 def tick(self):
  self.n+=1
  if self.n>512:raise TimeoutError

def gain(b,m):return (90 if b.is_en_passant(m) else V.get(b.piece_type_at(m.to_square),0))+(V[m.promotion]-90 if m.promotion else 0)
def see(b,s,z):
 z.tick();best=0
 for m in list(b.generate_legal_captures()):
  if m.to_square!=s:continue
  g=gain(b,m);b.push(m)
  try:best=max(best,g-see(b,s,z))
  finally:b.pop()
 return best

def probe(row,s):
 b=chess.Board(row['fen_after']);before=chess.Board(row['fen_before']);color=before.turn
 material=lambda x:sum(V[p.piece_type]*(1 if p.color==color else -1) for p in x.piece_map().values())
 credit=max(0,material(b)-material(before));out=[];z=Budget()
 try:
  for a in sorted(list(b.generate_legal_captures()),key=lambda x:x.uci()):
   if a.to_square!=chess.parse_square(s):continue
   g=gain(b,a);san=b.san(a);b.push(a)
   try:
    net=g-see(b,a.to_square,z)
    if net<=credit+100:continue
    item={'acceptance':a.uci(),'san':san,'net':net,'checks':[]};out.append(item)
    for m in sorted(list(b.legal_moves),key=lambda x:x.uci()):
     if not b.gives_check(m):continue
     z.tick();mg=gain(b,m);ms=b.san(m);b.push(m)
     try:
      if b.is_checkmate():item['checks'].append({'uci':m.uci(),'san':ms,'mate':True});continue
      responses=[]
      for e in list(b.legal_moves):
       z.tick();eg=gain(b,e);es=b.san(e);b.push(e)
       try:
        captures=[(gain(b,c),b.san(c),c.uci()) for c in b.generate_legal_captures()];best=max(captures,default=(0,'',''))
        responses.append({'evasion':es,'capture':best[1],'physicalGain':mg-eg+best[0]})
       finally:b.pop()
      if responses and min(x['physicalGain'] for x in responses)>100:item['checks'].append({'uci':m.uci(),'san':ms,'mate':False,'minPhysicalRecovery':min(x['physicalGain'] for x in responses),'evasions':responses})
     finally:b.pop()
   finally:b.pop()
 except TimeoutError:return {'status':'unknown','nodes':512,'acceptances':out}
 return {'status':'complete','nodes':z.n,'acceptances':out}
rows=[]
for r in json.load(open(P/'audit-complete.json'))['rows']:
 if not r['suppress']:continue
 gid,ply=r['key'].split(':');cur=dict(db.execute('select * from positions where game_id=? and ply=?',(gid,int(ply))).fetchone());origins=[]
 for p in r['priors']:
  if p.get('structural') and p.get('prediction',{}).get('symbol')=='!!':
   old=dict(db.execute('select * from positions where game_id=? and ply=?',(gid,p['ply'])).fetchone())
   for piece in p['pieces']:
    origins.append({'priorPly':p['ply'],'priorSan':p['san'],'victim':piece['square'],'prior':probe(old,piece['square']),'current':probe(cur,piece['square'])})
 rows.append({'key':r['key'],'san':r['san'],'origins':origins})
(P/'forcing.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:
 print(r['key'],r['san'])
 for o in r['origins']:
  for k in ['prior','current']:
   print(k,o[k]['status'],o[k]['nodes'],[(a['san'],[(c['san'],c.get('mate'),c.get('minPhysicalRecovery')) for c in a['checks']]) for a in o[k]['acceptances']])
