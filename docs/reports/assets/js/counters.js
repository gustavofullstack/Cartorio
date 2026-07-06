/* Animate KPI counters when in viewport */
(function() {
  const counters = document.querySelectorAll('.kpi-value[data-target]');

  function animate(el) {
    const target = parseFloat(el.getAttribute('data-target'));
    const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
    const duration = 1200;
    const start = performance.now();
    const isPct = el.hasAttribute('data-suffix-pct');

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      const value = target * eased;
      el.textContent = isPct
        ? value.toFixed(decimals) + '%'
        : decimals === 0
          ? Math.round(value).toLocaleString('pt-BR')
          : value.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animate(entry.target);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    counters.forEach(c => obs.observe(c));
  } else {
    counters.forEach(animate);
  }

  /* Animate progress bars */
  const bars = document.querySelectorAll('.progress-fill[data-target]');
  if ('IntersectionObserver' in window) {
    const obs2 = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.width = entry.target.getAttribute('data-target') + '%';
          obs2.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    bars.forEach(b => obs2.observe(b));
  }
})();