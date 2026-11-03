(() => {
  if('serviceWorker' in navigator && window.isSecureContext){
    navigator.serviceWorker.register('/sw.js').catch(()=>{
      // Normal browser editing remains available if installation is unavailable.
    });
  }
  const button=document.getElementById('install-qb');
  let prompt;
  window.addEventListener('beforeinstallprompt',event=>{
    event.preventDefault();prompt=event;button.hidden=false;
  });
  button.addEventListener('click',async()=>{
    if(!prompt)return;
    await prompt.prompt();await prompt.userChoice;prompt=null;button.hidden=true;
  });
  window.addEventListener('appinstalled',()=>{prompt=null;button.hidden=true;});
  const connection=document.getElementById('connection-status');
  function updateConnection(){connection.hidden=navigator.onLine;}
  window.addEventListener('online',updateConnection);
  window.addEventListener('offline',updateConnection);
  updateConnection();
})();
