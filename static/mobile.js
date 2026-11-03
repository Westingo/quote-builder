/* Move existing controls, preserving handlers and values across rotations. */
(() => {
  const header=document.querySelector('header');
  const toggle=document.getElementById('mobile-tools');
  toggle.addEventListener('click',()=>{
    const expanded=header.classList.toggle('mobile-tools-open');
    toggle.setAttribute('aria-expanded',String(expanded));
  });
  const bar=document.getElementById('quote-buildbar');
  const menu=bar.querySelector('.file-menu');
  const controls=[...bar.children].filter(el=>
    el.id==='jobs' || (el.tagName==='BUTTON' && !el.classList.contains('mobile-only') && !el.classList.contains('primary')));
  const slots=controls.map(el=>{
    const marker=document.createComment('desktop action');
    el.before(marker);return marker;
  });
  const media=window.matchMedia('(max-width:760px)');
  function arrange(){
    controls.forEach((el,i)=>{if(media.matches)menu.append(el);else slots[i].after(el);});
    document.getElementById('file-actions').open=false;
  }
  media.addEventListener('change',arrange);arrange();
  const bars=[...document.querySelectorAll('.buildbar')];
  const observer=new ResizeObserver(()=>{
    const height=Math.max(...bars.map(el=>el.getBoundingClientRect().height));
    document.documentElement.style.setProperty('--mobile-bar-height',height+'px');
  });
  bars.forEach(el=>observer.observe(el));
})();
