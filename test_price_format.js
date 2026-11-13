const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/static/index.html','utf8');
function extract(name){const a=source.indexOf('function '+name+'(');return source.slice(a,source.indexOf('\nfunction ',a+1));}
const target={text:'Original',amount:'100',format:{font_size:9,bold:true}};
const dialog={close(){}};
const ctx=vm.createContext({formatTarget:{target,index:0,price:true},$:()=>dialog,redraw(){},schedulePreview(){},applyFills:()=>''});
for(const name of ['saveFormatting','resetFormatting','cleanLine'])vm.runInContext(extract(name),ctx);
ctx.saveFormatting({elements:[{name:'font_size',type:'number',value:'14'},{name:'bold',type:'select-one',value:'false'},{name:'italic',type:'select-one',value:'true'}]});
assert.equal(target.price_format.font_size,14);assert.equal(target.price_format.bold,false);assert.equal(target.price_format.italic,true);
assert.equal(target.text,'Original');assert.equal(target.format.font_size,9);
for(const kind of [{text:'Item'},{code:'X',text:'Coded'},{text:'Note',sub:true},{text:'Note',atqty:true},{text:'Note',leftnote:true},{text:'Header',header:true},{amount_note:'Priced'}]){
  const clean=ctx.cleanLine({...kind,price_format:target.price_format});
  assert.equal(clean.price_format,target.price_format);
}
ctx.resetFormatting();assert.equal(target.price_format,undefined);assert.equal(target.format.font_size,9);
for(const script of source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(script[1]);
console.log('Passed price-only edits, explicit bold off, persistence for every line type, reset isolation, and editor syntax.');
