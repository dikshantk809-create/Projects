/* ==========================================================================
   AutoCare Pro — pages/settings.js
   Profile, units, notifications, location, environment provider, motion and
   data management (export / import / reset).
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.settings = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;
  const S = AC.storage;

  const SECTIONS = [
    { id: "profile", label: "Profile", icon: "user" },
    { id: "units", label: "Units", icon: "ruler" },
    { id: "notifications", label: "Notifications", icon: "bell" },
    { id: "location", label: "Location", icon: "pin" },
    { id: "environment", label: "Environmental data", icon: "wind" },
    { id: "appearance", label: "Appearance", icon: "sun" },
    { id: "data", label: "Data management", icon: "database" },
  ];

  let permission = "unknown";

  function render() {
    const s = S.getSettings();
    const db = S.loadDB();
    const bytes = S.usageBytes();

    return `
      <section class="page">
        <header class="page-head">
          <div>
            <div class="page-head__eyebrow">System</div>
            <h1>Settings</h1>
            <p class="page-head__sub">
              Everything here is stored locally in your browser under a single key
              (<code>${U.esc(S.KEY)}</code>). Nothing leaves this device unless you export it.
            </p>
          </div>
        </header>

        <div class="settings-layout">
          <nav class="settings-nav" aria-label="Settings sections">
            ${SECTIONS.map(
              (sec, i) =>
                `<button data-section="${sec.id}" class="${i === 0 ? "is-active" : ""}">
                   ${I.get(sec.icon, { size: 16 })}<span>${sec.label}</span>
                 </button>`
            ).join("")}
          </nav>

          <div class="settings-panels">
            ${profileSection(s)}
            ${unitsSection(s)}
            ${notificationsSection(s)}
            ${locationSection(s)}
            ${environmentSection(s)}
            ${appearanceSection(s)}
            ${dataSection(s, db, bytes)}
          </div>
        </div>
      </section>`;
  }

  const panel = (id, title, hint, inner) => `
    <article class="card settings-section" id="sec-${id}">
      <div class="card__head">
        <div>
          <span class="card__title">${U.esc(title)}</span>
          ${hint ? `<div class="chart-card__sub">${U.esc(hint)}</div>` : ""}
        </div>
      </div>
      ${inner}
    </article>`;

  const row = (title, desc, control) => `
    <div class="setting-row">
      <div class="setting-row__info">
        <div class="setting-row__title">${U.esc(title)}</div>
        <div class="setting-row__desc">${desc}</div>
      </div>
      <div class="setting-row__control">${control}</div>
    </div>`;

  /* ------------------------------------------------------------ sections -- */

  function profileSection(s) {
    return panel(
      "profile",
      "Profile",
      "Shown in the sidebar, the top bar and the dashboard greeting.",
      row(
        "Display name",
        "Used in the greeting — “Good morning, …”.",
        `<input class="input" id="setName" value="${U.esc(s.userName)}" maxlength="30" aria-label="Display name" />`
      ) +
        row(
          "Role label",
          "A short description shown under your name.",
          `<input class="input" id="setRole" value="${U.esc(s.userRole)}" maxlength="30" aria-label="Role label" />`
        )
    );
  }

  function unitsSection(s) {
    return panel(
      "units",
      "Units",
      "Distances are always stored in kilometres; this only changes how they are displayed.",
      row(
        "Distance unit",
        "Kilometres or miles.",
        `<div class="segmented" role="group" aria-label="Distance unit">
           <button data-units="km" class="${s.units === "km" ? "is-active" : ""}">Kilometres</button>
           <button data-units="mi" class="${s.units === "mi" ? "is-active" : ""}">Miles</button>
         </div>`
      )
    );
  }

  function notificationsSection(s) {
    const t = (key, label, desc) =>
      row(label, desc, UI.switchField({ name: `notif-${key}`, label: "", checked: s.notifications[key] }));
    return panel(
      "notifications",
      "Notifications",
      "Alerts are recomputed from your data every time a screen renders.",
      t("service", "Service alerts", "Overdue and due-soon maintenance items.") +
        t("wash", "Wash recommendations", "Raised when the wash score crosses 56.") +
        t("environment", "Environmental alerts", "Raised when AQI reaches the Poor band (201+).") +
        t("expense", "Expense reminders", "Reserved for future budget alerts.")
    );
  }

  function locationSection(s) {
    return panel(
      "location",
      "Location",
      "Location is optional. The app works fully without it.",
      row(
        "Location source",
        "Device location uses the browser Geolocation API and asks for permission. If it is denied or unavailable, AutoCare Pro silently falls back to the manual location.",
        `<div class="segmented" role="group" aria-label="Location source">
           <button data-location="manual" class="${s.locationMode === "manual" ? "is-active" : ""}">Manual</button>
           <button data-location="device" class="${s.locationMode === "device" ? "is-active" : ""}">Device</button>
         </div>`
      ) +
        row(
          "Manual location",
          "Used when device location is off or unavailable.",
          `<input class="input" id="setLocLabel" value="${U.esc(s.manualLocation.label)}" placeholder="City" aria-label="Location label" />
           <input class="input" id="setLat" type="number" step="0.0001" value="${U.esc(
             s.manualLocation.lat
           )}" style="min-width:120px" placeholder="Latitude" aria-label="Latitude" />
           <input class="input" id="setLon" type="number" step="0.0001" value="${U.esc(
             s.manualLocation.lon
           )}" style="min-width:120px" placeholder="Longitude" aria-label="Longitude" />`
        ) +
        row(
          "Permission status",
          "Reported by the browser without prompting, where supported.",
          `<span class="pill pill--muted" id="permState">${U.esc(permission)}</span>
           <button class="btn btn--sm" id="checkPermission">Check</button>`
        )
    );
  }

  function environmentSection(s) {
    const env = AC.environment.current();
    return panel(
      "environment",
      "Environmental data",
      "The provider that supplies AQI and weather to the Wash Advisor.",
      row(
        "Provider mode",
        "<strong>Mock</strong> is deterministic offline data — the app is fully functional with no network and no API key. <strong>Live</strong> uses the key-free Open-Meteo air-quality and forecast APIs; if the request fails the app degrades to mock automatically.",
        `<div class="segmented" role="group" aria-label="Environment provider">
           <button data-env="mock" class="${s.environmentMode === "mock" ? "is-active" : ""}">Mock / offline</button>
           <button data-env="live" class="${s.environmentMode === "live" ? "is-active" : ""}">Live (Open-Meteo)</button>
         </div>`
      ) +
        row(
          "Current reading",
          env
            ? `${U.esc(env.provider)} · AQI ${U.esc(env.aqi)} · ${U.esc(env.weather)} · fetched ${U.esc(
                new Date(env.fetchedAt).toLocaleString()
              )}`
            : "No reading cached yet.",
          `<button class="btn btn--sm" data-action="env:refresh">${I.get("refresh", { size: 14 })}<span>Refresh now</span></button>`
        )
    );
  }

  function appearanceSection(s) {
    return panel(
      "appearance",
      "Appearance",
      "AutoCare Pro ships as a single dark automotive theme, tuned for contrast on OLED panels.",
      row(
        "Theme",
        "The instrument-cluster palette is the product's identity, so there is no light mode. Accent, surface and status colours are all CSS variables in <code>css/variables.css</code> if you want to retheme it.",
        `<span class="pill pill--accent pill--plain">Dark cockpit</span>`
      ) +
        row(
          "Reduce motion",
          "Turns off non-essential animation. Your operating system's “reduce motion” setting is honoured automatically; this forces it on.",
          UI.switchField({ name: "reduceMotion", label: "", checked: s.reduceMotion })
        )
    );
  }

  function dataSection(s, db, bytes) {
    const counts = [
      ["Vehicles", db.vehicles.length],
      ["Service records", db.maintenanceRecords.length],
      ["Expenses", db.expenses.length],
      ["Journeys", db.journeys.length],
      ["Washes", db.washRecords.length],
    ];
    const quota = 5 * 1024 * 1024; // typical 5 MB localStorage budget
    const pct = U.clamp((bytes / quota) * 100, 0, 100);

    return `
      <article class="card settings-section danger-zone" id="sec-data">
        <div class="card__head">
          <div>
            <span class="card__title">Data management</span>
            <div class="chart-card__sub">Export, import or reset the local database.</div>
          </div>
          ${s.seededDemoData ? UI.demoFlag() : ""}
        </div>

        <div class="stat-row" style="margin-bottom:var(--sp-4)">
          ${counts
            .map(
              ([k, v]) => `<div class="stat"><span class="stat__label">${k}</span>
                            <span class="stat__value">${U.pad2(v)}</span></div>`
            )
            .join("")}
        </div>

        <div class="storage-meter" style="margin-bottom:var(--sp-4)">
          <div class="flex-between">
            <span class="micro-label">Storage used</span>
            <span class="mono" style="font-size:var(--fs-xs)">${(bytes / 1024).toFixed(1)} KB of ~5 MB</span>
          </div>
          <div class="storage-meter__bar"><div class="storage-meter__fill" style="width:${pct}%"></div></div>
        </div>

        ${row(
          "Export data",
          "Downloads the entire database as a timestamped JSON file — a complete backup you can re-import on any device.",
          `<button class="btn" id="btnExport">${I.get("download", { size: 15 })}<span>Export JSON</span></button>`
        )}
        ${row(
          "Import data",
          "Replaces the current database with a previously exported file. The payload is validated and sanitised before it is applied.",
          `<input type="file" id="importFile" accept="application/json,.json" hidden />
           <button class="btn" id="btnImport">${I.get("upload", { size: 15 })}<span>Import JSON</span></button>`
        )}
        ${row(
          "Reload demo data",
          "Clears everything and re-seeds the two demo vehicles with their full history.",
          `<button class="btn" id="btnReseed">${I.get("refresh", { size: 15 })}<span>Reset with demo data</span></button>`
        )}
        ${row(
          "Reset application",
          "Deletes every record and setting. This cannot be undone.",
          `<button class="btn btn--danger" id="btnReset">${I.get("trash", { size: 15 })}<span>Erase everything</span></button>`
        )}
      </article>`;
  }

  /* --------------------------------------------------------------- mount -- */

  function mount(root) {
    /* section navigation */
    U.$$("[data-section]", root).forEach((btn) =>
      btn.addEventListener("click", () => {
        U.$$("[data-section]", root).forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        const target = U.$(`#sec-${btn.dataset.section}`, root);
        if (target) target.scrollIntoView({ behavior: U.prefersReducedMotion() ? "auto" : "smooth", block: "start" });
      })
    );

    /* profile */
    const save = U.debounce(() => {
      S.setSettings({
        userName: (U.$("#setName", root).value || "Driver").trim().slice(0, 30),
        userRole: (U.$("#setRole", root).value || "Vehicle Owner").trim().slice(0, 30),
      });
      AC.app.renderChrome();
      UI.toast("Profile updated.");
    }, 500);
    ["#setName", "#setRole"].forEach((sel) => {
      const el = U.$(sel, root);
      if (el) el.addEventListener("input", save);
    });

    /* units */
    U.$$("[data-units]", root).forEach((btn) =>
      btn.addEventListener("click", () => {
        S.setSettings({ units: btn.dataset.units });
        UI.toast(`Distances now shown in ${btn.dataset.units === "mi" ? "miles" : "kilometres"}.`);
        AC.router.refresh();
      })
    );

    /* notifications */
    U.$$('input[name^="notif-"]', root).forEach((input) =>
      input.addEventListener("change", () => {
        const key = input.name.replace("notif-", "");
        S.setSettings({ notifications: { [key]: input.checked } });
        UI.toast("Notification preferences updated.");
      })
    );

    /* location */
    U.$$("[data-location]", root).forEach((btn) =>
      btn.addEventListener("click", async () => {
        S.setSettings({ locationMode: btn.dataset.location });
        UI.toast(
          btn.dataset.location === "device"
            ? "Device location enabled. Your browser may ask for permission."
            : "Using the manual location."
        );
        await AC.app.refreshEnvironment({ force: true });
        AC.router.refresh();
      })
    );

    const saveLoc = U.debounce(() => {
      const lat = Number(U.$("#setLat", root).value);
      const lon = Number(U.$("#setLon", root).value);
      if (Number.isNaN(lat) || Number.isNaN(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
        UI.toast("Latitude must be between -90 and 90, longitude between -180 and 180.", {
          type: "error",
          title: "Invalid coordinates",
        });
        return;
      }
      S.setSettings({
        manualLocation: {
          label: (U.$("#setLocLabel", root).value || "Custom location").trim().slice(0, 40),
          lat,
          lon,
        },
      });
      AC.app.refreshEnvironment({ force: true });
      UI.toast("Location updated.");
    }, 700);
    ["#setLocLabel", "#setLat", "#setLon"].forEach((sel) => {
      const el = U.$(sel, root);
      if (el) el.addEventListener("input", saveLoc);
    });

    const permBtn = U.$("#checkPermission", root);
    if (permBtn) {
      permBtn.addEventListener("click", async () => {
        permission = await AC.environment.permissionState();
        const el = U.$("#permState", root);
        if (el) el.textContent = permission;
        UI.toast(`Geolocation permission: ${permission}.`, { type: "info" });
      });
    }

    /* environment provider */
    U.$$("[data-env]", root).forEach((btn) =>
      btn.addEventListener("click", async () => {
        S.setSettings({ environmentMode: btn.dataset.env });
        UI.toast(
          btn.dataset.env === "live"
            ? "Switched to the live provider. Fetching…"
            : "Switched to deterministic offline data."
        );
        await AC.app.refreshEnvironment({ force: true });
        AC.router.refresh();
      })
    );

    /* appearance */
    const rm = U.$('input[name="reduceMotion"]', root);
    if (rm) {
      rm.addEventListener("change", () => {
        S.setSettings({ reduceMotion: rm.checked });
        document.documentElement.classList.toggle("reduce-motion", rm.checked);
        UI.toast(rm.checked ? "Non-essential motion disabled." : "Motion restored.");
      });
    }

    /* data management */
    const exportBtn = U.$("#btnExport", root);
    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        U.downloadFile(`autocare-pro-backup-${U.isoDate(U.today())}.json`, S.exportDB());
        UI.toast("Data exported successfully.");
      });
    }

    const importBtn = U.$("#btnImport", root);
    const fileInput = U.$("#importFile", root);
    if (importBtn && fileInput) {
      importBtn.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", async () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        try {
          const text = await U.readFileAsText(file);
          S.importDB(text);
          UI.toast("Data imported successfully.");
          AC.app.refreshAll();
        } catch (err) {
          UI.toast(err.message || "The selected file is not valid AutoCare Pro data.", {
            type: "error",
            title: "Import failed",
          });
        } finally {
          fileInput.value = "";
        }
      });
    }

    const reseed = U.$("#btnReseed", root);
    if (reseed) {
      reseed.addEventListener("click", async () => {
        const ok = await UI.confirm({
          title: "Reload demo data?",
          message:
            "This clears every record you have added and restores the two demo vehicles with their full history. This action cannot be undone.",
          confirmLabel: "Reload demo data",
        });
        if (!ok) return;
        S.resetDB({ seed: true });
        UI.toast("Demo data restored.");
        AC.app.refreshAll();
      });
    }

    const reset = U.$("#btnReset", root);
    if (reset) {
      reset.addEventListener("click", async () => {
        const ok = await UI.confirm({
          title: "Reset application data?",
          message:
            "Every vehicle, service record, expense, journey and setting will be permanently deleted from this browser. This action cannot be undone.",
          confirmLabel: "Erase everything",
        });
        if (!ok) return;
        S.resetDB({ seed: false });
        UI.toast("Application data erased.");
        AC.app.refreshAll();
      });
    }

    // Non-blocking permission probe on entry.
    AC.environment.permissionState().then((state) => {
      permission = state;
      const el = U.$("#permState");
      if (el) el.textContent = state;
    });
  }

  return { render, mount };
})();
