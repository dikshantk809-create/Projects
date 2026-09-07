/* ==========================================================================
   AutoCare Pro — pages/expenses.js
   Expense ledger with category breakdown and a spend chart.
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.expenses = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;
  const C = AC.constants;

  let state = { vehicleId: "all", category: "all", range: "all", limit: 25 };

  function filterObj() {
    const f = {};
    if (state.vehicleId !== "all") f.vehicleId = state.vehicleId;
    if (state.category !== "all") f.category = state.category;
    if (state.range !== "all") {
      const days = Number(state.range);
      f.from = U.isoDate(U.addDays(U.today(), -days));
    }
    return f;
  }

  function render() {
    const vehicles = AC.vehicles.all();
    if (!vehicles.length) {
      return `
        <section class="page">
          ${header()}
          ${UI.emptyState({
            icon: "rupee",
            title: "No vehicles registered",
            text: "Expenses are tracked per vehicle. Add one to begin recording costs.",
            actionLabel: "Add vehicle",
            actionEvent: "vehicle:new",
          })}
        </section>`;
    }

    const filter = filterObj();
    const rows = AC.expenses.query(filter);
    const cats = AC.expenses.byCategory(filter);
    const grand = U.sum(rows, (e) => e.amount);

    const scope = state.vehicleId === "all" ? {} : { vehicleId: state.vehicleId };

    return `
      <section class="page">
        ${header()}
        ${toolbar(vehicles, Math.min(state.limit, rows.length), rows.length)}

        <div class="expense-summary stagger">
          ${UI.metricCard({ label: "Total expenses", value: AC.expenses.total(scope), format: "money", icon: "rupee", foot: "All time" })}
          ${UI.metricCard({ label: "This month", value: AC.expenses.monthToDate(scope), format: "money", icon: "calendar", foot: U.monthLabel(U.formatMonthKey(U.today())) })}
          ${UI.metricCard({ label: "Fuel", value: AC.expenses.total({ ...scope, category: "fuel" }), format: "money", icon: "fuel", foot: "Recorded fills" })}
          ${UI.metricCard({ label: "Maintenance", value: AC.expenses.total({ ...scope, category: "maintenance" }) + AC.expenses.total({ ...scope, category: "repair" }), format: "money", icon: "wrench", foot: "Service + repair" })}
          ${UI.metricCard({ label: "Wash", value: AC.expenses.total({ ...scope, category: "wash" }), format: "money", icon: "droplet", foot: "Cleaning spend" })}
        </div>

        <div class="grid grid--2">
          <article class="chart-card">
            <div class="chart-card__head">
              <div>
                <h3 class="chart-card__title">Monthly spend</h3>
                <div class="chart-card__sub">Last 6 months, filtered by the controls above</div>
              </div>
            </div>
            <div class="chart-box"><canvas id="expMonthly"></canvas></div>
          </article>

          <article class="card">
            <div class="card__head">
              <span class="card__title">Category breakdown</span>
              <span class="count-note">${U.formatCurrency(grand)}</span>
            </div>
            ${
              cats.length
                ? `<div class="breakdown">${cats
                    .map(
                      (c) => `
                  <div class="breakdown__row">
                    <div class="breakdown__head">
                      <span class="cat-chip"><span class="cat-chip__dot" style="background:${c.hex}"></span>${U.esc(
                        c.label
                      )}</span>
                      <span>
                        <span class="money">${U.formatCurrency(c.amount)}</span>
                        <span class="breakdown__pct">${Math.round(c.share * 100)}%</span>
                      </span>
                    </div>
                    <div class="bar__track">
                      <div class="bar__fill" data-width="${c.share * 100}"
                           style="background:${c.hex};box-shadow:0 0 12px -2px ${c.hex}"></div>
                    </div>
                  </div>`
                    )
                    .join("")}</div>`
                : `<p class="text-muted">No expenses match the current filters.</p>`
            }
          </article>
        </div>

        ${UI.sectionHead("Expense ledger", `${rows.length} record${rows.length === 1 ? "" : "s"}`)}
        ${
          rows.length
            ? table(rows.slice(0, state.limit)) +
              (rows.length > state.limit
                ? `<div class="flex mt-4" style="justify-content:center">
                     <button class="btn" id="expMore">Load ${Math.min(25, rows.length - state.limit)} more</button>
                   </div>`
                : "")
            : UI.emptyState({
                icon: "rupee",
                title: "No expenses recorded",
                text: "Record fuel, maintenance, wash or insurance costs to build the analytics.",
                actionLabel: "Record expense",
                actionEvent: "expense:new",
              })
        }
      </section>`;
  }

  function header() {
    return `
      <header class="page-head">
        <div>
          <div class="page-head__eyebrow">Cost of ownership</div>
          <h1>Expenses</h1>
          <p class="page-head__sub">
            Every rupee spent on the fleet, grouped by category and vehicle.
          </p>
        </div>
        <div class="page-head__actions">
          <button class="btn btn--primary" data-action="expense:new">
            ${I.get("plus", { size: 16 })}<span>Record expense</span>
          </button>
        </div>
      </header>`;
  }

  /** Filters live in their own toolbar so the page title is never squeezed. */
  function toolbar(vehicles, shown, total) {
    return `
      <div class="toolbar">
        <select class="select" id="expVehicle" aria-label="Filter by vehicle">
          <option value="all"${state.vehicleId === "all" ? " selected" : ""}>All vehicles</option>
          ${vehicles
            .map(
              (v) =>
                `<option value="${U.esc(v.id)}"${state.vehicleId === v.id ? " selected" : ""}>${U.esc(
                  v.name
                )}</option>`
            )
            .join("")}
        </select>
        <select class="select" id="expCategory" aria-label="Filter by category">
          <option value="all"${state.category === "all" ? " selected" : ""}>All categories</option>
          ${C.EXPENSE_CATEGORIES.map(
            (c) => `<option value="${c.key}"${state.category === c.key ? " selected" : ""}>${c.label}</option>`
          ).join("")}
        </select>
        <select class="select" id="expRange" aria-label="Filter by period">
          <option value="all"${state.range === "all" ? " selected" : ""}>All time</option>
          <option value="30"${state.range === "30" ? " selected" : ""}>Last 30 days</option>
          <option value="90"${state.range === "90" ? " selected" : ""}>Last 90 days</option>
          <option value="365"${state.range === "365" ? " selected" : ""}>Last year</option>
        </select>
        <div class="toolbar__spacer"></div>
        <span class="count-note">Showing ${U.pad2(shown)} of ${U.pad2(total)}</span>
      </div>`;
  }

  function table(rows) {
    const vehicleName = (id) => {
      const v = AC.vehicles.get(id);
      return v ? v.name : "Deleted vehicle";
    };
    return `
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Date</th><th>Vehicle</th><th>Category</th><th>Description</th><th>Amount</th><th></th></tr>
          </thead>
          <tbody>
            ${rows
              .map((e) => {
                const cat = C.EXPENSE_BY_KEY[e.category] || C.EXPENSE_BY_KEY.other;
                return `
                <tr>
                  <td class="num">${U.formatDate(e.date)}</td>
                  <td>${U.esc(vehicleName(e.vehicleId))} ${e.source === "demo" ? UI.demoFlag() : ""}</td>
                  <td><span class="cat-chip"><span class="cat-chip__dot" style="background:${cat.hex}"></span>${U.esc(
                  cat.label
                )}</span></td>
                  <td class="text-muted">${U.esc(e.description || "—")}</td>
                  <td class="num money">${U.formatCurrency(e.amount)}</td>
                  <td>
                    <div class="actions">
                      <button class="btn btn--sm btn--icon" data-action="expense:edit" data-id="${U.esc(e.id)}"
                              aria-label="Edit expense">${I.get("edit", { size: 14 })}</button>
                      <button class="btn btn--sm btn--icon btn--danger" data-action="expense:delete" data-id="${U.esc(
                        e.id
                      )}" aria-label="Delete expense">${I.get("trash", { size: 14 })}</button>
                    </div>
                  </td>
                </tr>`;
              })
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  function mount(root) {
    const bind = (id, key) => {
      const el = U.$(id, root);
      if (el) {
        el.addEventListener("change", (e) => {
          state[key] = e.target.value;
          state.limit = 25; // a new filter starts a fresh page
          AC.router.refresh();
        });
      }
    };
    bind("#expVehicle", "vehicleId");
    bind("#expCategory", "category");
    bind("#expRange", "range");

    const more = U.$("#expMore", root);
    if (more) {
      more.addEventListener("click", () => {
        state.limit += 25;
        AC.router.refresh();
      });
    }

    if (AC.charts.available() && AC.vehicles.count()) {
      const series = AC.expenses.monthly(filterObj(), 6);
      AC.charts.bar("expMonthly", {
        labels: series.map((s) => s.label),
        data: series.map((s) => s.value),
        money: true,
        label: "Spend",
      });
    }
  }

  return { render, mount, state };
})();
