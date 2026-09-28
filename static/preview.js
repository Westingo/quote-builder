// Preview images come directly from the actual DOCX rendered by Word.
let previewTimer, previewVersion=0, previewBusy=false, previewLastPayload='', previewDesiredPayload='';
function schedulePreview(){
  if(!CODES)return;
  const payload=JSON.stringify(collect());
  if(payload===previewDesiredPayload && !document.getElementById('preview-retry').hidden)return updatePreview();
  if(payload===previewDesiredPayload)return;
  previewDesiredPayload=payload;
  previewVersion++;
  clearTimeout(previewTimer);
  document.getElementById('preview-status').textContent='Changes pending — rendering Word pages…';
  document.getElementById('preview-paper').classList.add('pv-stale');
  previewTimer=setTimeout(updatePreview,900);
}
async function updatePreview(){
  if(previewBusy)return; // The in-flight request will start the latest draft next.
  const payload=JSON.stringify(collect()), version=previewVersion;
  if(payload===previewLastPayload){
    document.getElementById('preview-paper').classList.remove('pv-stale');
    document.getElementById('preview-status').textContent='Preview up to date';return;
  }
  previewBusy=true;
  try{
    const response=await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:payload});
    const result=await response.json();
    if(version!==previewVersion)return;
    if(!response.ok||!result.ok)throw new Error(result.error||'Preview unavailable. Click Retry.');
    const paper=document.getElementById('preview-paper');
    const fragment=document.createDocumentFragment();
    result.pages.forEach((page,index)=>{
      const figure=document.createElement('figure');figure.className='word-page';
      const image=document.createElement('img');image.src=page.image;
      image.width=page.width;image.height=page.height;
      image.alt='Proposal page '+(index+1)+' of '+result.pages.length;
      const caption=document.createElement('figcaption');caption.textContent=image.alt;
      figure.append(caption,image);fragment.append(figure);
    });
    const scroll=document.getElementById('preview-scroll'),top=scroll.scrollTop;
    paper.replaceChildren(fragment);scroll.scrollTop=top;
    previewLastPayload=payload;
    paper.classList.remove('pv-stale');
    document.getElementById('preview-status').textContent='Up to date · '+result.pages.length+' page'+(result.pages.length===1?'':'s')+' · rendered by Microsoft Word';
    document.getElementById('preview-retry').hidden=true;
  }catch(error){
    if(version!==previewVersion)return;
    document.getElementById('preview-status').textContent=error.message;
    document.getElementById('preview-retry').hidden=false;
  }finally{
    previewBusy=false;
    if(version!==previewVersion){clearTimeout(previewTimer);previewTimer=setTimeout(updatePreview,300);}
  }
}
function openPreview(){
  const dialog=document.getElementById('preview-dialog');
  dialog.append(document.getElementById('preview-panel'));
  document.getElementById('preview-expand').hidden=true;
  document.getElementById('preview-close').hidden=false;
  document.body.style.overflow='hidden';dialog.showModal();
  document.getElementById('preview-close').focus();
}
function closePreview(){document.getElementById('preview-dialog').close();}
document.getElementById('preview-dialog').addEventListener('close',()=>{
  document.getElementById('preview-home').append(document.getElementById('preview-panel'));
  document.getElementById('preview-expand').hidden=false;
  document.getElementById('preview-close').hidden=true;
  document.body.style.overflow='';document.getElementById('preview-expand').focus();
});
const previewEditor=document.getElementById('quote-editor');
for(const event of ['input','change','click','keydown'])previewEditor.addEventListener(event,schedulePreview);
// Covers async scan/import/load and programmatic list redraws, including removals.
new MutationObserver(schedulePreview).observe(previewEditor,{childList:true,subtree:true});
init().then(schedulePreview).catch(()=>{
  document.getElementById('preview-status').textContent='Could not load products. Reopen the app to retry.';
});
