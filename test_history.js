const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const field={id:'f-for',value:'Original'},button={disabled:true},listeners={};
const ctx=vm.createContext({
  JOB:{gate_summary:[''],gates:[{id:'g1',lines:[{text:'',sub:true},{code:'6',_desc:'Saved wording',qty:2}]}],options:[]},
  NWE_ORDER:{N:[{text:'Custom note'}],W:[],E:[]},gateSeq:1,
  document:{querySelectorAll:s=>s.startsWith('#quote-editor')?[field]:[],
    getElementById:id=>id==='undo-btn'?button:field,
    addEventListener:(type,fn)=>listeners[type]=fn},
  renderSummary(){},redraw(){},renderFree(){},schedulePreview(){},queueMicrotask:fn=>fn(),
});
vm.runInContext(fs.readFileSync(__dirname+'/static/history.js','utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
ctx.resetQuoteHistory();
run('JOB.options.push({text:"New"});recordQuoteChange()');
assert.equal(button.disabled,false);
run('JOB.gates[0].lines.splice(0,1);recordQuoteChange()');
ctx.undoQuote();assert.equal(ctx.JOB.gates[0].lines.length,2);
assert.equal(ctx.JOB.gates[0].lines[1]._desc,'Saved wording');
ctx.undoQuote();assert.equal(ctx.JOB.options.length,0);assert.equal(button.disabled,true);
field.value='A';ctx.recordQuoteChange(field);field.value='AB';ctx.recordQuoteChange(field);
ctx.undoQuote();assert.equal(field.value,'Original');assert.equal(button.disabled,true);
run('NWE_ORDER.N.push({code:"N1",text:"Exact note"});recordQuoteChange()');
ctx.undoQuote();assert.equal(ctx.NWE_ORDER.N.length,1);
run('JOB.options.push({text:"Other quote"});resetQuoteHistory()');
ctx.undoQuote();assert.equal(ctx.JOB.options.length,1);assert.equal(button.disabled,true);
for(let i=0;i<110;i++){field.value=String(i);ctx.recordQuoteChange();}
assert.equal(run('quoteHistory.length'),100);
// Every option type reveals its actual insertion position and focuses the card.
const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
let revealed;
const options=vm.createContext({JOB:{options:[]},gateSeq:0,renderOptions(){},scrollToOption:i=>revealed=i});
for(const name of ['addOption','addDetailOption','addLowVoltage','addCleanup']){
  const start=html.indexOf('function '+name+'(');
  vm.runInContext(html.slice(start,html.indexOf('\nfunction ',start+1)),options);
  options[name]();assert.equal(revealed,name==='addDetailOption'?1:0);
}
console.log('Passed undo additions, removal with empty rows, cached wording, typing grouping, notes, quote reset, history limit and all option insertion targets.');

field.type='checkbox';field.checked=false;ctx.resetQuoteHistory();
field.checked=true;ctx.recordQuoteChange();ctx.undoQuote();
assert.equal(field.checked,false);
console.log('Passed checkbox undo.');
