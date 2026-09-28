const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/static/index.html','utf8');
function extract(name){const a=html.indexOf('function '+name+'(');return html.slice(a,html.indexOf('\nfunction ',a+1));}
let lines;
const ctx=vm.createContext({findLines:()=>({lines}),redraw(){}});
for(const name of ['changeNoteType','cleanLine'])vm.runInContext(extract(name),ctx);
for(const from of ['sub','atqty','leftnote','priced'])for(const to of ['sub','atqty','leftnote','priced']){
  const note=from==='priced'?{amount_note:'Keep exact wording'}:{text:'Keep exact wording',[from]:true};
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
console.log('Passed all 16 note conversions, text/amount/export preservation, empty notes and invalid type.');
