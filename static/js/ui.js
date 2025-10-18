
// ui.js — UX helpers
(function(){
  // toast
  const cont = document.createElement('div');
  cont.id = 'toast-container';
  cont.style.cssText = 'position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px;z-index:2000;';
  document.addEventListener('DOMContentLoaded', ()=>document.body.appendChild(cont));
  window.toast = function(msg, type){
    const el = document.createElement('div');
    el.textContent = msg;
    el.setAttribute('role','status');
    el.style.cssText = 'padding:.6rem .8rem;border-radius:10px;background:#15171a;color:#eaeaea;box-shadow:0 8px 28px rgba(0,0,0,.35);border:1px solid #2a2e34;';
    if(type==='success'){ el.style.borderColor = '#34d399'; }
    if(type==='error'){ el.style.borderColor = '#f87171'; }
    cont.appendChild(el); setTimeout(()=>el.remove(), 3000);
  };

  // "/" → фокус глобального поиска
  document.addEventListener('keydown', (e)=>{
    if(e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey){
      const search = document.querySelector('[data-global-search]');
      if(search){ e.preventDefault(); search.focus(); }
    }
    if(e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey){
      e.preventDefault(); window.toast('Быстрые клавиши: "/" — поиск', 'success');
    }
  });

  // lazy images
  document.addEventListener('DOMContentLoaded', ()=>{
    document.querySelectorAll('img:not([loading])').forEach(img=> img.loading = 'lazy');
  });

  // mobile sidebar toggle
  document.addEventListener('click', (e)=>{
    const btn = e.target.closest('.sidebar-toggle');
    if(btn){
      const sb = document.querySelector('.sidebar');
      if(sb){
        const shown = sb.dataset.open === '1';
        sb.style.transform = shown ? 'translateX(-100%)' : 'translateX(0)';
        sb.dataset.open = shown ? '0' : '1';
      }
    }
  });
})();
