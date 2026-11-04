// One-feature semantic correction: invoke the original bounded mating helper for every case.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { hasMatingAcceptance } from '../brilliants-improvement-2026-11-03/root/frozen-v4/noSweatClassify.ts';

const here=path.dirname(fileURLToPath(import.meta.url));
const sha=(p:string)=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const write=(name:string,value:any)=>fs.writeFileSync(path.join(here,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const protocol=JSON.parse(fs.readFileSync(path.join(here,'EXTRACTION-PROTOCOL.json'),'utf8'));
if(sha(fileURLToPath(import.meta.url))!==protocol.script_sha256)throw Error('Script hash mismatch');
for(const [p,digest] of Object.entries(protocol.source_sha256))if(sha(p)!==digest)throw Error('Source hash mismatch '+p);
for(const n of ['FEATURES.json','EXTRACTION.json'])if(fs.existsSync(path.join(here,n)))throw Error('Refuse overwrite '+n);
const data=JSON.parse(fs.readFileSync(protocol.input_path,'utf8'));
if(data.cases.length!==3724)throw Error('Expected3724');
const start=performance.now();
const features:Record<string,boolean>={};
const changes:any[]=[];
let countTrue=0,oldTrue=0,eligibleChanges=0;
for(const c of data.cases){
  if(performance.now()-start>180000)throw Error('180second bound; no outcome retry');
  const f=c.windows.current.features,prev=c.windows.previous.features;
  if(f.ec_sacrifice!==prev.ec_sacrifice || f.mating_acceptance!==prev.mating_acceptance)throw Error('Unexpected window disagreement');
  const corrected=hasMatingAcceptance(c.fen_before,c.fen_after);
  const expectedOld=!f.ec_sacrifice && corrected;
  if(expectedOld!==f.mating_acceptance)throw Error('Original masked feature parity failed '+c.key);
  if(features[c.key]!==undefined)throw Error('Duplicate key');
  features[c.key]=corrected;
  countTrue+=Number(corrected);oldTrue+=Number(f.mating_acceptance);
  if(corrected!==f.mating_acceptance){
    if(!f.ec_sacrifice || !corrected)throw Error('Not an EC unmasking');
    const eligible=c.windows.current.eligible && c.windows.previous.eligible && c.confidence_sufficient &&
      !f.physical_unknown && !prev.physical_unknown;
    eligibleChanges+=Number(eligible);
    changes.push({key:c.key,old:false,corrected:true,eligible});
  }
}
// This pass uses positions and original features only; labels never select extraction.
write('FEATURES.json',features);
write('EXTRACTION.json',{status:'complete',input_sha256:sha(protocol.input_path),
  feature_sha256:sha(path.join(here,'FEATURES.json')),
  protocol_sha256:sha(path.join(here,'EXTRACTION-PROTOCOL.json')),
  script_sha256:sha(fileURLToPath(import.meta.url)),
  counts:{cases:3724,old_true:oldTrue,corrected_true:countTrue,changed:changes.length,eligible_changed:eligibleChanges,
    masked_original_parity:3724,new_engine_queries:0},elapsed_seconds:(performance.now()-start)/1000,changes,
  semantics:'Original hasMatingAcceptance unchanged, called independently of EC on every case; literal legal immediate mate after a qualifying nonpawn acceptance. Existing512proof budget/false-on-exhaustion semantics retained. Same boolean in both windows.'});
console.log(JSON.stringify({cases:3724,old_true:oldTrue,corrected_true:countTrue,changed:changes.length,eligible_changed:eligibleChanges,
  elapsed_seconds:(performance.now()-start)/1000}));
