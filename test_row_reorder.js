const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
const JOB={gates:[{id:'g1',lines:[{text:'A',qty:2},{text:'B',sub:true},{amount_note:'C',amount:'50'}]},{id:'g2',lines:[]}],options:[{id:'o1',lines:[{text:'X'},{text:'Y'}]},{text:'Other'}]};
const ctx=vm.createContext({JOB,redraw(){},findLines:id=>[...JOB.gates,...JOB.options].find(x=>x.id===id)});
for(const name of ['reorderList','reorderAt']){const a=html.indexOf('function '+name+'(');vm.runInContext(html.slice(a,html.indexOf('\nfunction ',a+1)),ctx);}
for(const group of ['gates','options','lines:g1','lines:o1']){
  const items=ctx.reorderList(group),original=[...items];
  ctx.reorderAt(group,0,items.length);assert.equal(items.at(-1),original[0]);
  ctx.reorderAt(group,items.length-1,0);assert.deepEqual(items,original);
  ctx.reorderAt(group,0,1);assert.deepEqual(items,original);
  ctx.reorderAt(group,-1,0);assert.deepEqual(items,original);
}
assert.equal(JOB.gates[0].lines[0].qty,2);assert.equal(JOB.gates[0].lines[2].amount,'50');
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
console.log('Passed location, option and line reorder in both directions, boundaries, retained content and script syntax.');
