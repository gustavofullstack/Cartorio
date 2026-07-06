/* ===========================================================
   charts.js — Donut chart + bar chart helpers
   =========================================================== */

(function(){
  // --- Donut chart ---
  const renderDonut = (svg, data) => {
    const size = 200;
    const radius = 80;
    const stroke = 22;
    const cx = size / 2;
    const cy = size / 2;
    const circumference = 2 * Math.PI * radius;
    let offset = 0;
    const total = data.reduce((acc, d) => acc + d.value, 0);

    svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
    svg.setAttribute('width', '200');
    svg.setAttribute('height', '200');

    // Background ring
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    bg.setAttribute('cx', cx); bg.setAttribute('cy', cy);
    bg.setAttribute('r', radius);
    bg.setAttribute('fill', 'none');
    bg.setAttribute('stroke', '#f5f5f7');
    bg.setAttribute('stroke-width', stroke);
    svg.appendChild(bg);

    // Segments
    data.forEach((d) => {
      const seg = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      const len = (d.value / total) * circumference;
      seg.setAttribute('cx', cx); seg.setAttribute('cy', cy);
      seg.setAttribute('r', radius);
      seg.setAttribute('fill', 'none');
      seg.setAttribute('stroke', d.color);
      seg.setAttribute('stroke-width', stroke);
      seg.setAttribute('stroke-dasharray', `${len} ${circumference - len}`);
      seg.setAttribute('stroke-dashoffset', -offset);
      seg.setAttribute('transform', `rotate(-90 ${cx} ${cy})`);
      seg.setAttribute('stroke-linecap', 'butt');
      svg.appendChild(seg);
      offset += len;
    });

    // Center text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', cx); text.setAttribute('y', cy + 6);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('font-family', 'Poppins, sans-serif');
    text.setAttribute('font-weight', '700');
    text.setAttribute('font-size', '32');
    text.setAttribute('fill', '#0a0a0a');
    text.textContent = data[0].label || '';
    svg.appendChild(text);

    const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    sub.setAttribute('x', cx); sub.setAttribute('y', cy + 28);
    sub.setAttribute('text-anchor', 'middle');
    sub.setAttribute('font-family', 'Poppins, sans-serif');
    sub.setAttribute('font-weight', '400');
    sub.setAttribute('font-size', '12');
    sub.setAttribute('fill', '#6b7280');
    sub.textContent = data[0].sub || '';
    svg.appendChild(sub);
  };

  // --- Bar chart ---
  const renderBars = (svg, data) => {
    const w = 600, h = 240, pad = 40;
    const barW = (w - pad * 2) / data.length - 12;
    const max = Math.max(...data.map(d => d.value));

    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', h);

    // Y axis line
    const axis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    axis.setAttribute('x1', pad); axis.setAttribute('y1', pad);
    axis.setAttribute('x2', pad); axis.setAttribute('y2', h - pad);
    axis.setAttribute('stroke', '#e5e7eb'); axis.setAttribute('stroke-width', '1');
    svg.appendChild(axis);

    data.forEach((d, i) => {
      const x = pad + i * ((w - pad * 2) / data.length) + 6;
      const barH = ((h - pad * 2) * (d.value / max));
      const y = (h - pad) - barH;

      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', x); rect.setAttribute('y', y);
      rect.setAttribute('width', barW); rect.setAttribute('height', barH);
      rect.setAttribute('rx', 4);
      rect.setAttribute('fill', d.color || '#0f172a');
      svg.appendChild(rect);

      const valTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      valTxt.setAttribute('x', x + barW / 2); valTxt.setAttribute('y', y - 6);
      valTxt.setAttribute('text-anchor', 'middle');
      valTxt.setAttribute('font-family', 'Poppins, sans-serif');
      valTxt.setAttribute('font-weight', '600');
      valTxt.setAttribute('font-size', '11');
      valTxt.setAttribute('fill', '#0a0a0a');
      valTxt.textContent = d.label;
      svg.appendChild(valTxt);

      const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      lbl.setAttribute('x', x + barW / 2); lbl.setAttribute('y', h - pad + 16);
      lbl.setAttribute('text-anchor', 'middle');
      lbl.setAttribute('font-family', 'Poppins, sans-serif');
      lbl.setAttribute('font-weight', '500');
      lbl.setAttribute('font-size', '10');
      lbl.setAttribute('fill', '#6b7280');
      lbl.textContent = d.sub;
      svg.appendChild(lbl);
    });
  };

  // Auto-init any svg with data-chart attribute
  document.querySelectorAll('svg[data-chart]').forEach((svg) => {
    const type = svg.dataset.chart;
    let data;
    try { data = JSON.parse(svg.dataset.data || '[]'); } catch(e){ data = []; }
    if (type === 'donut') renderDonut(svg, data);
    if (type === 'bars') renderBars(svg, data);
  });
})();