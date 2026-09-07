/* ==========================================================================
   AutoCare Pro — charts.js
   A thin, opinionated wrapper over Chart.js.

   Responsibilities:
     - apply the dark automotive theme once, globally
     - keep a registry of live charts so route changes can destroy them
       (Chart.js leaks canvases and resize listeners otherwise)
     - expose small factories so pages describe data, not chart plumbing
   ========================================================================== */

window.AC = window.AC || {};

AC.charts = (function () {
  "use strict";

  const U = AC.utils;
  const registry = new Map();

  const css = (name, fallback) => {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  };

  const PALETTE = () => [
    css("--viz-1", "#e10600"),
    css("--viz-2", "#4aa8ff"),
    css("--viz-3", "#39ff88"),
    css("--viz-4", "#ff9d2e"),
    css("--viz-5", "#a06bff"),
    css("--viz-6", "#22d3ee"),
    css("--viz-7", "#f5d90a"),
    css("--viz-8", "#7d8794"),
  ];

  let themed = false;

  function applyTheme() {
    if (themed || typeof window.Chart === "undefined") return;
    const Chart = window.Chart;
    const grid = "rgba(255,255,255,.06)";
    const text = css("--text-muted", "#626b76");

    Chart.defaults.color = text;
    Chart.defaults.font.family = css("--font-sans", "Inter, sans-serif").replace(/"/g, "");
    Chart.defaults.font.size = 11;
    Chart.defaults.borderColor = grid;
    Chart.defaults.animation.duration = U.prefersReducedMotion() ? 0 : 800;
    Chart.defaults.animation.easing = "easeOutQuart";
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = css("--surface-elevated", "#171a1f");
    Chart.defaults.plugins.tooltip.borderColor = css("--border", "#282d35");
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.titleColor = css("--text-primary", "#f4f6f8");
    Chart.defaults.plugins.tooltip.bodyColor = css("--text-secondary", "#a1a8b2");
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.boxWidth = 8;
    Chart.defaults.plugins.tooltip.boxHeight = 8;
    Chart.defaults.maintainAspectRatio = false;
    themed = true;
  }

  const axis = (opts = {}) => ({
    grid: { color: "rgba(255,255,255,.05)", drawTicks: false, ...(opts.grid || {}) },
    border: { display: false },
    ticks: { padding: 8, maxRotation: 0, ...(opts.ticks || {}) },
    ...opts.rest,
  });

  /** Create (or replace) a chart bound to a canvas id. */
  function create(canvasId, config) {
    if (typeof window.Chart === "undefined") return null;
    applyTheme();
    destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    const chart = new window.Chart(canvas.getContext("2d"), config);
    registry.set(canvasId, chart);
    return chart;
  }

  function destroy(canvasId) {
    const existing = registry.get(canvasId);
    if (existing) {
      existing.destroy();
      registry.delete(canvasId);
    }
  }

  /** Called by the router before every page swap — prevents canvas leaks. */
  function destroyAll() {
    registry.forEach((chart) => chart.destroy());
    registry.clear();
  }

  /* ------------------------------------------------------------ factories -- */

  function bar(canvasId, { labels, data, color, money = false, label = "Value", integer = false }) {
    const c = color || css("--accent-red", "#e10600");
    return create(canvasId, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label,
            data,
            backgroundColor: c,
            hoverBackgroundColor: css("--accent-red-bright", "#ff2b24"),
            borderRadius: 5,
            maxBarThickness: 42,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          x: axis(),
          y: axis({
            ticks: {
              precision: 0,
              stepSize: integer ? 1 : undefined,
              callback: (v) =>
                integer && !Number.isInteger(v) ? "" : money ? U.compactCurrency(v) : U.formatNumber(v),
            },
            rest: { beginAtZero: true },
          }),
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) =>
                `${ctx.dataset.label}: ${money ? U.formatCurrency(ctx.parsed.y) : U.formatNumber(ctx.parsed.y)}`,
            },
          },
        },
      },
    });
  }

  function stackedBar(canvasId, { labels, series, money = true }) {
    return create(canvasId, {
      type: "bar",
      data: {
        labels,
        datasets: series.map((s) => ({
          label: s.label,
          data: s.data,
          backgroundColor: s.hex,
          borderRadius: 4,
          maxBarThickness: 42,
        })),
      },
      options: {
        responsive: true,
        scales: {
          x: { ...axis(), stacked: true },
          y: {
            ...axis({ ticks: { callback: (v) => (money ? U.compactCurrency(v) : U.formatNumber(v)) } }),
            stacked: true,
            beginAtZero: true,
          },
        },
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, pointStyle: "rectRounded", padding: 14 },
          },
          tooltip: {
            callbacks: {
              label: (ctx) =>
                `${ctx.dataset.label}: ${money ? U.formatCurrency(ctx.parsed.y) : U.formatNumber(ctx.parsed.y)}`,
            },
          },
        },
      },
    });
  }

  function line(canvasId, { labels, data, color, fill = true, label = "Value", money = false, suffix = "" }) {
    const c = color || css("--accent-red-bright", "#ff2b24");
    return create(canvasId, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label,
            data,
            borderColor: c,
            backgroundColor: fill ? gradient(canvasId, c) : "transparent",
            borderWidth: 2.4,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: c,
            pointBorderColor: css("--bg-primary", "#070809"),
            pointBorderWidth: 2,
            tension: 0.34,
            fill,
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: axis(),
          y: axis({
            ticks: {
              callback: (v) => (money ? U.compactCurrency(v) : `${U.formatNumber(v)}${suffix}`),
            },
          }),
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) =>
                `${ctx.dataset.label}: ${
                  money ? U.formatCurrency(ctx.parsed.y) : `${U.formatNumber(ctx.parsed.y)}${suffix}`
                }`,
            },
          },
        },
      },
    });
  }

  function multiLine(canvasId, { labels, series, suffix = "" }) {
    return create(canvasId, {
      type: "line",
      data: {
        labels,
        datasets: series.map((s, i) => ({
          label: s.label,
          data: s.data,
          borderColor: s.color || PALETTE()[i % 8],
          backgroundColor: "transparent",
          borderWidth: 2.2,
          pointRadius: 3,
          pointHoverRadius: 6,
          tension: 0.34,
          yAxisID: s.axis || "y",
          spanGaps: true,
        })),
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, pointStyle: "line", padding: 14 },
          },
        },
        scales: {
          x: axis(),
          y: axis({ ticks: { callback: (v) => `${U.formatNumber(v)}${suffix}` } }),
          y1: {
            ...axis({ grid: { drawOnChartArea: false } }),
            position: "right",
            display: series.some((s) => s.axis === "y1"),
          },
        },
      },
    });
  }

  function doughnut(canvasId, { labels, data, colors, money = true }) {
    return create(canvasId, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors || PALETTE(),
            borderColor: css("--surface", "#111419"),
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        cutout: "62%",
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, pointStyle: "rectRounded", padding: 14 },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0) || 1;
                const pct = Math.round((ctx.parsed / total) * 100);
                return `${ctx.label}: ${money ? U.formatCurrency(ctx.parsed) : U.formatNumber(ctx.parsed)} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  /** Vertical fade under a line series. */
  function gradient(canvasId, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return "transparent";
    const ctx = canvas.getContext("2d");
    const g = ctx.createLinearGradient(0, 0, 0, canvas.height || 240);
    g.addColorStop(0, hexToRgba(color, 0.34));
    g.addColorStop(1, hexToRgba(color, 0));
    return g;
  }

  function hexToRgba(hex, alpha) {
    const h = String(hex).replace("#", "").trim();
    if (h.length !== 6) return `rgba(225,6,0,${alpha})`;
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  const available = () => typeof window.Chart !== "undefined";

  return {
    PALETTE,
    applyTheme,
    create,
    destroy,
    destroyAll,
    bar,
    stackedBar,
    line,
    multiLine,
    doughnut,
    available,
    css,
  };
})();
