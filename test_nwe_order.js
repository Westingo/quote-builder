// Test the actual editor ordering functions without starting Word or a browser.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/static/index.html','utf8');
function extract(name){
  const start=source.indexOf('function '+name+'(');
  const end=source.indexOf('\nfunction ',start+1);
  return source.slice(start,end);
}
const boxes={N:[],W:[],E:[]};
for(const key of ['N','W','E'])for(const n of [1,2,6])boxes[key].push({value:(key==='E'?'EX':key)+n,checked:false,dataset:{description:key+' wording '+n}});
const context=vm.createContext({
  NWE_ORDER:{N:[],W:[],E:[]},renderFree(){},buildChecklists(){},
  $:selector=>({querySelectorAll:()=>boxes[selector.slice(-1)]})
});
for(const name of ['selectNWE','collectNWE','removeNWE','applyNWE','moveNWE','dropNWE'])vm.runInContext(extract(name),context);
for(const key of ['N','W','E']){
  for(const n of [2,1,6]){const cb=boxes[key].find(c=>c.value.endsWith(n));cb.checked=true;context.selectNWE(key,cb);}
  assert.deepEqual(Array.from(context.collectNWE(key),x=>x.code),[2,1,6].map(n=>(key==='E'?'EX':key)+n));
}
context.removeNWE('W',1);
const w1=boxes.W[0];w1.checked=true;context.selectNWE('W',w1);
assert.deepEqual(Array.from(context.collectNWE('W'),x=>x.code),['W2','W6','W1']);
const imported=['W2',{text:'Custom warranty'},'W1','W6'];
context.NWE_ORDER.W=[];context.applyNWE('W',imported);
assert.deepEqual(Array.from(context.collectNWE('W'),x=>x.code||x.text),['W2','Custom warranty','W1','W6']);
const saved=context.collectNWE('W');context.NWE_ORDER.W=[];context.applyNWE('W',saved);
assert.deepEqual(Array.from(context.collectNWE('W'),x=>x.code||x.text),['W2','Custom warranty','W1','W6']);
context.NWE_ORDER.W=[];context.applyNWE('W',[{code:'W2',text:'Older saved wording'},'W1']);
assert.deepEqual(Array.from(context.collectNWE('W'),x=>x.text),['Older saved wording','W wording 1']);
for(const key of ['N','W','E']){
  context.NWE_ORDER[key]=[{code:'second'},{text:'custom'},{code:'first'}];
  context.moveNWE(key,2,0);
  assert.deepEqual(Array.from(context.collectNWE(key),x=>x.code||x.text),['first','second','custom']);
  context.moveNWE(key,0,3);
  assert.deepEqual(Array.from(context.collectNWE(key),x=>x.code||x.text),['second','custom','first']);
  context.moveNWE(key,1,2); // Dropping onto itself leaves the order alone.
  context.moveNWE(key,-1,0);
  assert.deepEqual(Array.from(context.collectNWE(key),x=>x.code||x.text),['second','custom','first']);
  const reordered=context.collectNWE(key);
  context.NWE_ORDER[key]=[];context.applyNWE(key,reordered);
  assert.deepEqual(Array.from(context.collectNWE(key),x=>x.code||x.text),['second','custom','first']);
}
context.endNWEDrag=()=>{context.NWE_DRAG=null;};
const dropEvent={clientX:75,preventDefault(){},currentTarget:{getBoundingClientRect:()=>({left:0,width:100})}};
context.NWE_DRAG={key:'W',index:0};
context.dropNWE(dropEvent,'N',2); // Other sections cannot accept this item.
assert.equal(context.NWE_DRAG.key,'W');
context.dropNWE(dropEvent,'W',2); // Right half inserts after the target.
assert.deepEqual(Array.from(context.collectNWE('W'),x=>x.code||x.text),['custom','first','second']);
context.NWE_DRAG={key:'W',index:2};dropEvent.clientX=25;
context.dropNWE(dropEvent,'W',0); // Left half inserts before the target.
assert.deepEqual(Array.from(context.collectNWE('W'),x=>x.code||x.text),['second','custom','first']);
console.log('Passed: selection/import order, reorder both directions, drop placement, section boundaries, custom text, saved round-trip.');
