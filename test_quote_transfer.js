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
  buildChecklists(){},renderSummary(){},renderGates(){},renderOptions(){},renderFree(){},schedulePreview(){},
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
const job={slug:'liv-imported-2',proposal:{for:'Liv customer',ccb:'CUSTOM',cc:'CUSTOM-CC'},
  gate_summary:['Second','First'],gates:[{title:'Gate A',lines:[
    {code:'retired',sheet:'Old',text:'Liv’s exact wording',qty:2,amount:'100'},
    {text:'Note',atqty:true}, {amount_note:'By others',amount:'Excluded'}]}],
  options:[{kind:'block',title:'Option',bullets:['First','Second'],priced:[{label:'Single',amount:'50'}]}],
  notes:[{text:'Custom note'}],warranties:[],exclusions:[],total:'123'};
job.gates[0].format={page_break:true,font_size:9};
job.gates[0].lines[0].format={amount_align:'top',bold:true};
job.gates[0].lines[1].format={start:'left',wrap:'start'};
job.options.push({title:'Detailed',format:{keep_together:true},lines:[{text:'Multi\nline',qty:1,format:{underline:true}}]});
context.loadJobObject(job);
const exported=JSON.parse(JSON.stringify(context.collect()));
assert.equal(exported.slug,job.slug);
assert.equal(exported.proposal.ccb,'CUSTOM');
assert.equal(exported.proposal.cc,'CUSTOM-CC');
for(const key of ['gates','gate_summary','options','notes','warranties','exclusions','total'])assert.deepEqual(exported[key],job[key]);
context.loadJobObject({});
assert.equal(context.activeSlug,'');
assert.equal(context.collect().proposal.ccb,'46091');
console.log('Passed: imported save identity, editor round-trip, custom wording, license fields and reset.');
