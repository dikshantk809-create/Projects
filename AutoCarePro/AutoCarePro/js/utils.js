/* ==========================================================================
   AutoCare Pro — utils.js
   Pure helper functions. No DOM state, no storage access, no side effects
   beyond the DOM helpers at the bottom. Everything here is unit-testable.
   ========================================================================== */

window.AC = window.AC || {};

AC.utils = (function () {
  "use strict";

  const MS_DAY = 86400000;

  /* ---------------------------------------------------------------- ids -- */

  /**
   * Collision-resistant id. crypto.randomUUID() when the browser has it,
   * otherwise a timestamp + random suffix (good enough for a local database).
   */
  function uid(prefix = "id") {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return `${prefix}_${window.crypto.randomUUID().slice(0, 13).replace(/-/g, "")}`;
    }
    return `${prefix}_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  }

  /* ---------------------------------------------------------------- math -- */

  const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

  /** Linear interpolation of `value` from [inMin,inMax] onto [outMin,outMax]. */
  function mapRange(value, inMin, inMax, outMin, outMax) {
    if (inMax === inMin) return outMin;
    const t = clamp((value - inMin) / (inMax - inMin), 0, 1);
    return outMin + t * (outMax - outMin);
  }

  const sum = (arr, pick = (x) => x) =>
    arr.reduce((acc, item) => acc + (Number(pick(item)) || 0), 0);

  const round = (n, dp = 0) => {
    const f = Math.pow(10, dp);
    return Math.round((Number(n) || 0) * f) / f;
  };

  const isNum = (v) => v !== "" && v !== null && v !== undefined && !Number.isNaN(Number(v));

  /* --------------------------------------------------------------- dates -- */

  /** Parse a value into a Date at local midnight, or null when unusable. */
  function toDate(value) {
    if (!value) return null;
    const d = value instanceof Date ? new Date(value.getTime()) : new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    d.setHours(0, 0, 0, 0);
    return d;
  }

  const today = () => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  };

  /** Whole days from `from` to `to` (negative when `to` is in the past). */
  function daysBetween(from, to = today()) {
    const a = toDate(from);
    const b = toDate(to);
    if (!a || !b) return null;
    return Math.round((b - a) / MS_DAY);
  }

  function addDays(date, days) {
    const d = toDate(date) || today();
    d.setDate(d.getDate() + days);
    return d;
  }

  function addMonths(date, months) {
    const d = toDate(date) || today();
    d.setMonth(d.getMonth() + months);
    return d;
  }

  /** `YYYY-MM-DD` — the format used by <input type="date"> and by storage. */
  function isoDate(date) {
    const d = toDate(date);
    if (!d) return "";
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
  }

  const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

  /** "02 AUG 2026" — the automotive readout format used across the UI. */
  function formatDate(date) {
    const d = toDate(date);
    if (!d) return "—";
    return `${String(d.getDate()).padStart(2, "0")} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  }

  function formatMonthKey(date) {
    const d = toDate(date);
    if (!d) return "";
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  }

  function monthLabel(key) {
    const [y, m] = String(key).split("-");
    return `${MONTHS[Number(m) - 1]} ${String(y).slice(2)}`;
  }

  /** "8 days ago" / "in 12 days" / "today". */
  function relativeDays(date) {
    const diff = daysBetween(date);
    if (diff === null) return "—";
    if (diff === 0) return "TODAY";
    if (diff > 0) return `${diff} DAY${diff === 1 ? "" : "S"} AGO`;
    return `IN ${Math.abs(diff)} DAY${Math.abs(diff) === 1 ? "" : "S"}`;
  }

  /* ------------------------------------------------------------- numbers -- */

  const nf = new Intl.NumberFormat("en-IN");

  const formatNumber = (n) => nf.format(Math.round(Number(n) || 0));

  /** Indian rupee, no decimals — matches how workshop bills are quoted. */
  function formatCurrency(n) {
    const value = Math.round(Number(n) || 0);
    return `₹${nf.format(value)}`;
  }

  /** Compact currency for chart axes: ₹12.4K, ₹1.2L. */
  function compactCurrency(n) {
    const v = Number(n) || 0;
    if (Math.abs(v) >= 100000) return `₹${round(v / 100000, 1)}L`;
    if (Math.abs(v) >= 1000) return `₹${round(v / 1000, 1)}K`;
    return `₹${Math.round(v)}`;
  }

  const KM_PER_MILE = 1.609344;

  /**
   * Distance display honouring the user's unit preference. Everything is
   * stored in kilometres; conversion happens only at the presentation layer.
   */
  function formatDistance(km, units = "km", withUnit = true) {
    const n = Number(km) || 0;
    const value = units === "mi" ? n / KM_PER_MILE : n;
    const text = formatNumber(value);
    return withUnit ? `${text} ${units === "mi" ? "MI" : "KM"}` : text;
  }

  const unitLabel = (units) => (units === "mi" ? "MI" : "KM");

  /** Zero-padded counter, e.g. 2 -> "02". Used by the dashboard readouts. */
  const pad2 = (n) => String(Math.max(0, Math.round(Number(n) || 0))).padStart(2, "0");

  /* -------------------------------------------------------------- strings -- */

  /**
   * Escape untrusted text before it is interpolated into an HTML template.
   * Every user- or file-supplied string in this app goes through here.
   */
  function esc(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  const titleCase = (s) =>
    String(s || "")
      .toLowerCase()
      .replace(/(^|\s|-)(\w)/g, (m) => m.toUpperCase());

  const initials = (name) =>
    String(name || "?")
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => w[0])
      .join("")
      .toUpperCase();

  const slug = (s) =>
    String(s || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

  /* -------------------------------------------------------------- arrays -- */

  function groupBy(arr, keyFn) {
    return arr.reduce((acc, item) => {
      const k = keyFn(item);
      (acc[k] = acc[k] || []).push(item);
      return acc;
    }, {});
  }

  const sortBy = (arr, pick, dir = "asc") =>
    [...arr].sort((a, b) => {
      const av = pick(a);
      const bv = pick(b);
      if (av === bv) return 0;
      return (av > bv ? 1 : -1) * (dir === "asc" ? 1 : -1);
    });

  /* -------------------------------------------------------------- timing -- */

  function debounce(fn, wait = 200) {
    let t;
    return function debounced(...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  const raf = (fn) => window.requestAnimationFrame(fn);

  const prefersReducedMotion = () =>
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ----------------------------------------------------------------- DOM -- */

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /**
   * Animate a number from 0 to `target` inside an element. Skipped entirely
   * when the user prefers reduced motion.
   */
  function countUp(el, target, { duration = 900, format = formatNumber } = {}) {
    if (!el) return;
    const end = Number(target) || 0;
    if (prefersReducedMotion() || duration === 0) {
      el.textContent = format(end);
      return;
    }
    const start = performance.now();
    const step = (now) => {
      const t = clamp((now - start) / duration, 0, 1);
      // easeOutExpo — fast settle, feels mechanical rather than bouncy
      const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      el.textContent = format(end * eased);
      if (t < 1) raf(step);
    };
    raf(step);
  }

  /** Trigger a client-side file download from a string payload. */
  function downloadFile(filename, content, mime = "application/json") {
    const blob = new Blob([content], { type: `${mime};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(new Error("Unable to read the selected file."));
      reader.readAsText(file);
    });
  }

  /** Greeting driven by the device clock — Good Morning / Afternoon / Evening. */
  function greeting(d = new Date()) {
    const h = d.getHours();
    if (h < 12) return "GOOD MORNING";
    if (h < 17) return "GOOD AFTERNOON";
    return "GOOD EVENING";
  }

  return {
    MS_DAY,
    uid,
    clamp,
    mapRange,
    sum,
    round,
    isNum,
    toDate,
    today,
    daysBetween,
    addDays,
    addMonths,
    isoDate,
    formatDate,
    formatMonthKey,
    monthLabel,
    relativeDays,
    formatNumber,
    formatCurrency,
    compactCurrency,
    formatDistance,
    unitLabel,
    pad2,
    esc,
    titleCase,
    initials,
    slug,
    groupBy,
    sortBy,
    debounce,
    raf,
    prefersReducedMotion,
    $,
    $$,
    countUp,
    downloadFile,
    readFileAsText,
    greeting,
    KM_PER_MILE,
  };
})();
