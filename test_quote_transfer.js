// Exercise the actual editor load/export path, including imported save identity.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/static/index.html','utf8');
function extract(name){
  const start=source.indexOf('function '+name+'(');
  return source.slice(start,source.indexOf('\nfunction ',start+1));
}
const fields={};
const context=vm.createContext({
  JOB:{}, activeSlug:'',gateSeq:0,NWE_ORDER:{},
  $:s=>fields[s]??=( {value:''} ),
  document:{querySelectorAll:()=>[]},
  descOf:()=> 'Different wording on this computer',
  buildChecklists(){},renderSummary(){},renderGates(){},renderOptions(){},renderFree(){},schedulePreview(){},resetQuoteHistory(){},
  applyNWE:(key,arr)=>context.NWE_ORDER[key]=arr||[],
  collectNWE:key=>context.NWE_ORDER[key],
  applyFills:line=>line._desc,
});
for(const name of ['titleFor','collect','dropEmptySubs','cleanLine','cleanOption','loadJobObject']){
  let code=extract(name);
  // loadJobObject is followed by async transfer handlers; isolate its closing brace.
  if(name==='loadJobObject')code=code.slice(0,code.indexOf('\nasync function'));
  vm.runInContext(code,context);
}
const job={slug:'liv-imported-2',proposal:{cmi:true,for:'Liv customer',ccb:'CUSTOM',cc:'CUSTOM-CC'},
  gate_summary:['Second','First'],gates:[{title:'Gate A',lines:[
    {code:'retired',sheet:'Old',text:'Liv’s exact wording',qty:2,amount:'100'},
    {text:'Note',atqty:true}, {amount_note:'By others',amount:'Excluded'}]}],
  options:[{kind:'block',title:'Option',bullets:['First','Second'],priced:[{label:'Single',amount:'50'}]}],
  notes:[{text:'Custom note'}],warranties:[],exclusions:[],total:'123'};
job.gates[0].format={page_break:true,font_size:9};
job.summary_text='Project detail\nSecond line';
job.summary_text_format={italic:true,align:'center',space_before:12};
job.gates[0].lines[0].format={amount_align:'top',bold:true};
job.gates[0].lines[1].format={start:'left',wrap:'start'};
job.options.push({title:'Detailed',format:{keep_together:true},lines:[{text:'Multi\nline',qty:1,format:{underline:true}}]});
context.loadJobObject(job);
const exported=JSON.parse(JSON.stringify(context.collect()));
assert.equal(exported.proposal.cmi,true);
assert.equal(exported.summary_text,job.summary_text);
assert.deepEqual(exported.summary_text_format,job.summary_text_format);
assert.equal(exported.slug,job.slug);
assert.equal(exported.proposal.ccb,'CUSTOM');
assert.equal(exported.proposal.cc,'CUSTOM-CC');
for(const key of ['gates','gate_summary','options','notes','warranties','exclusions','total'])assert.deepEqual(exported[key],job[key]);
context.loadJobObject({});
assert.equal(context.activeSlug,'');
assert.equal(context.collect().summary_text_format,undefined);
assert.equal(fields['#f-cmi'].checked,false);
assert.equal(context.collect().proposal.cmi,undefined);
assert.equal(context.collect().summary_text,'');
assert.equal(context.collect().proposal.ccb,'46091');
console.log('Passed: imported save identity, editor round-trip, custom wording, license fields and reset.');

// Attach to an identity, reorder locations, save/reload, then remove the parent.
context.redraw=()=>{};context.renderOptions=()=>{};context.scrollToOption=()=>{};
for(const name of ['assignOption','removeGate','reorderList','reorderAt'])vm.runInContext(extract(name),context);
context.loadJobObject({...job,gates:[...job.gates,{title:'Gate B',lines:[]}]});
context.assignOption(0,context.JOB.gates[0].id);
context.reorderAt('gates',0,2);
let grouped=JSON.parse(JSON.stringify(context.collect()));
assert.equal(grouped.gates[1].title,'Gate A');
assert.deepEqual(grouped.gates[1].options,[job.options[0]]);
assert.deepEqual(grouped.options,[job.options[1]]);
context.loadJobObject(grouped);
assert.deepEqual(JSON.parse(JSON.stringify(context.collect())).gates,grouped.gates);
context.removeGate(context.JOB.gates[1].id);
assert.equal(context.collect().options.length,2);
assert.deepEqual(JSON.parse(JSON.stringify(context.collect().options[1])),job.options[0]);
console.log('Passed: option association follows location reorder, survives reload, and returns to general when location is removed.');
