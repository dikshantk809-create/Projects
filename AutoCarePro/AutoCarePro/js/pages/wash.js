/* ==========================================================================
   AutoCare Pro — pages/wash.js
   The Smart Wash Advisor. The gauge, the live conditions and the
   "Why this score?" breakdown all come from AC.wash.calculateWashScore().
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.wash = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;
  const C = AC.constants;

  const GAUGE_R = 128;
  const CIRC = 2 * Math.PI * GAUGE_R;

  let state = { vehicleId: null };
  let lastResult = null;

  function activeVehicle() {
    const vehicles = AC.vehicles.all();
    if (!vehicles.length) return null;
    const found = vehicles.find((v) => v.id === state.vehicleId);
    if (found) return found;
    const primary = AC.vehicles.primary();
    state.vehicleId = primary ? primary.id : vehicles[0].id;
    return AC.vehicles.get(state.vehicleId);
  }

  function render(params) {
    if (params && params.vehicleId) state.vehicleId = params.vehicleId;
    const settings = AC.storage.getSettings();
    const env = AC.environment.current();
    const vehicle = activeVehicle();

    if (!vehicle) {
      return `
        <section class="page">
          ${header(null)}
          ${UI.emptyState({
            icon: "droplet",
            title: "No vehicles registered",
            text: "The wash advisor needs a vehicle before it can compute exposure and recommendations.",
            actionLabel: "Add vehicle",
            actionEvent: "vehicle:new",
          })}
        </section>`;
    }

    const result = AC.wash.calculateWashScore(vehicle, env);
    lastResult = result;

    return `
      <section class="page">
        ${header(vehicle)}

        ${
          result.conditions.degraded
            ? `<div style="margin-bottom:var(--sp-4)">${UI.banner(
                `Live environmental data is unavailable (${U.esc(
                  result.conditions.degraded
                )}). The score below uses offline reference data.`,
                "warning",
                "alert"
              )}</div>`
            : ""
        }

        <div class="wash-layout">
          ${gaugeCard(result, vehicle)}
          <div class="flex" style="flex-direction:column;gap:var(--sp-4)">
            ${conditionsCard(result, settings)}
            ${factorsCard(result)}
          </div>
        </div>

        ${UI.sectionHead("Environmental exposure", "Derived from the journeys logged for this vehicle.")}
        ${journeysCard(vehicle, settings)}

        ${UI.sectionHead("Wash history", "Each wash resets the time and usage factors.")}
        ${historyCard(vehicle, settings)}
      </section>`;
  }

  function header(vehicle) {
    const vehicles = AC.vehicles.all();
    return `
      <header class="page-head">
        <div>
          <div class="page-head__eyebrow">Environmental intelligence</div>
          <h1>Wash Advisor</h1>
          <p class="page-head__sub">
            A 0–100 recommendation built from elapsed time, pollution exposure, road dust and
            how far the vehicle has actually been driven — not a fixed weekly reminder.
          </p>
        </div>
        <div class="page-head__actions">
          ${
            vehicles.length > 1
              ? `<select class="select" id="washVehiclePicker" aria-label="Select vehicle" style="min-width:200px">
                   ${vehicles
                     .map(
                       (v) =>
                         `<option value="${U.esc(v.id)}"${vehicle && v.id === vehicle.id ? " selected" : ""}>${U.esc(
                           v.name
                         )}</option>`
                     )
                     .join("")}
                 </select>`
              : ""
          }
          <button class="btn" data-action="env:refresh">${I.get("refresh", { size: 16 })}<span>Refresh data</span></button>
          <button class="btn btn--primary" data-action="wash:new"${
            vehicle ? ` data-vehicle-id="${U.esc(vehicle.id)}"` : ""
          }>${I.get("droplet", { size: 16 })}<span>Record wash</span></button>
        </div>
      </header>`;
  }

  /* ---------------------------------------------------------------- gauge -- */

  function gaugeCard(result, vehicle) {
    const statusClass = `wash-status--${result.key}`;
    const ticks = [];
    for (let i = 0; i < 60; i += 1) {
      const angle = (i / 60) * Math.PI * 2;
      const long = i % 5 === 0;
      const r1 = GAUGE_R + 16;
      const r2 = r1 + (long ? 9 : 5);
      ticks.push(
        `<line x1="${150 + Math.cos(angle) * r1}" y1="${150 + Math.sin(angle) * r1}" x2="${
          150 + Math.cos(angle) * r2
        }" y2="${150 + Math.sin(angle) * r2}" opacity="${long ? 0.8 : 0.35}"/>`
      );
    }

    return `
      <article class="gauge-card corner-ticks">
        <div class="micro-label">Wash score · ${U.esc(vehicle.name)}</div>

        <div class="gauge">
          <svg viewBox="0 0 300 300" role="img" aria-label="Wash score ${result.score} out of 100">
            <g class="gauge__ticks">${ticks.join("")}</g>
            <circle class="gauge__track" cx="150" cy="150" r="${GAUGE_R}"/>
            <circle class="gauge__value" id="gaugeArc" cx="150" cy="150" r="${GAUGE_R}"
                    stroke-dasharray="${CIRC}" stroke-dashoffset="${CIRC}"
                    data-offset="${CIRC * (1 - result.score / 100)}"
                    style="stroke:${strokeFor(result.key)}"/>
          </svg>
          <div class="gauge__readout">
            <span class="gauge__num counter ${statusClass}" data-count="${result.score}"></span>
            <span class="gauge__caption">Wash score · 0–100</span>
          </div>
        </div>

        <div class="gauge__status ${statusClass}">${U.esc(result.status)}</div>
        <p class="gauge__message">${U.esc(result.message)}</p>

        <div class="provider-line">
          ${I.get("pin", { size: 14 })}
          <span>${U.esc(
            result.conditions.location ? result.conditions.location.label : "Unknown location"
          )}</span>
          <span>·</span>
          <span>${U.esc(result.conditions.provider || "mock")}</span>
          ${result.conditions.isDemo ? `<span>·</span><span>reference data</span>` : ""}
        </div>
      </article>`;
  }

  const strokeFor = (key) =>
    ({
      clean: "var(--success)",
      monitor: "var(--info)",
      soon: "var(--warning)",
      now: "var(--critical)",
    }[key] || "var(--accent-red-bright)");

  /* ----------------------------------------------------------- conditions -- */

  function conditionsCard(result, settings) {
    const c = result.conditions;
    const aqiBand = c.aqiBand || C.aqiBand(0);
    const dustBand = c.dustBand || C.levelBand(0);

    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Current conditions</span>
          ${UI.statusPill(c.isDemo ? "Offline data" : "Live data", c.isDemo ? "muted" : "success", {
            live: !c.isDemo,
          })}
        </div>

        <div class="condition-grid">
          <div class="condition">
            <div class="condition__label">Days since wash</div>
            <div class="condition__value">${U.pad2(result.daysSinceWash)}<small>days</small></div>
            <div class="condition__sub">${
              result.tripsSinceWash
                ? `${result.tripsSinceWash} trip${result.tripsSinceWash === 1 ? "" : "s"} logged since`
                : "No trips logged since"
            }</div>
          </div>
          <div class="condition">
            <div class="condition__label">Distance travelled</div>
            <div class="condition__value">${U.formatDistance(
              result.distanceSinceWash,
              settings.units,
              false
            )}<small>${U.unitLabel(settings.units)}</small></div>
            <div class="condition__sub">Source: ${U.esc(result.distanceSource)}</div>
          </div>
          <div class="condition">
            <div class="condition__label">Air quality</div>
            <div class="condition__value text-${aqiBand.tone === "success" ? "success" : aqiBand.tone}">${U.esc(
      c.aqi ?? "—"
    )}</div>
            <div class="condition__sub">${U.esc(aqiBand.label)}</div>
          </div>
          <div class="condition">
            <div class="condition__label">Road dust</div>
            <div class="condition__value text-${dustBand.tone === "success" ? "success" : dustBand.tone}">${Math.round(
      (c.dust || 0) * 100
    )}</div>
            <div class="condition__sub">${U.esc(dustBand.label)}</div>
          </div>
          <div class="condition">
            <div class="condition__label">Weather</div>
            <div class="condition__value" style="font-size:var(--fs-lg)">${U.esc(c.weather || "—")}</div>
            <div class="condition__sub">${U.esc(c.temperature ?? "—")}°C · ${U.esc(c.humidity ?? "—")}% RH</div>
          </div>
          <div class="condition">
            <div class="condition__label">Soiling multiplier</div>
            <div class="condition__value">×${(AC.wash.WEATHER_MULTIPLIER[c.weather] || 1).toFixed(2)}</div>
            <div class="condition__sub">Applied to elapsed time</div>
          </div>
        </div>
      </article>`;
  }

  /* -------------------------------------------------------------- factors -- */

  function factorsCard(result) {
    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Why this score?</span>
          <span class="count-note">${result.score} / 100</span>
        </div>

        ${result.factors.map(factorRow).join("")}

        <div class="divider"></div>
        <p class="field__hint">
          Weights: time 60 · pollution 20 · road dust 10 · usage 10. Each factor is computed
          independently and summed, so the recommendation can always be explained.
        </p>
      </article>`;
  }

  function factorRow(f) {
    const segments = 10;
    const filled = (f.points / f.max) * segments;
    const cells = Array.from({ length: segments }, (_, i) => {
      if (i + 1 <= Math.floor(filled)) return '<span class="factor__seg is-on"></span>';
      if (i < filled) return '<span class="factor__seg is-partial"></span>';
      return '<span class="factor__seg"></span>';
    }).join("");

    return `
      <div class="factor">
        <div class="factor__head">
          <span class="factor__name">${U.esc(f.name)}</span>
          <span class="factor__points">${U.esc(f.points)}<span> / ${U.esc(f.max)}</span></span>
        </div>
        <div class="factor__meter">${cells}</div>
        <span class="factor__note">${U.esc(f.note)}</span>
      </div>`;
  }

  /* ------------------------------------------------------------- journeys -- */

  function journeysCard(vehicle, settings) {
    const trips = AC.journeys.forVehicle(vehicle.id).slice(0, 6);
    const summary = AC.journeys.exposureSummary(vehicle.id);

    if (!trips.length) {
      return UI.emptyState({
        icon: "route",
        title: "No journeys logged",
        text: "Log a journey to feed distance, pollution and dust exposure into the wash score.",
        actionLabel: "Log journey",
        actionEvent: "journey:new",
      });
    }

    return `
      <article class="card">
        <div class="card__head">
          <span class="card__title">Recent journeys</span>
          <div class="flex gap-3" style="align-items:center">
            ${UI.statusPill(`Exposure ${summary.label}`, summary.tone)}
            <button class="btn btn--ghost btn--sm" data-action="journey:new">
              ${I.get("plus", { size: 14 })}<span>Log journey</span>
            </button>
          </div>
        </div>

        <div class="flex" style="flex-direction:column;gap:var(--sp-2)">
          ${trips
            .map(
              (t) => `
            <div class="journey">
              <div class="journey__route">
                <span class="journey__place">${U.esc(t.from)}</span>
                <span class="journey__arrow"></span>
                <span class="journey__place">${U.esc(t.to)}</span>
              </div>
              <div class="journey__stats">
                <div class="journey__stat"><span class="k">Distance</span><span class="v">${U.formatDistance(
                  t.distanceKm,
                  settings.units
                )}</span></div>
                <div class="journey__stat"><span class="k">Avg AQI</span><span class="v">${U.esc(
                  t.avgAqi ?? "—"
                )}</span></div>
                <div class="journey__stat"><span class="k">Dust</span><span class="v">${U.esc(
                  AC.journeys.dustLabel(t.dustLevel)
                )}</span></div>
                <div class="journey__stat"><span class="k">Date</span><span class="v">${U.formatDate(
                  t.date
                )}</span></div>
              </div>
              <button class="btn btn--sm btn--icon btn--danger" data-action="journey:delete" data-id="${U.esc(
                t.id
              )}" aria-label="Delete journey">${I.get("trash", { size: 14 })}</button>
            </div>`
            )
            .join("")}
        </div>

        <div class="divider"></div>
        <div class="stat-row">
          <div class="stat stat--accent">
            <span class="stat__label">Total distance</span>
            <span class="stat__value">${U.formatDistance(summary.totalDistance, settings.units)}</span>
          </div>
          <div class="stat">
            <span class="stat__label">Distance-weighted AQI</span>
            <span class="stat__value">${U.esc(summary.avgAqi ?? "—")}</span>
          </div>
          <div class="stat">
            <span class="stat__label">Dust exposure</span>
            <span class="stat__value">${Math.round(summary.dust * 100)}%</span>
          </div>
          <div class="stat">
            <span class="stat__label">Journeys</span>
            <span class="stat__value">${U.pad2(summary.count)}</span>
          </div>
        </div>
      </article>`;
  }

  function historyCard(vehicle, settings) {
    const rows = AC.wash.history(vehicle.id);
    if (!rows.length) {
      return UI.emptyState({
        icon: "droplet",
        title: "No washes recorded",
        text: "Record a wash to reset the time and usage factors of the score.",
        actionLabel: "Record wash",
        actionEvent: "wash:new",
      });
    }
    return `
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Date</th><th>Odometer</th><th>Cost</th><th>Interval</th><th></th></tr></thead>
          <tbody>
            ${rows
              .map((w, idx) => {
                const prev = rows[idx + 1];
                const gap = prev ? U.daysBetween(prev.date, w.date) : null;
                return `
                <tr>
                  <td class="num">${U.formatDate(w.date)} ${w.source === "demo" ? UI.demoFlag() : ""}</td>
                  <td class="num">${U.formatDistance(w.odometer, settings.units)}</td>
                  <td class="num">${U.formatCurrency(w.cost)}</td>
                  <td class="num text-muted">${gap === null ? "—" : `${gap} days after previous`}</td>
                  <td>
                    <div class="actions">
                      <button class="btn btn--sm btn--icon btn--danger" data-action="wash:delete" data-id="${U.esc(
                        w.id
                      )}" aria-label="Delete wash record">${I.get("trash", { size: 14 })}</button>
                    </div>
                  </td>
                </tr>`;
              })
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  /* ---------------------------------------------------------------- mount -- */

  function mount(root) {
    U.raf(() =>
      U.raf(() => {
        const arc = U.$("#gaugeArc", root);
        if (arc) arc.style.strokeDashoffset = arc.dataset.offset;
      })
    );

    const picker = U.$("#washVehiclePicker", root);
    if (picker) {
      picker.addEventListener("change", (e) => {
        state.vehicleId = e.target.value;
        AC.router.refresh();
      });
    }
  }

  return { render, mount, state, get lastResult() { return lastResult; } };
})();
