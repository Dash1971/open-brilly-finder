async function(tab,t,role,store,fsp){
  if(store.currentGame!==t.game_id){await tab.goto(t.source_link);store.currentGame=t.game_id;}
  let feedbackReady=false;const loadStarted=Date.now();
  while(!feedbackReady && Date.now()-loadStarted<25000){
    try{await tab.playwright.locator('.move-feedback-box-description').waitFor({state:'visible',timeoutMs:5000});feedbackReady=true;}
    catch(error){if(Date.now()-loadStarted>=25000)throw error;await tab.playwright.domSnapshot();}
  }
  if(!feedbackReady)throw Error('Review feedback never appeared');
  let identity=await tab.playwright.evaluate(()=>({san:document.querySelector('.move-feedback-box-move .move-san-san')?.innerText,ply:Number(new URL(location.href).searchParams.get('move'))+1}));
  if(identity.san!==t.san||identity.ply!==t.ply){
    await tab.playwright.locator('.main-line-ply[data-node="0-'+(t.ply-1)+'"]').click();
  }
  const placement=pieces=>{const squares=new Map();for(const cls of pieces||[]){const p=cls.match(/\b([wb][pnbrqk])\b/);const q=cls.match(/\bsquare-([1-8])([1-8])\b/);if(!p||!q)continue;const sq=Number(q[2])-1+','+(Number(q[1])-1);const symbol=p[1][0]==='w'?p[1][1].toUpperCase():p[1][1];if(squares.has(sq))return null;squares.set(sq,symbol);}let rows=[];for(let rank=7;rank>=0;rank--){let row='',blank=0;for(let file=0;file<8;file++){const symbol=squares.get(rank+','+file);if(symbol){if(blank)row+=blank;blank=0;row+=symbol;}else blank++;}if(blank)row+=blank;rows.push(row);}return rows.join('/');};
  let d,lastText=null,stable=0;
  for(let i=0;i<6;i++){
    d=await tab.playwright.evaluate(()=>({
      san:document.querySelector('.move-feedback-box-move .move-san-san')?.innerText,
      displayed_label_text:document.querySelector('.move-feedback-box-description')?.innerText,
      displayed_evaluation:document.querySelector('.move-feedback-box-content a')?.innerText,
      coach_explanation:document.querySelector('.move-feedback-speech-text-component')?.innerText??null,
      coach_pending_hidden_characters:Array.from(document.querySelectorAll('.move-feedback-speech-text-hidden')).reduce((n,e)=>n+(e.textContent?.length||0),0),
      review_board_pieces:Array.from(document.querySelectorAll('wc-chess-board .piece')).map(p=>p.className).sort(),
      observed_page_url:location.href,observed_query_move:new URL(location.href).searchParams.get('move')
    }));
    const correct=placement(d.review_board_pieces)===t.fen_after.split(' ')[0]&&d.san===t.san&&Number(d.observed_query_move)+1===t.ply&&d.observed_page_url.includes('/'+t.game_id+'/review');
    if(correct&&d.coach_explanation===lastText)stable++;else stable=0;
    lastText=d.coach_explanation;
    if(correct&&stable>=1&&d.coach_pending_hidden_characters===0&&/[.!?]\s*$/.test(d.coach_explanation||''))break;
    await new Promise(r=>setTimeout(r,180));
  }
  if(placement(d.review_board_pieces)!==t.fen_after.split(' ')[0]||d.san!==t.san||Number(d.observed_query_move)+1!==t.ply||!d.observed_page_url.includes('/'+t.game_id+'/review'))throw Error('Move identity mismatch '+t.game_id+':'+t.ply);
  const match=d.displayed_label_text?.toLowerCase().match(/brilliant|great|best|excellent|good|book|forced|inaccuracy|mistake|miss|blunder/);
  if(!match)throw Error('No explicit displayed classification '+t.game_id+':'+t.ply);
  const r={...t,...d,label:match[0],source_type:'fresh_review',source_link:d.observed_page_url,captured_at:new Date().toISOString(),account:store.account,categories:[],selected:true,sample_role:role,
    coach_extraction:'Visible DOM innerText only; hidden spans inspected only for pending character count, never copied.',
    coach_completeness:stable>=1&&d.coach_pending_hidden_characters===0&&/[.!?]\s*$/.test(d.coach_explanation||'')?'verified_visible_complete':'partial_or_unverified',
    review_configuration:'Current Chrome Game Review display; no deeper rerun requested; settings unknown unless separately observed.'};
  if(role==='positive_target'&&r.label!=='brilliant'){r.selected=false;r.sample_role='gallery_review_disagreement';}
  if(role==='negative_control'&&r.label==='brilliant'){r.selected=false;r.sample_role='control_candidate_was_brilliant';}
  store.fresh.push(r);store.used.add(r.game_id+':'+r.ply);
  await fsp.writeFile(store.root+'/evidence/'+store.filename,JSON.stringify(store.fresh,null,2));
  return r;
}
