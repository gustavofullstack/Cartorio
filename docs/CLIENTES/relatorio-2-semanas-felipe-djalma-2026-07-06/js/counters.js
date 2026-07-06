/* ===========================================================
   counters.js — Animated KPI counters (IntersectionObserver)
   =========================================================== */

(function(){
  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

  const formatBR = (v) => {
    if (Number.isInteger(v)) return v.toLocaleString('pt-BR');
    return v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  };

  const animate = (el) => {
    const target = parseFloat(el.dataset.counter || '0');
    const dur = 1400;
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / dur);
      const v = target * easeOutCubic(t);
      el.textContent = formatBR(v);
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = formatBR(target);
    };
    requestAnimationFrame(step);
  };

  if ('IntersectionObserver' in window){
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animate(entry.target);
        io.unobserve(entry.target);
      });
    }, { threshold: 0.3 });
    document.querySelectorAll('[data-counter]').forEach((el) => io.observe(el));
  } else {
    document.querySelectorAll('[data-counter]').forEach(animate);
  }
})();