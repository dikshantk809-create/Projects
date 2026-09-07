/* ==========================================================================
   AutoCare Pro — pages/dashboard.js
   The overview screen. Every number on it is computed by AC.analytics,
   AC.health, AC.maintenance or AC.wash from stored records.
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.dashboard = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;

  let alertsCache = [];

  function render() {
    const settings = AC.storage.getSettings();
    const env = AC.environment.current();
    const vehicles = AC.vehicles.all();
    const metrics = AC.analytics.dashboardMetrics(env);
    const primary = AC.vehicles.primary();
    alertsCache = AC.notifications.generate(env);

    return `
      <section class="page">
        ${head(settings, vehicles.length)}

        <div class="grid grid--metrics stagger">
          ${UI.metricCard({
            label: "Total vehicles",
            value: metrics.totalVehicles,
            format: "pad",
            foot: metrics.totalVehicles === 1 ? "Registered vehicle" : "Registered vehicles",
            icon: "car",
          })}
          ${UI.metricCard({
            label: "Service due",
            value: metrics.serviceDue,
            format: "pad",
            foot: metrics.serviceDue ? "Maintenance required" : "Nothing due soon",
            icon: "wrench",
            tone: metrics.serviceDue ? "warning" : "",
          })}
          ${UI.metricCard({
            label: "Overdue",
            value: metrics.overdue,
            format: "pad",
            foot: metrics.overdue ? "Immediate attention" : "No overdue services",
            icon: "alert",
            tone: metrics.overdue ? "critical" : "success",
          })}
          ${UI.metricCard({
            label: "Maintenance cost",
            value: metrics.maintenanceCost,
            format: "money",
            foot: "Recorded service + repair spend",
            icon: "rupee",
          })}
        </div>

        ${
          vehicles.length
            ? `<div class="split-hero mt-4">
                 ${heroVehicle(primary, settings)}
                 ${healthCard(primary)}
               </div>`
            : `<div class="mt-6">${UI.emptyState({
                icon: "car",
                title: "No vehicles registered",
                text: "Add your first vehicle to start tracking maintenance, expenses, health and environmental exposure.",
                actionLabel: "Add vehicle",
                actionEvent: "vehicle:new",
              })}</div>`
        }

        <div class="grid grid--2 mt-4">
          ${alertsCard()}
          ${environmentCard(env, settings)}
        </div>

        <div class="grid grid--2 mt-4">
          ${timelineCard(primary, settings)}
          ${spendCard()}
        </div>
      </section>`;
  }

  /* --------------------------------------------------------------- parts -- */

  function head(settings, count) {
    return `
      <header class="page-head">
        <div>
          <div class="page-head__eyebrow">Vehicle Management System</div>
          <h1>Dashboard</h1>
          <div class="greeting mt-4">${U.esc(U.greeting())}, ${U.esc(
      settings.userName.toUpperCase()
    )}</div>
          <p class="page-head__sub">
            ${
              count
                ? "Here's your vehicle performance overview — health, service intervals and environmental exposure, computed from your records."
                : "Add a vehicle to bring this dashboard to life."
            }
          </p>
        </div>
        <div class="page-head__actions">
          <button class="btn" data-action="journey:new">${I.get("route", { size: 16 })}<span>Log journey</span></button>
          <button class="btn btn--primary" data-action="vehicle:new">${I.get("plus", { size: 16 })}<span>Add vehicle</span></button>
        </div>
      </header>`;
  }

  function heroVehicle(vehicle, settings) {
    if (!vehicle) return "";
    const next = AC.maintenance.nextService(vehicle);
    const washDays = U.daysBetween(vehicle.lastWashDate);

    return `
      <article class="hero-vehicle tech-grid corner-ticks">
        <div class="hero-vehicle__top">
          <div>
            <div class="micro-label">Primary vehicle</div>
            <h2 class="hero-vehicle__name">${U.esc(vehicle.name)}</h2>
            <div class="hero-vehicle__spec">
              ${U.esc(vehicle.fuelType)} · ${U.esc(vehicle.year)} · ${U.formatDistance(
      vehicle.odometer,
      settings.units
    )}
            </div>
          </div>
          ${vehicle.source === "demo" ? UI.demoFlag() : ""}
        </div>

        <div class="hero-vehicle__art">${I.carArt()}</div>

        <div class="hero-vehicle__foot">
          <div class="stat-row" style="flex:1">
            <div class="stat stat--accent">
              <span class="stat__label">Odometer</span>
              <span class="stat__value">${U.formatDistance(vehicle.odometer, settings.units)}</span>
            </div>
            <div class="stat">
              <span class="stat__label">Next service</span>
              <span class="stat__value">${
                next && next.remainingKm !== null
                  ? U.formatDistance(Math.abs(next.remainingKm), settings.units)
                  : "—"
              }</span>
              <span class="stat__label">${
                next
                  ? `${U.esc(next.label)}${next.remainingKm < 0 ? " · overdue" : ""}`
                  : "No history"
              }</span>
            </div>
            <div class="stat">
              <span class="stat__label">Last wash</span>
              <span class="stat__value">${washDays === null ? "—" : U.pad2(washDays)}</span>
              <span class="stat__label">${washDays === null ? "Not recorded" : "days ago"}</span>
            </div>
          </div>
          <button class="btn btn--primary" data-action="vehicle:view" data-id="${U.esc(vehicle.id)}">
            View vehicle ${I.get("arrowRight", { size: 16 })}
          </button>
        </div>
        <span class="telemetry-caption">SYS/PRIMARY · ${U.esc(vehicle.registration || "NO-REG")}</span>
      </article>`;
  }

  function healthCard(vehicle) {
    if (!vehicle) return "";
    const h = AC.health.calculateVehicleHealth(vehicle);
    const tone = h.band.tone;

    return `
      <article class="card health-card corner-ticks">
        <div class="card__head">
          <span class="card__title">Vehicle health</span>
          ${UI.statusPill(h.band.label, tone)}
        </div>

        <div class="health-hero">
          ${healthRing(h.overall, tone)}
          <div>
            <div class="health-hero__value text-${tone === "success" ? "success" : tone}">
              <span class="counter" data-count="${h.overall}"></span><sup>%</sup>
            </div>
            <div class="micro-label mt-4">Composite score · ${U.esc(vehicle.name)}</div>
          </div>
        </div>

        <div class="health-bars">
          ${UI.progressBar({ label: "Engine", value: h.engine, tone: barTone(h.engine) })}
          ${UI.progressBar({ label: "Tyres", value: h.tyres, tone: barTone(h.tyres) })}
          ${UI.progressBar({ label: "Battery", value: h.battery, tone: barTone(h.battery) })}
          ${UI.progressBar({ label: "Brakes", value: h.brakes, tone: barTone(h.brakes) })}
        </div>

        <p class="health-note">
          Weighted from service history (engine 35%, brakes 25%, tyres 20%, battery 20%),
          vehicle age (${h.ageYears} yr) and distance travelled.
          ${h.overdueCount ? `${h.overdueCount} overdue item${h.overdueCount === 1 ? "" : "s"} deducted.` : ""}
        </p>
      </article>`;
  }

  const barTone = (v) => (v >= 75 ? "success" : v >= 50 ? "warning" : "critical");

  /** Compact SVG ring used beside the health number. */
  function healthRing(value, tone) {
    const r = 42;
    const circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - U.clamp(value, 0, 100) / 100);
    const color =
      tone === "success" ? "var(--success)" : tone === "warning" ? "var(--warning)" : "var(--critical)";
    return `
      <svg class="health-ring" width="104" height="104" viewBox="0 0 104 104" aria-hidden="true">
        <circle cx="52" cy="52" r="${r}" fill="none" stroke="var(--surface-sunken)" stroke-width="9"/>
        <circle cx="52" cy="52" r="${r}" fill="none" stroke="${color}" stroke-width="9"
                stroke-linecap="round" transform="rotate(-90 52 52)"
                stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}"
                data-ring-offset="${offset}" style="transition:stroke-dashoffset 1100ms cubic-bezier(.16,1,.3,1)"/>
      </svg>`;
  }

  function alertsCard() {
    const rows = alertsCache.slice(0, 5).map(UI.alertRow).join("");
    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Active alerts</span>
          <span class="count-note">${U.pad2(alertsCache.length)} generated</span>
        </div>
        <div class="alert-list">${rows}</div>
        <div class="divider"></div>
        <div class="quick-actions">
          <button class="quick-action" data-action="maintenance:new">${I.get("wrench", { size: 17 })}<span>Log service</span></button>
          <button class="quick-action" data-action="wash:new">${I.get("droplet", { size: 17 })}<span>Record wash</span></button>
          <button class="quick-action" data-action="expense:new">${I.get("rupee", { size: 17 })}<span>Add expense</span></button>
          <button class="quick-action" data-action="nav:wash">${I.get("activity", { size: 17 })}<span>Wash advisor</span></button>
        </div>
      </article>`;
  }

  function environmentCard(env, settings) {
    if (!env) {
      return `<article class="card"><div class="card__head"><span class="card__title">Environment</span></div>
        <p class="text-muted">Loading environmental data…</p></article>`;
    }
    const band = AC.constants.aqiBand(env.aqi);
    const dust = AC.environment.dustIndex(env);
    const dustBand = AC.constants.levelBand(dust);

    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Environmental conditions</span>
          ${UI.statusPill(env.isDemo ? "Mock data" : "Live", env.isDemo ? "muted" : "success", { live: !env.isDemo })}
        </div>

        <div class="env-strip">
          <div class="env-cell">
            <div class="env-cell__label">Air quality</div>
            <div class="env-cell__value text-${band.tone === "success" ? "success" : band.tone}">${U.esc(env.aqi)}</div>
            <div class="env-cell__sub">${U.esc(band.label)}</div>
          </div>
          <div class="env-cell">
            <div class="env-cell__label">PM2.5</div>
            <div class="env-cell__value">${U.esc(env.pm25)}</div>
            <div class="env-cell__sub">µg/m³</div>
          </div>
          <div class="env-cell">
            <div class="env-cell__label">Road dust</div>
            <div class="env-cell__value text-${dustBand.tone === "success" ? "success" : dustBand.tone}">${Math.round(
      dust * 100
    )}</div>
            <div class="env-cell__sub">${U.esc(dustBand.label)}</div>
          </div>
          <div class="env-cell">
            <div class="env-cell__label">Weather</div>
            <div class="env-cell__value" style="font-size:var(--fs-lg)">${U.esc(env.weather)}</div>
            <div class="env-cell__sub">${U.esc(env.temperature)}°C · ${U.esc(env.humidity)}% RH</div>
          </div>
        </div>

        <div class="provider-line mt-4">
          ${I.get("pin", { size: 14 })}
          <span>${U.esc(env.location ? env.location.label : "Unknown")}</span>
          <span>·</span>
          <span>${U.esc(env.provider)}</span>
          <span>·</span>
          <span>Updated ${U.esc(new Date(env.fetchedAt).toLocaleTimeString())}</span>
          <button class="btn btn--ghost btn--sm" style="margin-left:auto" data-action="env:refresh">
            ${I.get("refresh", { size: 14 })}<span>Refresh</span>
          </button>
        </div>
        ${
          env.degraded
            ? `<div class="mt-4">${UI.banner(
                `Live provider unavailable (${U.esc(env.degraded)}) — showing offline data.`,
                "warning",
                "alert"
              )}</div>`
            : ""
        }

        <div class="divider"></div>
        <div class="card__head" style="margin-bottom:var(--sp-3)">
          <span class="card__title">Fleet exposure · last 6 months</span>
          <span class="count-note">${U.esc(U.unitLabel(settings.units))}</span>
        </div>
        <div class="chart-box" style="height:180px"><canvas id="dashExposureChart"></canvas></div>
      </article>`;
  }

  function timelineCard(vehicle, settings) {
    if (!vehicle) return "";
    const records = AC.maintenance.forVehicle(vehicle.id).slice(0, 4);
    const schedule = AC.maintenance.scheduleFor(vehicle);
    const byType = schedule.reduce((acc, r) => {
      acc[r.type] = r;
      return acc;
    }, {});

    const items = records
      .map((r) => {
        const st = byType[r.type];
        const tone = st ? UI.toneForStatus(st.status) : "success";
        return `
          <li class="timeline__item timeline__item--${tone}">
            <span class="timeline__dot"></span>
            <div class="timeline__title">${U.esc(AC.constants.maintenanceLabel(r.type))}</div>
            <div class="timeline__meta">
              <span>${U.formatDate(r.date)}</span>
              <span>${U.formatDistance(r.odometer, settings.units)}</span>
              <span>${U.formatCurrency(r.cost)}</span>
            </div>
            ${
              st && st.dueOdometer
                ? `<div class="timeline__next">Next service at ${U.formatDistance(
                    st.dueOdometer,
                    settings.units
                  )} · ${UI.statusPill(AC.maintenance.STATUS_META[st.status].label, tone)}</div>`
                : ""
            }
          </li>`;
      })
      .join("");

    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Maintenance timeline · ${U.esc(vehicle.name)}</span>
          <button class="btn btn--ghost btn--sm" data-action="nav:maintenance">Open</button>
        </div>
        ${
          items
            ? `<ul class="timeline">${items}</ul>`
            : `<p class="text-muted">No maintenance recorded for this vehicle yet.</p>`
        }
      </article>`;
  }

  function spendCard() {
    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Monthly spend · last 6 months</span>
          <button class="btn btn--ghost btn--sm" data-action="nav:expenses">Open</button>
        </div>
        <div class="chart-box"><canvas id="dashSpendChart"></canvas></div>
      </article>`;
  }

  /* --------------------------------------------------------------- mount -- */

  function mount(root) {
    // Health ring animation
    U.raf(() =>
      U.raf(() => {
        U.$$("[data-ring-offset]", root).forEach((c) => {
          c.style.strokeDashoffset = c.dataset.ringOffset;
        });
      })
    );

    if (AC.charts.available()) {
      // Monthly spend
      const series = AC.expenses.monthly({}, 6);
      AC.charts.bar("dashSpendChart", {
        labels: series.map((s) => s.label),
        data: series.map((s) => s.value),
        money: true,
        label: "Spend",
      });

      // Distance driven per month — the exposure the fleet actually accumulates
      const usage = AC.journeys.monthlyDistance(null, 6);
      AC.charts.line("dashExposureChart", {
        labels: usage.map((u) => u.label),
        data: usage.map((u) => u.value),
        label: "Distance",
        color: AC.charts.css("--viz-2", "#4aa8ff"),
        suffix: " km",
      });
    }

    // Alert action buttons
    U.$$("[data-alert-action]", root).forEach((btn) => {
      btn.addEventListener("click", () => {
        const alert = alertsCache.find((a) => a.id === btn.dataset.alertAction);
        if (!alert || !alert.action) return;
        if (alert.action.hash) AC.router.navigate(alert.action.hash);
        else if (alert.action.event) AC.app.dispatch(alert.action.event, alert.action.payload || {});
      });
    });
  }

  return { render, mount };
})();
