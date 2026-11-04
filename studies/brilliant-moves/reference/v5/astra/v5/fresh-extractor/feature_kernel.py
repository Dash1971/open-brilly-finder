#!/usr/bin/env python3
"""Auditable semantic features on848 already-unblinded cases; no engine or UI."""
import csv,hashlib,importlib.util,json,math,resource,sys,time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
import chess
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'learning-v5'))
import physical_kernel as pk
ROOT=Path(__file__).resolve().parent;IMPROVE=ROOT.parent;FINAL=IMPROVE.parent/'brilliants-final-2026-11-03'
VALUES={1:90,2:300,3:300,4:500,5:1000,6:0}
def load(p):return json.loads(p.read_text())
def save(name,x):(ROOT/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def raw(b,color):return sum(VALUES[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
def canon(f):return ' '.join(chess.Board(f).fen().split()[:4])
def cp(line,color):return line.get('cp')*(1 if color else -1) if line and line.get('cp') is not None else None
def mate(line,color):return line.get('mate')*(1 if color else -1) if line and line.get('mate') is not None else None
def normalized(line,color):
 if not line:return None
 m=mate(line,color)
 return (1000 if m>0 else -1000 if m<0 else 0) if m is not None else max(-1000,min(1000,cp(line,color)))
def wc(x):return 100/(1+math.exp(-.00368208*x)) if x is not None else None
class OfferBudget:
 def __init__(self):self.nodes=0
 def tick(self):
  self.nodes+=1
  if self.nodes>512:raise TimeoutError('512-node attribution proof cap')
def exchange(b,square,budget):
 budget.tick();best=0
 for move in list(b.generate_legal_captures()):
  if move.to_square!=square:continue
  gain=pk.mp.gain(b,move);b.push(move)
  try:value=gain-exchange(b,square,budget)
  finally:b.pop()
  best=max(best,value)
 return best

def extend_panel(t):
 b=chess.Board(t['fen_before']);a=chess.Board(t['fen_after']);color=b.turn;base=raw(b,color);credit=max(0,raw(a,color)-base);budget=pk.Budget();out={'raw_before':base,'credit':credit,'acceptances':[],'unknown':False}
 try:
  for move in list(a.generate_legal_captures()):
   victim=a.piece_at(move.to_square)
   if not victim or victim.piece_type in (1,6):continue
   san=a.san(move);value=pk.mp.gain(a,move);a.push(move)
   try:
    net=value-pk.mp.same_square(a,move.to_square,pk.mp.Budget())
    if net<=credit+100:continue
    outcome,line=pk.search(a,color,3,budget)
   finally:a.pop()
   out['acceptances'].append({'uci':move.uci(),'san':san,'victim':victim.symbol(),'offer_net':net,'debt3':base-outcome,'conditional_line':pk.mp.line_san(a,[move.uci()]+line)})
 except TimeoutError:out['unknown']=True
 out.update(nodes=budget.nodes,checked_horizon_leaves=budget.leafchecks,mate_terminals=budget.mates,quiet_evasions_generated=budget.evasions)
 out['max_debt3']=max((a['debt3'] for a in out['acceptances']),default=None) if not out['unknown'] else None
 return out

def attribution(t,previous,physical):
 after=chess.Board(t['fen_after']);before=chess.Board(t['fen_before']);move=chess.Move.from_uci(t['uci']);budget=OfferBudget();offers={chess.parse_square(x['uci'][2:4]) for x in physical['acceptances']};out={'attribution_unknown':False,'prior_history_missing':previous is None,'offered_piece_moved':move.to_square in offers,'offered_piece_count':len(offers),'already_vulnerable_same_square_count':None,'prior_offer_gain_same_square_max':None,'prior_offer_gain_original_square_max':None}
 for role in ('p','n','b','r','q','k'):out['offered_role_'+role]=any(after.piece_at(s).symbol().lower()==role for s in offers)
 if previous is None:return out
 prior=chess.Board(previous);same=[];original=[];unmoved=0
 try:
  for square in offers:
   piece=after.piece_at(square);origin=move.from_square if square==move.to_square else square
   if before.is_castling(move) and piece.piece_type==4 and chess.square_file(square) in (3,5):origin=chess.square(7 if chess.square_file(square)==5 else 0,chess.square_rank(square))
   old=prior.piece_at(square);same_gain=exchange(prior,square,budget) if old==piece else 0;same.append(same_gain)
   old=prior.piece_at(origin);original.append(exchange(prior,origin,budget) if old==piece else 0)
   unmoved+=square!=move.to_square and same_gain>100
  out.update(already_vulnerable_same_square_count=unmoved,prior_offer_gain_same_square_max=max(same,default=0),prior_offer_gain_original_square_max=max(original,default=0))
 except TimeoutError:out['attribution_unknown']=True
 return out


from avoidability_kernel import avoid,terminalproof

def extract_features(t,c):
 # Input t contains only UCI, before/after FENs, snapshots and optional full PGN validation upstream.
 b=chess.Board(t['fen_before']);a=chess.Board(t['fen_after']);color=b.turn;move=chess.Move.from_uci(t['uci']);piece=b.piece_at(move.from_square)
 if move not in b.legal_moves:raise ValueError('Illegal played move')
 expected=b.copy();expected.push(move)
 if expected.fen()!=a.fen():raise ValueError('Played move/FEN mismatch')
 p=extend_panel(t)
 v={'avoidability512':avoid(t,512),'direct_stalemate_after_acceptance':terminalproof(t)}
 snaps=t['snaps'];prior=snaps[-3] if len(snaps)>2 else None;before=snaps[-2];after=snaps[-1];previous_fen=prior['fen'] if prior else None
 f={'raw_offer':c['raw_offer'],'ec_sacrifice':c['ec_sacrifice'],'mating_acceptance':c['mate_acceptance'],'checked_continuation':c['checked_continuation'],'converted_material_or_endgame':c['phase_context_relevant'],'move_capture':b.is_capture(move),'move_check':a.is_check(),'move_in_check':b.is_check(),'move_castling':b.is_castling(move),'move_en_passant':b.is_en_passant(move),'move_promotion':bool(move.promotion),'raw_material_before':raw(b,color),'raw_material_after':raw(a,color),'immediate_material_gain':raw(a,color)-raw(b,color),'capture_promotion_credit':p['credit'],'phase':sum({1:0,2:1,3:1,4:2,5:4,6:0}[x.piece_type] for x in b.piece_map().values()),'ec_material_before':c['ec_material'][-2],'ec_material_after':c['ec_material'][-1],'ec_material_margin':c['ec_material'][-2]+c['ec_material'][-1]-100,'physical_unknown':p['unknown'],'physical_checked_horizon':p['checked_horizon_leaves']>0,'physical_mate_leaf':p['mate_terminals']>0,'physical_debt3_max':None if p['unknown'] else p['max_debt3'],'physical_debt3_min':None if p['unknown'] else min((x['debt3'] for x in p['acceptances']),default=None),'offer_exchange_gain_max':max((x['offer_net'] for x in p['acceptances']),default=None),'offer_exchange_gain_min':min((x['offer_net'] for x in p['acceptances']),default=None),'avoidability':v['avoidability512']['avoidable'],'avoidability_unknown':v['avoidability512']['avoidable'] is None,'direct_stalemate_acceptance':bool(v['direct_stalemate_after_acceptance']['proofs']) if v['direct_stalemate_after_acceptance']['complete'] else None,'stalemate_probe_unknown':not v['direct_stalemate_after_acceptance']['complete']}
 f.update(attribution(t,previous_fen,p))
 for role in ('p','n','b','r','q','k'):f['moved_role_'+role]=piece.symbol().lower()==role
 windows={}
 for which in ('current','previous'):
  bb=before[which];aa=after['current'] if which=='previous' and after['terminal'] else after[which];pp=prior[which] if prior else None;z=dict(f);z.update(window_complete=c[which]['complete'],before_depth=bb['depth'] if bb else None,after_depth=aa['depth'] if aa else None,prior_depth=pp['depth'] if pp else None,before_roots=len(bb['lines']) if bb else 0)
  best=bb['lines'][0] if bb else None;child=aa['lines'][0] if aa else None;old=pp['lines'][0] if pp else None;root=next((l for l in bb['lines'] if l['moves'] and l['moves'][0]==t['uci']),None) if bb else None
  for name,line in (('best',best),('after',child),('prior',old),('played_root',root)):
   z[name+'_cp']=cp(line,color);z[name+'_mate']=mate(line,color);z[name+'_mapped_score']=normalized(line,color)
  z['mapped_loss_pp']=c[which].get('loss_pp');z['same_root_loss_pp']=wc(normalized(best,color))-wc(normalized(root,color)) if root else None;z['same_root_rank']=next((i+1 for i,line in enumerate(bb['lines']) if line['moves'] and line['moves'][0]==t['uci']),None) if bb else None;z['played_root_missing']=root is None
  z['best_second_gap_pp']=wc(normalized(best,color))-wc(normalized(bb['lines'][1],color)) if bb and len(bb['lines'])>1 else None
  z['after_minus_prior_cp']=c[which].get('after_minus_previous_cp');z['best_minus_prior_cp']=c[which].get('before_minus_previous_cp');z['winning_safe_alternatives']=len(c[which].get('safe_alternatives',[]));z['safe_alternative_best_cp']=max((x['cp_mover'] for x in c[which].get('safe_alternatives',[])),default=None)
  gates=c[which].get('gates') or {};eligible=all(gates.get(g) is True for g in ('two_roots','raw_offer','quality','after_floor'))
  windows[which]={'features':z,'eligible':eligible}

 return {'windows':windows,'confidence_sufficient':c['confidence_sufficient'],'diagnostics':{'physical_unknown':p['unknown'],'physical_nodes':p['nodes']}}
