
(function(){
  const key = "admin-theme";
  function apply(t){
    document.body.classList.remove("theme-light","theme-dark");
    document.body.classList.add(t);
  }
  const saved = localStorage.getItem(key) || "theme-dark";
  apply(saved);
  window.toggleTheme = function(){
    const cur = document.body.classList.contains("theme-dark") ? "theme-dark" : "theme-light";
    const next = (cur === "theme-dark") ? "theme-light" : "theme-dark";
    apply(next); localStorage.setItem(key, next);
  };
})();
