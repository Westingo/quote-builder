/* Separate PM editor; quote form and draft remain mounted when switching tabs. */
(() => {
  const monthNames=['January','February','March','April','May','June','July','August','September','October','November','December'];
  const frequencies={Quarterly:3,Semiannual:6,Annual:12};
  function updateMonths(data){
    if(data.starting_month && data.frequency){
      const start=monthNames.indexOf(data.starting_month),step=frequencies[data.frequency];
      if(start>=0 && step)data.months=Array.from({length:12/step},(_,i)=>monthNames[(start+i*step)%12]).join(', ');
    }else if('starting_month' in data && 'frequency' in data){data.months='';}
  }
  function migrate(data){
    if(!('starting_month' in data)){
      const old=(data.months||'').split(',').map(m=>m.trim()).filter(Boolean);
      data.starting_month='';data.frequency='';
      const frequency=Object.keys(frequencies).find(f=>12/frequencies[f]===old.length);
      if(frequency && old.every((m,i)=>m===monthNames[(monthNames.indexOf(old[0])+i*frequencies[frequency])%12])){
        data.starting_month=old[0];data.frequency=frequency;
      }
    }
    delete data.visit_month;
    return data;
  }
  const fields = [
    ['account','Account number'],['zone','Zone'],['ticket','Ticket number (optional)'],
    ['starting_month','Starting month'],['frequency','Frequency'],['months','Scheduled visit months'],
    ['customer','Customer / site'],['address','Site address',true],['contact','Contact',true],
    ['created','Date created'],['phone','Phone'],['scope','Service / equipment description',true],
    ['checklist','Service checklist (one item per line)',true],['price','Service price ($)'],
    ['notes','Site / access notes',true]
  ];
  const defaultChecklist = [
    'Includes Lubrication, Adjustments and Inspection for Wear',
    'If need for further repairs are found, they will be quoted first',
    'If UL325 required safety warning signs are unreadable or missing, replace at $20/ea',
    'replace batteries on CSL-24v if test fails below 10% of rated value at $32/ea'
  ].join('\n');
  const blank = () => Object.fromEntries(fields.map(([key]) => [key, key==='created' ? new Date().toLocaleDateString('en-US') : key==='checklist' ? defaultChecklist : '']));
  let current=blank(), id='', dirty=false, timer, version=0, imageUrl, busy=false;
  const key='metro-pm-draft-v1';
  try { const saved=JSON.parse(localStorage.getItem(key)); if(saved?.data){current={...current,...migrate(saved.data)};id=saved.id||'';dirty=true;} } catch (_) {}
  const nav=document.createElement('nav'); nav.className='pm-tabs'; nav.setAttribute('aria-label','Document type');
  nav.innerHTML='<button class="btn primary" id="quotes-tab" aria-pressed="true">Quotes</button><button class="btn" id="pm-tab" aria-pressed="false">PM Sheets</button>';
  document.querySelector('header').append(nav);
  const main=document.createElement('main'); main.id='pm-editor'; main.hidden=true;
  main.innerHTML=`<div class="pm-layout"><div><section class="sheet"><h2>PM sheet <span class="muted">New contract setup</span></h2><div class="pad">
    <p class="muted">Create a reusable worksheet for a maintenance contract. Technician fields stay blank for the service visit.</p>
    <div class="pm-actions"><button type="button" class="btn" id="pm-new">New sheet</button><button type="button" class="btn" id="pm-copy">Duplicate</button></div>
    <label for="pm-saved">Saved PM sheets</label><div class="pm-actions"><select id="pm-saved"><option value="">Choose a saved sheet…</option></select><button type="button" class="btn" id="pm-open">Open</button></div>
    <form id="pm-form" class="pm-fields"></form>
    </div></section></div><section class="sheet pm-preview"><h2>Print preview <button class="btn sm" id="pm-refresh">Refresh</button></h2><div class="pad"><p class="muted">Letter size · Matches the existing PM worksheet</p><p id="pm-preview-status" role="status"></p><img id="pm-image" alt="PM worksheet print preview" hidden></div></section></div>
    <div class="buildbar" id="pm-bar"><span id="pm-status" role="status" class="muted"></span><span class="sp"></span><button class="btn" id="pm-save">Save PM sheet</button><button class="btn primary" id="pm-pdf">Build PDF</button></div>`;
  document.querySelector('main').after(main);
  const form=main.querySelector('form');
  for(const [name,label,multi] of fields){
    const wrap=document.createElement('div'); if(multi||name==='months'||name==='customer')wrap.className='pm-wide';
    const l=document.createElement('label'); l.htmlFor='pm-'+name; l.textContent=label;
    const choices=name==='starting_month'?monthNames:name==='frequency'?Object.keys(frequencies):null;
    const input=document.createElement(choices?'select':multi?'textarea':'input'); input.id='pm-'+name;input.name=name;
    if(choices){input.add(new Option('Choose '+label.toLowerCase()+'…',''));for(const choice of choices)input.add(new Option(choice,choice));}
    else if(multi)input.rows=name==='checklist'?5:3;else input.type='text';
    if(name==='months'){input.readOnly=true;input.className='ro';input.placeholder='Choose a starting month and frequency';}
    input.maxLength=5000; input.value=current[name]; wrap.append(l,input);form.append(wrap);
  }
  const $=s=>main.querySelector(s);
  const status=message=>{$('#pm-status').textContent=message;};
  function persist(){try{localStorage.setItem(key,JSON.stringify({id,data:current}));}catch(_){status('Draft could not be stored in this browser. Use Save PM sheet.');}}
  function fill(){for(const [name] of fields)form.elements[name].value=current[name]||'';persist();schedule();}
  function schedule(){clearTimeout(timer);version++;$('#pm-image').style.opacity='.45';timer=setTimeout(preview,450);}
  async function request(url,body){
    const response=await fetch('/api/pm/'+url,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
    if(!response.ok){let message='Request failed ('+response.status+').';try{const e=await response.json();message=e.detail||e.error||message;}catch(_){}throw Error(message);}
    return response;
  }
  async function preview(){const token=version;$('#pm-preview-status').textContent='Updating preview…';try{
    const response=await request('preview',current), blob=await response.blob();if(token!==version)return;
    if(imageUrl)URL.revokeObjectURL(imageUrl);imageUrl=URL.createObjectURL(blob);$('#pm-image').src=imageUrl;$('#pm-image').hidden=false;$('#pm-image').style.opacity='1';$('#pm-preview-status').textContent='One page · Ready to print';
  }catch(e){if(token===version){$('#pm-preview-status').textContent=e.message;$('#pm-image').hidden=true;}}}
  async function list(){try{const rows=await (await request('sheets')).json();const select=$('#pm-saved');select.replaceChildren(new Option('Choose a saved sheet…',''));for(const row of rows)select.add(new Option(row.customer+(row.account?' — #'+row.account:''),row.id));select.value=id;}catch(e){status(e.message);}}
  async function save(){const data={...current};const result=await (await request('sheets',{...data,id})).json();id=result.id;dirty=JSON.stringify(data)!==JSON.stringify(current);persist();await list();status(dirty?'Saved. Newer edits are still unsaved.':'PM sheet saved.');}
  function okay(){return !dirty||confirm('Replace this PM draft? Save PM sheet first to keep these changes.');}
  function action(fn){return async()=>{if(busy)return;busy=true;$('#pm-save').disabled=$('#pm-pdf').disabled=true;try{await fn();}catch(e){status(e.message);}finally{busy=false;$('#pm-save').disabled=$('#pm-pdf').disabled=false;}};}
  form.addEventListener('submit',e=>e.preventDefault());
  form.addEventListener('input',e=>{current[e.target.name]=e.target.value;if(['starting_month','frequency'].includes(e.target.name)){updateMonths(current);form.elements.months.value=current.months;}dirty=true;status('Unsaved changes · draft kept on this computer');persist();schedule();});
  $('#pm-new').onclick=()=>{if(okay()){current=blank();id='';dirty=false;fill();status('New PM sheet');$('#pm-saved').value='';}};
  $('#pm-copy').onclick=()=>{id='';dirty=true;persist();$('#pm-saved').value='';status('Duplicate ready — saving creates a separate PM sheet.');};
  $('#pm-open').onclick=action(async()=>{const selected=$('#pm-saved').value;if(!selected||!okay())return;current=migrate(await(await request('sheets/'+selected)).json());id=selected;dirty=false;fill();status('PM sheet opened.');});
  $('#pm-save').onclick=action(save);
  $('#pm-pdf').onclick=action(async()=>{
    const data={...current};if(!data.customer.trim())throw Error('Enter a customer / site before building.');
    status('Building PDF…');
    if(window.pywebview?.api?.save_pm_pdf){const saved=await window.pywebview.api.save_pm_pdf(data);status(saved?'PDF saved.':'PDF save canceled.');}
    else{const response=await request('pdf',data);const blob=await response.blob(),url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=(data.customer.replace(/[^a-z0-9-]/gi,'-')||'worksheet')+'-PM.pdf';link.click();setTimeout(()=>URL.revokeObjectURL(url),60000);status('PDF downloaded.');}
  });
  $('#pm-refresh').onclick=()=>{version++;preview();};
  const quoteMain=document.querySelector('main'),quoteBar=document.querySelector('body > .buildbar');
  function tab(pm){
    main.hidden=!pm;quoteMain.hidden=pm;quoteBar.hidden=pm;document.body.classList.toggle('pm-active',pm);
    for(const [name,on] of [['pm-tab',pm],['quotes-tab',!pm]]){const button=document.getElementById(name);button.classList.toggle('primary',on);button.setAttribute('aria-pressed',String(on));}
    if(pm){list();schedule();}
  }
  document.getElementById('pm-tab').onclick=()=>tab(true);
  document.getElementById('quotes-tab').onclick=()=>tab(false);
})();
