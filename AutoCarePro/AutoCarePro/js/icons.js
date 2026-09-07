/* ==========================================================================
   AutoCare Pro — icons.js
   A small hand-rolled inline-SVG icon set. Inline SVG (rather than an icon
   font or emoji) keeps the UI crisp, themeable via currentColor, and free of
   an extra network request.
   ========================================================================== */

window.AC = window.AC || {};

AC.icons = (function () {
  "use strict";

  // 24x24 stroke icons. Each entry is the inner markup only.
  const PATHS = {
    gauge: '<path d="M12 14 17 9"/><circle cx="12" cy="14" r="1"/><path d="M3.6 18a9 9 0 1 1 16.8 0"/>',
    car:
      '<path d="M5 17h14M6.5 17v2a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-2M20.5 17v2a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-2"/>' +
      '<path d="M3 17v-4.2a2 2 0 0 1 .2-.9l2.1-4.2A2 2 0 0 1 7.1 6.6h9.8a2 2 0 0 1 1.8 1.1l2.1 4.2c.13.28.2.58.2.9V17"/>' +
      '<path d="M3.5 12.5h17"/><circle cx="7.5" cy="14.6" r="1"/><circle cx="16.5" cy="14.6" r="1"/>',
    wrench:
      '<path d="M14.7 6.3a4 4 0 0 0 5 5l-9.4 9.4a2.1 2.1 0 0 1-3-3z"/><path d="M14.7 6.3 18 3"/>',
    droplet: '<path d="M12 2.7 6.9 8.4a7 7 0 1 0 10.2 0z"/>',
    chart: '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M7 15l3.5-4 3 2.6L20 7"/>',
    rupee: '<path d="M7 4h10M7 9h10M15.5 4c0 3.3-2.4 5-5.5 5H7l8 11"/>',
    settings:
      '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .33 1.77l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.6 1.6 0 0 0-1.77-.33 1.6 1.6 0 0 0-1 1.47V21a2 2 0 1 1-4 0v-.11A1.6 1.6 0 0 0 9 19.4a1.6 1.6 0 0 0-1.77.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.6 1.6 0 0 0 4.6 15a1.6 1.6 0 0 0-1.47-1H3a2 2 0 1 1 0-4h.11A1.6 1.6 0 0 0 4.6 9a1.6 1.6 0 0 0-.33-1.77l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.6 1.6 0 0 0 9 4.6h.09A1.6 1.6 0 0 0 10 3.13V3a2 2 0 1 1 4 0v.11a1.6 1.6 0 0 0 1 1.47 1.6 1.6 0 0 0 1.77-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.6 1.6 0 0 0 19.4 9v.09a1.6 1.6 0 0 0 1.47 1H21a2 2 0 1 1 0 4h-.11a1.6 1.6 0 0 0-1.47 1z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/>',
    bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    edit: '<path d="M11 4H4v16h16v-7"/><path d="M18.4 2.6a2 2 0 0 1 2.8 2.8L12 14.6l-3.5.9.9-3.5z"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/><path d="M10 11v5M14 11v5"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    close: '<path d="M18 6 6 18M6 6l12 12"/>',
    check: '<path d="m4 12 5 5L20 6"/>',
    alert: '<path d="M12 3 2 20h20z"/><path d="M12 9v5M12 17.5v.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
    wind: '<path d="M3 8h9a3 3 0 1 0-3-3"/><path d="M3 16h13a3 3 0 1 1-3 3"/><path d="M3 12h15"/>',
    heart: '<path d="M12 20.3 4.6 13a4.6 4.6 0 0 1 6.5-6.5l.9.9.9-.9A4.6 4.6 0 0 1 19.4 13z"/>',
    download: '<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 20h16"/>',
    upload: '<path d="M12 20V8"/><path d="m7 12 5-5 5 5"/><path d="M4 20h16"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    chevronRight: '<path d="m9 6 6 6-6 6"/>',
    chevronDown: '<path d="m6 9 6 6 6-6"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    fuel: '<path d="M4 20V5a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v15"/><path d="M3 20h11"/><path d="M13 9h3l2 2v6a2 2 0 0 0 3 0V8l-3-3"/>',
    pin: '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/>',
    activity: '<path d="M3 12h4l3 8 4-16 3 8h4"/>',
    trending: '<path d="M3 17 10 10l4 4 7-7"/><path d="M15 7h6v6"/>',
    shield: '<path d="M12 3 4.5 6v6c0 4.4 3.1 8.3 7.5 9.4 4.4-1.1 7.5-5 7.5-9.4V6z"/>',
    play: '<path d="M7 4.5 19 12 7 19.5z"/>',
    filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
    arrowRight: '<path d="M4 12h15"/><path d="m13 6 6 6-6 6"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    database: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/><path d="M4 11.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    ruler: '<rect x="2.5" y="8.5" width="19" height="7" rx="1.5"/><path d="M7 8.5v3M11 8.5v4M15 8.5v3M19 8.5v4"/>',
    wifi: '<path d="M2.5 9a15 15 0 0 1 19 0"/><path d="M5.5 12.5a10.5 10.5 0 0 1 13 0"/><path d="M8.5 16a6 6 0 0 1 7 0"/><path d="M12 19.5v.01"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    route: '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M15.5 5H9a3 3 0 0 0 0 6h6a3 3 0 0 1 0 6H8.5"/>',
    file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  };

  /**
   * @param {string} name
   * @param {object} [opts] { size, className, strokeWidth }
   * @returns {string} SVG markup
   */
  function get(name, opts = {}) {
    const inner = PATHS[name] || PATHS.info;
    const size = opts.size || 24;
    const cls = opts.className ? ` class="${opts.className}"` : "";
    const sw = opts.strokeWidth || 1.7;
    const fill = name === "play" ? "currentColor" : "none";
    return (
      `<svg${cls} width="${size}" height="${size}" viewBox="0 0 24 24" fill="${fill}" ` +
      `stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" ` +
      `stroke-linejoin="round" aria-hidden="true" focusable="false">${inner}</svg>`
    );
  }

  /** The AgentProof-style brand mark: shield + telemetry nodes + check. */
  function logo(size = 34) {
    return `
<svg width="${size}" height="${size}" viewBox="0 0 48 48" fill="none" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="acShield" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ff2b24"/>
      <stop offset="100%" stop-color="#8c0300"/>
    </linearGradient>
  </defs>
  <path d="M24 3.5 8 9.4v12.4c0 9.7 6.8 18.4 16 21.2 9.2-2.8 16-11.5 16-21.2V9.4z"
        fill="#0d0f12" stroke="url(#acShield)" stroke-width="2.4"/>
  <path d="M24 8.6 12.8 12.7v9c0 7.2 4.8 13.6 11.2 15.8 6.4-2.2 11.2-8.6 11.2-15.8v-9z"
        fill="none" stroke="rgba(255,43,36,.35)" stroke-width="1.1"/>
  <path d="M17 17.6 24 14l7 3.6" stroke="#ff2b24" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="17" cy="17.6" r="2" fill="#ff2b24"/>
  <circle cx="31" cy="17.6" r="2" fill="#ff2b24"/>
  <circle cx="24" cy="14" r="2" fill="#ff5b55"/>
  <path d="m17.6 25.8 4.6 4.8 9-9.4" stroke="#39ff88" stroke-width="3.2"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>`.trim();
  }

  /**
   * A side-profile hatchback drawn from scratch (no third-party artwork).
   * Uses the .car-art CSS classes so the colours stay in the design system.
   */
  function carArt() {
    return `
<svg class="car-art" viewBox="0 0 520 210" role="img" aria-label="Vehicle illustration">
  <defs>
    <linearGradient id="carBodyGradient" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ff2b24"/>
      <stop offset="55%" stop-color="#c00500"/>
      <stop offset="100%" stop-color="#5e0200"/>
    </linearGradient>
    <linearGradient id="groundGradient" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="rgba(225,6,0,0)"/>
      <stop offset="50%" stop-color="rgba(225,6,0,.55)"/>
      <stop offset="100%" stop-color="rgba(225,6,0,0)"/>
    </linearGradient>
  </defs>

  <!-- body: rear hatch on the left, bonnet on the right -->
  <path class="body-fill" d="M44 156c-13 0-20-8-18-21l3-16c2-11 10-19 21-21l82-13 62-40c10-6 21-10 33-10h84c16 0 31 6 43 17l40 37 58 10c22 4 33 16 33 33v11c0 8-5 13-13 13z"/>

  <!-- greenhouse -->
  <path class="glass" d="M206 51h32v37h-88z"/>
  <path class="glass" d="M250 51h63l30 37h-93z"/>

  <!-- shoulder + rocker lines -->
  <path d="M52 120h404" stroke="rgba(255,255,255,.16)" stroke-width="2" fill="none"/>
  <path d="M96 146h330" stroke="rgba(0,0,0,.28)" stroke-width="3" fill="none"/>
  <!-- door split -->
  <path d="M244 92v52" stroke="rgba(0,0,0,.32)" stroke-width="2.5" fill="none"/>
  <!-- handles -->
  <rect x="196" y="104" width="26" height="6" rx="3" fill="rgba(255,255,255,.32)"/>
  <rect x="270" y="104" width="26" height="6" rx="3" fill="rgba(255,255,255,.32)"/>
  <!-- lamps -->
  <path class="lamp" d="M436 106l38 6c7 1 11 5 11 11h-49z"/>
  <path class="lamp-rear" d="M27 112h32v20H26c-5 0-7-4-6-9z"/>
  <!-- wheel arches cut out of the body, then wheels on top -->
  <circle cx="132" cy="152" r="45" fill="#0d0f12"/>
  <circle cx="396" cy="152" r="45" fill="#0d0f12"/>
  <circle class="tyre" cx="132" cy="152" r="36"/>
  <circle class="tyre" cx="396" cy="152" r="36"/>
  <circle class="rim" cx="132" cy="152" r="17"/>
  <circle class="rim" cx="396" cy="152" r="17"/>
  <circle cx="132" cy="152" r="5" fill="#5a626d"/>
  <circle cx="396" cy="152" r="5" fill="#5a626d"/>
  <!-- ground glow -->
  <rect class="ground" x="40" y="192" width="440" height="3" rx="1.5"/>
</svg>`.trim();
  }

  return { get, logo, carArt, PATHS };
})();
