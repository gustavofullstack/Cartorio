(function () {
  var palette = { blue: "#2563eb", teal: "#0f766e", rose: "#b83f58", gold: "#b7791f", line: "#e6ebf0" };
  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent || "null"); } catch (e) { return null; }
  }
  function grid() { return { left: 58, right: 40, top: 48, bottom: 44, containLabel: true }; }

  function commitsOption(rows) {
    return {
      animation: false,
      color: [palette.blue],
      tooltip: { trigger: "axis" },
      grid: grid(),
      xAxis: { type: "category", data: rows.map(function (r) { return r.week; }) },
      yAxis: { type: "value", name: "commits", splitLine: { lineStyle: { color: palette.line } } },
      series: [{ name: "Commits", type: "bar", data: rows.map(function (r) { return r.commits; }), label: { show: true, position: "top" } }]
    };
  }

  function testsOption(rows) {
    return {
      animation: false,
      color: [palette.teal, palette.gold],
      tooltip: { trigger: "axis" },
      legend: { top: 8 },
      grid: grid(),
      xAxis: { type: "category", data: rows.map(function (r) { return r.date; }) },
      yAxis: [
        { type: "value", name: "testes", splitLine: { lineStyle: { color: palette.line } } },
        { type: "value", name: "coverage", min: 85, max: 100, axisLabel: { formatter: function (v) { return v + "%"; } } }
      ],
      series: [
        { name: "Testes pytest", type: "line", smooth: true, lineStyle: { width: 3 }, data: rows.map(function (r) { return r.tests; }) },
        { name: "Coverage %", type: "line", smooth: true, yAxisIndex: 1, lineStyle: { width: 2, type: "dashed" }, data: rows.map(function (r) { return r.cov; }) }
      ]
    };
  }

  function scopesOption(rows) {
    return {
      animation: false,
      color: [palette.blue, palette.teal, palette.gold, palette.rose, "#64748b", "#7c3aed", "#0ea5e9", "#84cc16", "#f97316", "#14b8a6", "#a855f7"],
      tooltip: { trigger: "item" },
      legend: { bottom: 4, type: "scroll" },
      series: [{
        type: "pie",
        radius: ["40%", "68%"],
        center: ["50%", "44%"],
        data: rows.map(function (r) { return { name: r.scope, value: r.count }; }),
        label: { formatter: function (p) { return p.name + " " + p.value; } }
      }]
    };
  }

  function setup() {
    if (!window.echarts) return;
    var defs = {
      "chart-commits": { data: "data-commits", fn: commitsOption },
      "chart-tests": { data: "data-tests", fn: testsOption },
      "chart-scopes": { data: "data-scopes", fn: scopesOption }
    };
    Object.keys(defs).forEach(function (elId) {
      var el = document.getElementById(elId);
      var rows = readJson(defs[elId].data);
      if (!el || !rows) return;
      var chart = echarts.init(el, null, { renderer: "canvas" });
      chart.setOption(defs[elId].fn(rows), true);
      window.addEventListener("resize", function () { chart.resize(); });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
