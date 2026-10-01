const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
function extract(name){const a=html.indexOf('function '+name+'(');return html.slice(a,html.indexOf('\nfunction ',a+1));}
let lines;
const ctx=vm.createContext({findLines:()=>({lines}),redraw(){},applyFills:ln=>ln._desc.replace('_',ln.fills[0])});
for(const name of ['changeNoteType','cleanLine'])vm.runInContext(extract(name),ctx);
for(const from of ['item','sub','atqty','leftnote','priced'])for(const to of ['item','sub','atqty','leftnote','priced']){
  const note=from==='priced'?{amount_note:'Keep exact wording'}:{text:'Keep exact wording',...(from==='item'?{qty:1}:{[from]:true})};
  note.amount='15%';lines=[{text:'Before'},note,{text:'After'}];
  ctx.changeNoteType('gate',1,to);
  assert.equal(lines[1],note);assert.equal(note.amount,'15%');
  assert.equal(to==='priced'?note.amount_note:note.text,'Keep exact wording');
  for(const flag of ['sub','atqty','leftnote'])assert.equal(note[flag],flag===to?true:undefined);
  assert.equal(note.amount_note,to==='priced'?'Keep exact wording':undefined);
  const exported=ctx.cleanLine(note);
  assert.equal(exported.amount,'15%');assert.equal(to==='priced'?exported.amount_note:exported.text,'Keep exact wording');
  assert.equal(lines[0].text,'Before');assert.equal(lines[2].text,'After');
}
lines=[{amount_note:''}];ctx.changeNoteType('option',0,'leftnote');assert.equal(lines[0].text,'');
const saved=JSON.stringify(lines);ctx.changeNoteType('option',0,'unknown');assert.equal(JSON.stringify(lines),saved);
lines=[{code:'CODE',_desc:'Surface mounted _',fills:['outside'],qty:1,amount:'25',format:{start:'left',wrap:'start',align:'right',bold:true,amount_align:'top'}}];
ctx.changeNoteType('gate',0,'sub');
assert.equal(lines[0].text,'Surface mounted outside');
assert.equal(lines[0].sub,true);
assert.equal(lines[0].format.start,undefined);
assert.equal(lines[0].format.bold,true);
assert.equal(lines[0].format.amount_align,'top');
assert.equal(ctx.cleanLine(lines[0]).sub,true);
ctx.changeNoteType('gate',0,'item');
assert.equal(lines[0].code,'CODE');assert.equal(lines[0].qty,1);
assert.equal(lines[0].text,'Surface mounted outside');assert.equal(lines[0].amount,'25');
console.log('Passed all 25 item/note conversions, resolved code wording, formatting, amounts, export, empty notes and invalid type.');
