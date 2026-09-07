/* ==========================================================================
   AutoCare Pro — app.js
   Application bootstrap and the global shell:
     - builds the sidebar / top bar / mobile navigation from ROUTES
     - one delegated click handler drives every [data-action] in the app
     - command palette (Ctrl/Cmd + K) and keyboard shortcuts
     - splash screen lifecycle
     - service-worker registration and online/offline status
   ========================================================================== */

window.AC = window.AC || {};

AC.app = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;
  const C = AC.constants;

  let paletteIndex = 0;
  let paletteItems = [];

  /* ================================================================ chrome = */

  function renderChrome() {
    renderSidebar();
    renderTopbar();
    renderMobileNav();
    if (AC.router.current) AC.router.render();
  }

  function renderSidebar() {
    const sidebar = U.$("#sidebar");
    if (!sidebar) return;
    const groups = [];
    C.ROUTES.forEach((r) => {
      let g = groups.find((x) => x.label === r.group);
      if (!g) {
        g = { label: r.group, items: [] };
        groups.push(g);
      }
      g.items.push(r);
    });

    const alerts = AC.notifications.generate(AC.environment.current());
    const badges = {
      maintenance: alerts.filter((a) => a.id.startsWith("overdue-") || a.id.startsWith("due-")).length,
      wash: alerts.filter((a) => a.id.startsWith("wash-")).length,
    };

    sidebar.innerHTML = `
      <div class="sidebar__brand">
        <span class="brand-mark">${I.logo(34)}</span>
        <span class="brand-text">
          <span class="brand-text__name">AutoCare</span>
          <span class="brand-text__sub">// PRO</span>
        </span>
      </div>

      <div class="sidebar__status">
        <span class="pill pill--success pill--live" style="border:0;background:transparent;padding:0"></span>
        <span id="systemStatus">System online</span>
      </div>

      <nav class="sidebar__nav" aria-label="Primary">
        ${groups
          .map(
            (g) => `
          <div class="nav-group">
            <div class="nav-group__label">${U.esc(g.label)}</div>
            ${g.items
              .map(
                (item) => `
              <a class="nav-item" href="#${item.hash}" data-route="${item.hash}">
                <span class="nav-item__icon">${I.get(item.icon, { size: 18 })}</span>
                <span>${U.esc(item.label)}</span>
                ${
                  badges[item.hash]
                    ? `<span class="nav-item__badge">${badges[item.hash]}</span>`
                    : ""
                }
              </a>`
              )
              .join("")}
          </div>`
          )
          .join("")}
      </nav>

      <div class="sidebar__footer">
        <span>SVMS v1.0</span>
        <span id="netStatus">${navigator.onLine ? "ONLINE" : "OFFLINE"}</span>
      </div>`;
  }

  function renderTopbar() {
    const bar = U.$("#topbar");
    if (!bar) return;
    const s = AC.storage.getSettings();
    const alerts = AC.notifications.generate(AC.environment.current());
    const actionable = AC.notifications.actionableCount(alerts);

    bar.innerHTML = `
      <div class="topbar__search">
        ${I.get("search", { size: 16 })}
        <input id="globalSearch" type="search" placeholder="Search vehicles, services, expenses…"
               aria-label="Global search" />
        <span class="topbar__kbd"><kbd>Ctrl</kbd> <kbd>K</kbd></span>
      </div>

      <div class="topbar__spacer"></div>

      <div class="topbar__actions">
        <button class="icon-btn" data-action="palette:open" aria-label="Open command palette">
          ${I.get("layers", { size: 18 })}
        </button>
        <button class="icon-btn" data-action="alerts:open" aria-label="Notifications">
          ${I.get("bell", { size: 18 })}
          ${actionable ? '<span class="icon-btn__dot"></span>' : ""}
        </button>
        <button class="user-chip" data-action="nav:settings" aria-label="Open settings">
          <span class="avatar">${U.esc(U.initials(s.userName))}</span>
          <span class="user-chip__meta">
            <span class="user-chip__name">${U.esc(s.userName)}</span>
            <span class="user-chip__role">${U.esc(s.userRole)}</span>
          </span>
        </button>
      </div>`;
  }

  function renderMobileNav() {
    const nav = U.$("#mobileNav");
    const top = U.$("#mobileTopbar");
    if (!nav || !top) return;
    const s = AC.storage.getSettings();

    top.innerHTML = `
      <button class="icon-btn" data-action="drawer:toggle" aria-label="Open navigation" aria-expanded="false">
        ${I.get("menu", { size: 20 })}
      </button>
      <span class="mobile-topbar__brand">${I.logo(24)} AutoCare</span>
      <span class="mobile-topbar__spacer"></span>
      <button class="icon-btn" data-action="palette:open" aria-label="Search">${I.get("search", { size: 18 })}</button>
      <button class="user-chip" data-action="nav:settings" aria-label="Settings">
        <span class="avatar" style="width:30px;height:30px;font-size:.9rem">${U.esc(U.initials(s.userName))}</span>
      </button>`;

    const primary = ["dashboard", "vehicles", "maintenance", "wash", "analytics"];
    nav.innerHTML = primary
      .map((hash) => {
        const r = C.ROUTES.find((x) => x.hash === hash);
        return `<a class="mobile-nav__item" href="#${r.hash}" data-route="${r.hash}">
                  ${I.get(r.icon, { size: 20 })}<span>${U.esc(r.label.split(" ")[0])}</span>
                </a>`;
      })
      .join("");
  }

  /* ============================================================== actions = */

  /** Central action dispatcher — every `data-action` in the app lands here. */
  async function dispatch(action, payload = {}) {
    switch (action) {
      case "vehicle:new":
        return AC.forms.vehicleModal();
      case "vehicle:edit":
        return AC.forms.vehicleModal(payload.id);
      case "vehicle:view":
        return AC.forms.vehicleDetailModal(payload.id);
      case "vehicle:primary": {
        const v = AC.vehicles.setPrimary(payload.id);
        UI.toast(`${v ? v.name : "Vehicle"} is now the primary vehicle.`);
        return refreshAll();
      }
      case "vehicle:delete": {
        const v = AC.vehicles.get(payload.id);
        if (!v) return null;
        const ok = await UI.confirm({
          title: "Delete vehicle?",
          message: `This removes ${v.name} together with its service records, expenses, journeys and wash history. This action cannot be undone.`,
          confirmLabel: "Delete vehicle",
        });
        if (!ok) return null;
        AC.vehicles.remove(payload.id);
        UI.toast(`${v.name} deleted.`);
        return refreshAll();
      }

      case "maintenance:new":
        return AC.forms.maintenanceModal({ vehicleId: payload.vehicleId, type: payload.type });
      case "maintenance:edit":
        return AC.forms.maintenanceModal({ recordId: payload.id });
      case "maintenance:delete": {
        const ok = await UI.confirm({
          title: "Delete service record?",
          message:
            "Due dates and health scores will be recalculated without it. Any expense created from this record is removed too.",
          confirmLabel: "Delete record",
        });
        if (!ok) return null;
        AC.maintenance.deleteRecord(payload.id);
        UI.toast("Service record deleted.");
        return refreshAll();
      }

      case "expense:new":
        return AC.forms.expenseModal({ vehicleId: payload.vehicleId, category: payload.category });
      case "expense:edit":
        return AC.forms.expenseModal({ expenseId: payload.id });
      case "expense:delete": {
        const ok = await UI.confirm({
          title: "Delete expense?",
          message: "This entry will be removed from all totals and charts.",
          confirmLabel: "Delete expense",
        });
        if (!ok) return null;
        AC.expenses.remove(payload.id);
        UI.toast("Expense deleted.");
        return refreshAll();
      }

      case "journey:new":
        return AC.forms.journeyModal({ vehicleId: payload.vehicleId });
      case "journey:delete": {
        const ok = await UI.confirm({
          title: "Delete journey?",
          message:
            "Exposure and wash-score usage will be recalculated. The odometer is not rolled back automatically.",
          confirmLabel: "Delete journey",
        });
        if (!ok) return null;
        AC.journeys.remove(payload.id);
        UI.toast("Journey deleted.");
        return refreshAll();
      }

      case "wash:new":
        return AC.forms.washModal({ vehicleId: payload.vehicleId });
      case "wash:delete": {
        const ok = await UI.confirm({
          title: "Delete wash record?",
          message: "The wash score will be recalculated from the next most recent wash.",
          confirmLabel: "Delete record",
        });
        if (!ok) return null;
        AC.storage.remove("washRecords", payload.id);
        UI.toast("Wash record deleted.");
        return refreshAll();
      }

      case "env:refresh": {
        UI.toast("Refreshing environmental data…", { type: "info", duration: 1600 });
        await refreshEnvironment({ force: true });
        AC.router.refresh();
        return null;
      }

      case "alerts:open":
        return alertsModal();
      case "palette:open":
        return openPalette();
      case "drawer:toggle":
        return toggleDrawer();

      default:
        if (action.startsWith("nav:")) return AC.router.navigate(action.slice(4));
        console.warn("[AutoCare] Unhandled action:", action);
        return null;
    }
  }

  function bindGlobalClicks() {
    document.addEventListener("click", (e) => {
      const trigger = e.target.closest("[data-action]");
      if (!trigger) return;
      e.preventDefault();
      dispatch(trigger.dataset.action, {
        id: trigger.dataset.id,
        vehicleId: trigger.dataset.vehicleId,
        type: trigger.dataset.type,
        category: trigger.dataset.category,
      });
    });

    // Close the mobile drawer whenever a nav link is used.
    document.addEventListener("click", (e) => {
      if (e.target.closest("[data-route]")) closeDrawer();
    });
  }

  /* ============================================================== alerts == */

  function alertsModal() {
    const alerts = AC.notifications.generate(AC.environment.current());
    UI.openModal({
      title: "Alerts",
      subtitle: `${alerts.length} generated from your current data`,
      body: `<div class="alert-list">${alerts.map(UI.alertRow).join("")}</div>`,
      footer: `<button class="btn btn--ghost" data-close-modal>Close</button>`,
      onMount(modal) {
        modal.querySelectorAll("[data-alert-action]").forEach((btn) => {
          btn.addEventListener("click", () => {
            const alert = alerts.find((a) => a.id === btn.dataset.alertAction);
            UI.closeModal(true);
            if (!alert || !alert.action) return;
            if (alert.action.hash) AC.router.navigate(alert.action.hash);
            else if (alert.action.event) dispatch(alert.action.event, alert.action.payload || {});
          });
        });
      },
    });
  }

  /* ============================================================= drawer === */

  const drawerOpen = () => U.$("#sidebar").classList.contains("is-open");

  function toggleDrawer() {
    drawerOpen() ? closeDrawer() : openDrawer();
  }

  function openDrawer() {
    U.$("#sidebar").classList.add("is-open");
    U.$("#drawerBackdrop").classList.add("is-open");
    const btn = U.$('[data-action="drawer:toggle"]');
    if (btn) btn.setAttribute("aria-expanded", "true");
  }

  function closeDrawer() {
    U.$("#sidebar").classList.remove("is-open");
    U.$("#drawerBackdrop").classList.remove("is-open");
    const btn = U.$('[data-action="drawer:toggle"]');
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  /* ==================================================== command palette === */

  function paletteCommands() {
    const cmds = [
      { label: "Go to Dashboard", hint: "#dashboard", icon: "gauge", run: () => AC.router.navigate("dashboard") },
      { label: "Go to Vehicles", hint: "#vehicles", icon: "car", run: () => AC.router.navigate("vehicles") },
      { label: "Go to Maintenance", hint: "#maintenance", icon: "wrench", run: () => AC.router.navigate("maintenance") },
      { label: "Go to Wash Advisor", hint: "#wash", icon: "droplet", run: () => AC.router.navigate("wash") },
      { label: "Go to Analytics", hint: "#analytics", icon: "chart", run: () => AC.router.navigate("analytics") },
      { label: "Go to Expenses", hint: "#expenses", icon: "rupee", run: () => AC.router.navigate("expenses") },
      { label: "Go to Settings", hint: "#settings", icon: "settings", run: () => AC.router.navigate("settings") },
      { label: "Add vehicle", hint: "Create", icon: "plus", run: () => dispatch("vehicle:new") },
      { label: "Log maintenance", hint: "Create", icon: "wrench", run: () => dispatch("maintenance:new") },
      { label: "Record expense", hint: "Create", icon: "rupee", run: () => dispatch("expense:new") },
      { label: "Record wash", hint: "Create", icon: "droplet", run: () => dispatch("wash:new") },
      { label: "Log journey", hint: "Create", icon: "route", run: () => dispatch("journey:new") },
      { label: "Refresh environmental data", hint: "System", icon: "refresh", run: () => dispatch("env:refresh") },
      { label: "Export data as JSON", hint: "System", icon: "download", run: () => {
          U.downloadFile(`autocare-pro-backup-${U.isoDate(U.today())}.json`, AC.storage.exportDB());
          UI.toast("Data exported successfully.");
        } },
      { label: "View alerts", hint: "System", icon: "bell", run: () => dispatch("alerts:open") },
    ];

    // Vehicles become searchable entries of their own.
    AC.vehicles.all().forEach((v) =>
      cmds.push({
        label: `Open ${v.name}`,
        hint: v.registration || "Vehicle",
        icon: "car",
        run: () => dispatch("vehicle:view", { id: v.id }),
      })
    );

    return cmds;
  }

  function openPalette(prefill = "") {
    const palette = U.$("#palette");
    palette.hidden = false;
    palette.innerHTML = `
      <div class="modal__backdrop" data-close-palette></div>
      <div class="palette__panel" role="dialog" aria-modal="true" aria-label="Command palette">
        <input class="palette__input" id="paletteInput" type="text" placeholder="Type a command or search…"
               value="${U.esc(prefill)}" autocomplete="off" />
        <div class="palette__list" id="paletteList"></div>
      </div>`;

    palette.querySelector("[data-close-palette]").addEventListener("click", closePalette);
    const input = U.$("#paletteInput");
    input.addEventListener("input", () => filterPalette(input.value));
    input.addEventListener("keydown", paletteKeys);
    filterPalette(prefill);
    input.focus();
    input.select();
  }

  function filterPalette(query) {
    const q = String(query || "").toLowerCase().trim();
    paletteItems = paletteCommands().filter(
      (c) => !q || c.label.toLowerCase().includes(q) || c.hint.toLowerCase().includes(q)
    );
    paletteIndex = 0;
    paintPalette();
  }

  function paintPalette() {
    const list = U.$("#paletteList");
    if (!list) return;
    if (!paletteItems.length) {
      list.innerHTML = `<div class="palette__empty">No matching commands.</div>`;
      return;
    }
    list.innerHTML = paletteItems
      .map(
        (c, i) => `
        <button class="palette__item${i === paletteIndex ? " is-active" : ""}" data-index="${i}">
          ${I.get(c.icon, { size: 16 })}<span>${U.esc(c.label)}</span><small>${U.esc(c.hint)}</small>
        </button>`
      )
      .join("");
    list.querySelectorAll("[data-index]").forEach((btn) =>
      btn.addEventListener("click", () => runPalette(Number(btn.dataset.index)))
    );
  }

  function paletteKeys(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      paletteIndex = Math.min(paletteIndex + 1, paletteItems.length - 1);
      paintPalette();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      paletteIndex = Math.max(paletteIndex - 1, 0);
      paintPalette();
    } else if (e.key === "Enter") {
      e.preventDefault();
      runPalette(paletteIndex);
    }
  }

  function runPalette(index) {
    const cmd = paletteItems[index];
    closePalette();
    if (cmd) cmd.run();
  }

  function closePalette() {
    const palette = U.$("#palette");
    if (!palette) return;
    palette.hidden = true;
    palette.innerHTML = "";
  }

  const paletteOpen = () => !U.$("#palette").hidden;

  /* ========================================================== shortcuts === */

  function bindKeyboard() {
    document.addEventListener("keydown", (e) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        paletteOpen() ? closePalette() : openPalette();
        return;
      }

      if (e.key === "Escape") {
        if (paletteOpen()) return closePalette();
        if (UI.isModalOpen()) return UI.closeModal();
        if (drawerOpen()) return closeDrawer();
        return;
      }

      if (typing || e.ctrlKey || e.metaKey || e.altKey) return;

      // Single-key navigation shortcuts (press "g" then a letter is overkill
      // for this app — direct digits map to the seven routes).
      const digit = Number(e.key);
      if (digit >= 1 && digit <= C.ROUTES.length) {
        AC.router.navigate(C.ROUTES[digit - 1].hash);
        return;
      }
      if (e.key.toLowerCase() === "n") dispatch("vehicle:new");
      if (e.key === "?") shortcutsModal();
    });
  }

  function shortcutsModal() {
    const rows = [
      ["Ctrl / ⌘ + K", "Open the command palette"],
      ["1 – 7", "Jump to a section"],
      ["N", "Add a vehicle"],
      ["Esc", "Close dialog, palette or drawer"],
      ["?", "Show this help"],
    ];
    UI.openModal({
      title: "Keyboard shortcuts",
      size: "sm",
      body: rows
        .map(
          ([k, v]) =>
            `<div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--border-soft)">
               <span class="text-muted">${U.esc(v)}</span><kbd>${U.esc(k)}</kbd></div>`
        )
        .join(""),
      footer: `<button class="btn btn--ghost" data-close-modal>Close</button>`,
    });
  }

  /* ============================================================= search === */

  function bindSearch() {
    document.addEventListener("focusin", (e) => {
      if (e.target.id === "globalSearch") {
        e.target.blur();
        openPalette();
      }
    });
  }

  /* ======================================================== environment === */

  async function refreshEnvironment(opts = {}) {
    try {
      await AC.environment.load(opts);
    } catch (err) {
      console.warn("[AutoCare] Environment refresh failed", err);
    }
  }

  /* ============================================================ refresh === */

  /** Re-render chrome + current page after any data mutation. */
  function refreshAll() {
    renderSidebar();
    renderTopbar();
    renderMobileNav();
    AC.router.refresh();
  }

  /* ================================================================ boot == */

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    // The single-file build has no separate service-worker.js to register.
    if (window.AC && window.AC.STANDALONE) {
      console.info("[AutoCare] Single-file build — service worker not applicable.");
      return;
    }
    if (window.location.protocol === "file:") {
      console.info("[AutoCare] Service worker skipped — open the app over http:// to enable offline mode.");
      return;
    }
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("service-worker.js")
        .then((reg) => console.info("[AutoCare] Service worker registered", reg.scope))
        .catch((err) => console.warn("[AutoCare] Service worker registration failed", err));
    });
  }

  function bindNetworkStatus() {
    const paint = () => {
      const online = navigator.onLine;
      const net = U.$("#netStatus");
      const sys = U.$("#systemStatus");
      if (net) net.textContent = online ? "ONLINE" : "OFFLINE";
      if (sys) sys.textContent = online ? "System online" : "Offline mode";
    };
    window.addEventListener("online", () => {
      paint();
      UI.toast("Back online.", { type: "success", duration: 2200 });
    });
    window.addEventListener("offline", () => {
      paint();
      UI.toast("You are offline. AutoCare Pro keeps working from local data.", {
        type: "warning",
        duration: 4200,
      });
    });
    paint();
  }

  function hideSplash() {
    const splash = U.$("#splash");
    const shell = U.$("#appShell");
    if (shell) shell.classList.add("is-ready");
    if (!splash) return;
    splash.classList.add("is-hidden");
    setTimeout(() => splash.remove(), 500);
  }

  async function init() {
    const started = performance.now();

    // 1. Database — create + seed on very first run only.
    const db = AC.storage.loadDB();
    if (!db.vehicles.length && !db.settings.seededDemoData) {
      AC.seed.apply(db);
      AC.storage.saveDB(db);
    }

    if (!AC.storage.isAvailable()) {
      UI.toast(
        "Browser storage is unavailable, so changes will not persist after you close this tab.",
        { type: "warning", title: "Storage disabled", duration: 6000 }
      );
    }

    if (db.settings.reduceMotion) document.documentElement.classList.add("reduce-motion");

    // 2. Register pages and start routing.
    Object.keys(AC.pages).forEach((name) => AC.router.register(name, AC.pages[name]));

    renderChrome();
    bindGlobalClicks();
    bindKeyboard();
    bindSearch();
    bindNetworkStatus();
    U.$("#drawerBackdrop").addEventListener("click", closeDrawer);

    AC.router.start();
    AC.router.onChange(closeDrawer);

    // 3. Environment is fetched after first paint so nothing blocks on it.
    refreshEnvironment().then(() => {
      renderSidebar();
      renderTopbar();
      AC.router.refresh();
    });

    // 4. Splash: minimum 1.4s so the animation reads, never longer than needed.
    const elapsed = performance.now() - started;
    setTimeout(hideSplash, Math.max(0, 1400 - elapsed));

    registerServiceWorker();
  }

  return {
    init,
    dispatch,
    refreshAll,
    refreshEnvironment,
    renderChrome,
    renderSidebar,
    renderTopbar,
    openPalette,
    closePalette,
    toggleDrawer,
  };
})();

document.addEventListener("DOMContentLoaded", () => {
  try {
    AC.app.init();
  } catch (err) {
    console.error("[AutoCare] Startup failed", err);
    const splash = document.getElementById("splash");
    if (splash) splash.remove();
    const view = document.getElementById("view");
    if (view) {
      view.innerHTML =
        '<div class="empty"><h3 class="empty__title">AutoCare Pro could not start</h3>' +
        '<p class="empty__text">Reload the page. If the problem persists, clear this site\'s storage and try again.</p></div>';
    }
  }
});
