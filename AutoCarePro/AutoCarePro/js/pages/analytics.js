/* ==========================================================================
   AutoCare Pro — pages/analytics.js
   Eight charts, all fed by computed series. Charts are created in mount() and
   destroyed by the router before the next page renders.
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.analytics = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;

  let state = { vehicleId: "all", months: 6 };

  const scopeFilter = () => (state.vehicleId === "all" ? {} : { vehicleId: state.vehicleId });
  const scopeId = () => (state.vehicleId === "all" ? null : state.vehicleId);

  function render() {
    const vehicles = AC.vehicles.all();
    if (!vehicles.length) {
      return `
        <section class="page">
          ${header([])}
          ${UI.emptyState({
            icon: "chart",
            title: "Nothing to analyse yet",
            text: "Add a vehicle and record a few services, expenses or journeys — the charts build themselves from your data.",
            actionLabel: "Add vehicle",
            actionEvent: "vehicle:new",
          })}
        </section>`;
    }

    const insights = AC.analytics.insights(scopeId());

    return `
      <section class="page">
        ${header(vehicles)}

        <div class="grid grid--2 stagger" style="margin-bottom:var(--sp-4)">
          ${insights
            .slice(0, 4)
            .map(
              (ins) => `
            <div class="insight">
              <span class="insight__mark"></span>
              <div>
                <div class="insight__title">${U.esc(ins.title)}</div>
                <div class="insight__text">${U.esc(ins.text)}</div>
              </div>
            </div>`
            )
            .join("")}
        </div>

        <div class="grid grid--2">
          ${chartCard("Monthly expenses", "Total recorded spend per month", "chMonthly")}
          ${chartCard("Expense distribution", "Share of spend by category", "chCategory")}
        </div>

        <div class="grid grid--2 mt-4">
          ${chartCard("Vehicle usage", "Distance from logged journeys", "chUsage")}
          ${chartCard("Odometer growth", "Reconstructed from recorded readings", "chOdometer")}
        </div>

        <div class="grid grid--2 mt-4">
          ${chartCard("Maintenance cost by type", "Where service money goes", "chMaintenance")}
          ${chartCard("Vehicle health trend", "Score replayed over recent months", "chHealth")}
        </div>

        <div class="grid grid--2 mt-4">
          ${chartCard("Wash frequency", "Washes recorded per month", "chWash")}
          ${chartCard("Environmental exposure", "Distance-weighted AQI and dust index", "chExposure")}
        </div>
      </section>`;
  }

  function header(vehicles) {
    return `
      <header class="page-head">
        <div>
          <div class="page-head__eyebrow">Data intelligence</div>
          <h1>Analytics</h1>
          <p class="page-head__sub">
            Spending, usage, health and exposure trends — every series is derived from the records
            stored on this device.
          </p>
        </div>
        <div class="page-head__actions">
          ${
            vehicles.length
              ? `<select class="select" id="anVehicle" aria-label="Scope" style="min-width:190px">
                   <option value="all"${state.vehicleId === "all" ? " selected" : ""}>All vehicles</option>
                   ${vehicles
                     .map(
                       (v) =>
                         `<option value="${U.esc(v.id)}"${state.vehicleId === v.id ? " selected" : ""}>${U.esc(
                           v.name
                         )}</option>`
                     )
                     .join("")}
                 </select>`
              : ""
          }
          <div class="segmented" role="group" aria-label="Time range">
            ${[3, 6, 12]
              .map(
                (m) =>
                  `<button data-months="${m}" class="${state.months === m ? "is-active" : ""}">${m}M</button>`
              )
              .join("")}
          </div>
        </div>
      </header>`;
  }

  function chartCard(title, sub, canvasId, extra = "") {
    return `
      <article class="chart-card">
        <div class="chart-card__head">
          <div>
            <h3 class="chart-card__title">${U.esc(title)}</h3>
            <div class="chart-card__sub">${U.esc(sub)}</div>
          </div>
          ${extra}
        </div>
        <div class="chart-box"><canvas id="${canvasId}"></canvas></div>
      </article>`;
  }

  /* ---------------------------------------------------------------- mount -- */

  function mount(root) {
    const picker = U.$("#anVehicle", root);
    if (picker) {
      picker.addEventListener("change", (e) => {
        state.vehicleId = e.target.value;
        AC.router.refresh();
      });
    }
    U.$$("[data-months]", root).forEach((btn) =>
      btn.addEventListener("click", () => {
        state.months = Number(btn.dataset.months);
        AC.router.refresh();
      })
    );

    if (!AC.charts.available() || !AC.vehicles.count()) return;

    const months = state.months;
    const filter = scopeFilter();
    const id = scopeId();

    /* 1. Monthly expenses (stacked by category) */
    const stacked = AC.expenses.monthlyByCategory(filter, months);
    if (stacked.series.length) {
      AC.charts.stackedBar("chMonthly", { labels: stacked.labels, series: stacked.series });
    } else {
      const m = AC.expenses.monthly(filter, months);
      AC.charts.bar("chMonthly", {
        labels: m.map((x) => x.label),
        data: m.map((x) => x.value),
        money: true,
        label: "Spend",
      });
    }

    /* 2. Category distribution */
    const cats = AC.expenses.byCategory(filter);
    AC.charts.doughnut("chCategory", {
      labels: cats.map((c) => c.label),
      data: cats.map((c) => c.amount),
      colors: cats.map((c) => c.hex),
    });

    /* 3. Usage */
    const usage = AC.journeys.monthlyDistance(id, months);
    AC.charts.line("chUsage", {
      labels: usage.map((x) => x.label),
      data: usage.map((x) => x.value),
      label: "Distance (km)",
      color: AC.charts.css("--viz-2", "#4aa8ff"),
      suffix: " km",
    });

    /* 4. Odometer growth (primary or selected vehicle) */
    const odoVehicle = id || (AC.vehicles.primary() || {}).id;
    const odo = AC.analytics.odometerGrowth(odoVehicle, months);
    AC.charts.line("chOdometer", {
      labels: odo.map((x) => x.label),
      data: odo.map((x) => x.value),
      label: "Odometer (km)",
      color: AC.charts.css("--viz-3", "#39ff88"),
      suffix: " km",
    });

    /* 5. Maintenance cost by type */
    const byType = AC.analytics.maintenanceCostByType(id);
    AC.charts.bar("chMaintenance", {
      labels: byType.map((x) => x.label),
      data: byType.map((x) => x.value),
      money: true,
      label: "Spend",
    });

    /* 6. Health trend */
    const trendVehicle = AC.vehicles.get(odoVehicle);
    const trend = AC.health.healthTrend(trendVehicle, months);
    AC.charts.line("chHealth", {
      labels: trend.map((x) => x.label),
      data: trend.map((x) => x.value),
      label: "Health score",
      color: AC.charts.css("--viz-4", "#ff9d2e"),
      suffix: "%",
    });

    /* 7. Wash frequency */
    const washes = AC.wash.monthlyFrequency(id, months);
    AC.charts.bar("chWash", {
      labels: washes.map((x) => x.label),
      data: washes.map((x) => x.value),
      label: "Washes",
      color: AC.charts.css("--viz-6", "#22d3ee"),
      integer: true,
    });

    /* 8. Environmental exposure */
    const exposure = AC.analytics.exposureSeries(id, months);
    AC.charts.multiLine("chExposure", {
      labels: exposure.map((x) => x.label),
      series: [
        {
          label: "Avg AQI",
          data: exposure.map((x) => x.aqi),
          color: AC.charts.css("--viz-1", "#e10600"),
        },
        {
          label: "Dust index",
          data: exposure.map((x) => x.dust),
          color: AC.charts.css("--viz-7", "#f5d90a"),
        },
      ],
    });
  }

  return { render, mount, state };
})();
