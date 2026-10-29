// Keep the editing state, including empty rows and cached product descriptions.
// collect() intentionally removes those details for export, so is not a snapshot.
let quoteHistory=[], quoteSnapshot=null, quoteTypingTarget=null;
function snapshotQuote(){
  const fields={};
  document.querySelectorAll('#quote-editor [id^="f-"], #f-formatting-profile').forEach(el=>fields[el.id]=el.type==='checkbox'?el.checked:el.value);
  return JSON.stringify({job:JOB,nwe:NWE_ORDER,fields,gateSeq});
}
function resetQuoteHistory(){
  quoteHistory=[]; quoteTypingTarget=null; quoteSnapshot=snapshotQuote();
  document.getElementById('undo-btn').disabled=true;
}
function recordQuoteChange(typingTarget=null){
  if(quoteSnapshot===null)return;
  const next=snapshotQuote();
  if(next===quoteSnapshot)return;
  if(!typingTarget || typingTarget!==quoteTypingTarget){
    quoteHistory.push(quoteSnapshot);
    if(quoteHistory.length>100)quoteHistory.shift();
  }
  quoteTypingTarget=typingTarget;
  quoteSnapshot=next;
  document.getElementById('undo-btn').disabled=!quoteHistory.length;
}
function undoQuote(){
  if(!quoteHistory.length)return;
  const state=JSON.parse(quoteHistory.pop());
  JOB=state.job; NWE_ORDER=state.nwe; gateSeq=state.gateSeq;
  for(const [id,value] of Object.entries(state.fields)){
    const el=document.getElementById(id);
    if(el.type==='checkbox')el.checked=value;else el.value=value;
  }
  // Rebuild checkmarks without replacing the saved wording or order.
  document.querySelectorAll('.checklist input').forEach(cb=>cb.checked=false);
  for(const key of ['N','W','E']){
    document.querySelectorAll('#cl-'+key+' input').forEach(cb=>{
      const item=NWE_ORDER[key].find(item=>item.code===cb.value);
      if(item){cb.checked=true; cb.dataset.description=item.text;}
    });
  }
  renderSummary(); redraw(); renderFree();
  quoteTypingTarget=null; quoteSnapshot=snapshotQuote();
  document.getElementById('undo-btn').disabled=!quoteHistory.length;
  schedulePreview();
}
// Capture before inline handlers, then snapshot after they finish. This also
// covers controls in the product picker and formatting dialog, and drag/drop.
for(const type of ['input','change','click','keydown','drop','submit']){
  document.addEventListener(type,event=>{
    if(event.target.closest?.('#undo-btn'))return;
    const typing=type==='input' && event.target.matches('input:not([type="checkbox"]),textarea');
    queueMicrotask(()=>recordQuoteChange(typing?event.target:null));
  },true);
}
document.addEventListener('focusout',()=>{quoteTypingTarget=null;},true);
