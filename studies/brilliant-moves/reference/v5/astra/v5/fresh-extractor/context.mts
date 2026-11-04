// Study-local semantic context extraction. No identity or observed label inputs.
import fs from 'node:fs';
import {naiveMaterial,isSacrifice,isMuteSacrifice,hasMatingAcceptance,continuedOfferWhileInCheck,convertedMaterialOrEndgame,normalized,winChance,annotation} from '../../../root/frozen-v4/noSweatClassify.ts';
import {after} from '../../../root/frozen-v4/noSweatCore.ts';
const cache=new Map<string,number>();
const material=(fen:string)=>{if(!cache.has(fen))cache.set(fen,naiveMaterial(fen));return cache.get(fen)!;};
export function semanticContext(t:any){
 const snaps=t.snaps;
 const reviews=snaps.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:s.quality}));
  const color=t.fen_before.split(' ')[1]==='w'?'white':'black',n=reviews.length;
  const broad=isSacrifice(t.fen_before,t.fen_after,material),raw=isMuteSacrifice(t.fen_before,t.fen_after);
  const mateAcceptance=!broad&&hasMatingAcceptance(t.fen_before,t.fen_after);
  const continuation=continuedOfferWhileInCheck(n>2?snaps[n-3].fen:undefined,t.fen_before,t.fen_after,t.uci);
  const phaseRelevant=convertedMaterialOrEndgame(t.fen_before);
  const offers=new Map<string,boolean>();
  const isOffer=(uci:string)=>{if(!offers.has(uci))offers.set(uci,isMuteSacrifice(t.fen_before,uci===t.uci?t.fen_after:after(t.fen_before,uci)));return offers.get(uci)!;};
  const window=(b:any,a:any,p:any)=>{
   if(!b||!a)return {complete:false,gates:null};
   const next=normalized(a.lines[0],color),best=normalized(b.lines[0],color),loss=winChance(best)-winChance(next);
   const searchedMate=a.lines[0].mate!==undefined&&next>0;
   const safe=b.lines.filter((l:any)=>l.moves[0]!==t.uci&&normalized(l,color)>=600&&!isOffer(l.moves[0])).map((l:any)=>({uci:l.moves[0],cp_mover:normalized(l,color)}));
   const gates={two_roots:b.lines.length>1,raw_offer:raw,ec_or_mate_corroboration:!!(broad||searchedMate||mateAcceptance),
    quality:loss<=5,after_floor:next>=-100,phase_safe_alternative:!(phaseRelevant&&safe.length),checked_continuation:!continuation};
   const previous=p?.lines[0],prior=previous?normalized(previous,color):null;
   return {complete:true,gates,all_gates_pass:Object.values(gates).every(Boolean),failed_gates:Object.entries(gates).filter(([,pass])=>!pass).map(([k])=>k),
    before_depth:b.depth,after_depth:a.depth,previous_depth:p?.depth,best_cp_mover:best,after_cp_mover:next,loss_pp:loss,
    previous_own_after_cp_mover:prior,previous_explicit_winning_mate:previous?.mate!==undefined&&prior!==null&&prior>0,
    previous_score:previous?{cp:previous.cp,mate:previous.mate}:null,
    before_minus_previous_cp:prior===null?null:best-prior,after_minus_previous_cp:prior===null?null:next-prior,
    prior600_veto:prior!==null&&prior>=600,safe_alternatives:safe,
    raw_ec_annotation:annotation(previous,b,a.lines[0],color,t.uci,broad)};
  };
  const current=window(reviews[n-2].current,reviews[n-1].current,n>2?reviews[n-3].current:undefined);
  const previous=window(reviews[n-2].previous,reviews[n-1].terminal?reviews[n-1].current:reviews[n-1].previous,n>2?reviews[n-3].previous:undefined);
  const sufficient=reviews[n-2].quality===reviews[n-1].quality;

 return {raw_offer:raw,ec_sacrifice:broad,mate_acceptance:mateAcceptance,phase_context_relevant:phaseRelevant,checked_continuation:continuation,current,previous,confidence_sufficient:sufficient,ec_material:snaps.map((s:any)=>material(s.fen))};
}
const input=JSON.parse(fs.readFileSync(0,'utf8'));const output=input.map(semanticContext);process.stdout.write(JSON.stringify(output));
