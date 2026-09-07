/* ==========================================================================
   AutoCare Pro — pages/maintenance.js
   Service schedule (computed) + the record log (stored).
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.maintenance = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;
  const M = AC.maintenance;
  const C = AC.constants;

  let state = { vehicleId: null, statusFilter: "all", typeFilter: "all" };

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
    const vehicle = activeVehicle();

    if (!vehicle) {
      return `
        <section class="page">
          ${header(null)}
          ${UI.emptyState({
            icon: "car",
            title: "No vehicles registered",
            text: "Maintenance records belong to a vehicle. Add one to begin logging services.",
            actionLabel: "Add vehicle",
            actionEvent: "vehicle:new",
          })}
        </section>`;
    }

    const schedule = M.scheduleFor(vehicle, { includeUnrecorded: true });
    const visible = schedule.filter(
      (row) => state.statusFilter === "all" || row.status === state.statusFilter
    );
    const records = M.forVehicle(vehicle.id).filter(
      (r) => state.typeFilter === "all" || r.type === state.typeFilter
    );

    const counts = {
      overdue: schedule.filter((r) => r.status === M.STATUS.OVERDUE).length,
      dueSoon: schedule.filter((r) => r.status === M.STATUS.DUE_SOON).length,
      upcoming: schedule.filter((r) => r.status === M.STATUS.UPCOMING).length,
      unknown: schedule.filter((r) => r.status === M.STATUS.UNKNOWN).length,
    };

    return `
      <section class="page">
        ${header(vehicle)}

        <div class="maintenance-summary stagger">
          ${UI.metricCard({ label: "Overdue", value: counts.overdue, format: "pad", icon: "alert", tone: counts.overdue ? "critical" : "success", foot: "Past interval" })}
          ${UI.metricCard({ label: "Due soon", value: counts.dueSoon, format: "pad", icon: "clock", tone: counts.dueSoon ? "warning" : "", foot: "Within 500 km / 15 days" })}
          ${UI.metricCard({ label: "Upcoming", value: counts.upcoming, format: "pad", icon: "check", foot: "Within interval" })}
          ${UI.metricCard({ label: "Total spend", value: M.totalCost(vehicle.id), format: "money", icon: "rupee", foot: `${records.length} records` })}
        </div>

        ${UI.sectionHead(
          "Service schedule",
          "Computed from the latest record of each type against the manufacturer interval.",
          `<select class="select" id="statusFilter" style="min-width:170px" aria-label="Filter schedule by status">
             <option value="all"${state.statusFilter === "all" ? " selected" : ""}>All statuses</option>
             <option value="overdue"${state.statusFilter === "overdue" ? " selected" : ""}>Overdue</option>
             <option value="due-soon"${state.statusFilter === "due-soon" ? " selected" : ""}>Due soon</option>
             <option value="upcoming"${state.statusFilter === "upcoming" ? " selected" : ""}>Upcoming</option>
             <option value="unknown"${state.statusFilter === "unknown" ? " selected" : ""}>Not recorded</option>
           </select>`
        )}

        ${
          visible.length
            ? `<div class="service-grid">${visible.map((r) => serviceCard(r, vehicle, settings)).join("")}</div>`
            : UI.emptyState({ icon: "filter", title: "Nothing here", text: "No services match this status filter." })
        }

        ${UI.sectionHead(
          "Service records",
          "Everything logged for this vehicle.",
          `<select class="select" id="typeFilter" style="min-width:170px" aria-label="Filter records by type">
             <option value="all">All types</option>
             ${C.MAINTENANCE_TYPES.map(
               (t) => `<option value="${t.key}"${state.typeFilter === t.key ? " selected" : ""}>${t.label}</option>`
             ).join("")}
           </select>`
        )}

        ${records.length ? recordsTable(records, settings) : UI.emptyState({
          icon: "wrench",
          title: "No service records",
          text: "Log your first service to start the due-date and health calculations.",
          actionLabel: "Log maintenance",
          actionEvent: "maintenance:new",
        })}
      </section>`;
  }

  function header(vehicle) {
    const vehicles = AC.vehicles.all();
    return `
      <header class="page-head">
        <div>
          <div class="page-head__eyebrow">Service intelligence</div>
          <h1>Maintenance</h1>
          <p class="page-head__sub">
            AutoCare Pro tracks both deadlines — distance and time — for every service type and
            flags whichever arrives first.
          </p>
        </div>
        <div class="page-head__actions">
          ${
            vehicles.length > 1
              ? `<select class="select" id="vehiclePicker" aria-label="Select vehicle" style="min-width:200px">
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
          <button class="btn btn--primary" data-action="maintenance:new"${
            vehicle ? ` data-vehicle-id="${U.esc(vehicle.id)}"` : ""
          }>${I.get("plus", { size: 16 })}<span>Log maintenance</span></button>
        </div>
      </header>`;
  }

  function serviceCard(row, vehicle, settings) {
    const tone = UI.toneForStatus(row.status);
    const unknown = row.status === M.STATUS.UNKNOWN;

    const primaryNumber = unknown
      ? "—"
      : row.remainingKm !== null
      ? U.formatDistance(Math.abs(row.remainingKm), settings.units, false)
      : Math.abs(row.remainingDays);

    const primaryUnit = unknown
      ? "no record"
      : row.remainingKm !== null
      ? `${U.unitLabel(settings.units)} ${row.remainingKm < 0 ? "past due" : "remaining"}`
      : `days ${row.remainingDays < 0 ? "past due" : "remaining"}`;

    return `
      <article class="service-card service-card--${U.esc(row.status)}">
        <div class="service-card__head">
          <div>
            <h3 class="service-card__type">${U.esc(row.label)}</h3>
            <div class="service-card__meta">
              <span>${row.interval.km ? `${U.formatNumber(row.interval.km)} km` : "—"}</span>
              <span>${row.interval.months ? `${row.interval.months} months` : "—"}</span>
            </div>
          </div>
          ${UI.statusPill(M.STATUS_META[row.status].label, tone)}
        </div>

        <div class="service-card__remaining">
          <span class="n">${U.esc(primaryNumber)}</span>
          <span class="u">${U.esc(primaryUnit)}</span>
        </div>

        ${
          unknown
            ? `<p class="field__hint">No history for this service. Log one to activate tracking.</p>`
            : UI.progressBar({
                label: "Interval used",
                value: Math.round(U.clamp(row.consumed, 0, 1.5) * 100),
                max: 150,
                tone,
                suffix: "%",
              })
        }

        <div class="service-card__meta">
          ${
            row.record
              ? `<span>Last: ${U.formatDate(row.record.date)}</span>
                 <span>${U.formatDistance(row.record.odometer, settings.units)}</span>`
              : ""
          }
          ${row.dueDate ? `<span>Due: ${U.formatDate(row.dueDate)}</span>` : ""}
        </div>

        <button class="btn btn--sm btn--block" data-action="maintenance:new"
                data-vehicle-id="${U.esc(vehicle.id)}" data-type="${U.esc(row.type)}">
          ${I.get("plus", { size: 14 })}<span>Log ${U.esc(row.label.toLowerCase())}</span>
        </button>
      </article>`;
  }

  function recordsTable(records, settings) {
    return `
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Service</th><th>Date</th><th>Odometer</th><th>Cost</th><th>Next due</th><th>Notes</th><th></th>
            </tr>
          </thead>
          <tbody>
            ${records
              .map(
                (r) => `
              <tr>
                <td>
                  <span class="record-type"><span class="record-type__dot"></span>${U.esc(
                    C.maintenanceLabel(r.type)
                  )}</span>
                  ${r.source === "demo" ? ` ${UI.demoFlag()}` : ""}
                </td>
                <td class="num">${U.formatDate(r.date)}</td>
                <td class="num">${U.formatDistance(r.odometer, settings.units)}</td>
                <td class="num">${U.formatCurrency(r.cost)}</td>
                <td class="num text-muted">${
                  r.nextServiceOdometer
                    ? U.formatDistance(r.nextServiceOdometer, settings.units)
                    : r.nextServiceDate
                    ? U.formatDate(r.nextServiceDate)
                    : "Standard interval"
                }</td>
                <td class="text-muted">${U.esc(r.notes || "—")}</td>
                <td>
                  <div class="actions">
                    <button class="btn btn--sm btn--icon" data-action="maintenance:edit" data-id="${U.esc(r.id)}"
                            aria-label="Edit record">${I.get("edit", { size: 14 })}</button>
                    <button class="btn btn--sm btn--icon btn--danger" data-action="maintenance:delete" data-id="${U.esc(
                      r.id
                    )}" aria-label="Delete record">${I.get("trash", { size: 14 })}</button>
                  </div>
                </td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  function mount(root) {
    const picker = U.$("#vehiclePicker", root);
    if (picker) {
      picker.addEventListener("change", (e) => {
        state.vehicleId = e.target.value;
        AC.router.refresh();
      });
    }
    const status = U.$("#statusFilter", root);
    if (status) {
      status.addEventListener("change", (e) => {
        state.statusFilter = e.target.value;
        AC.router.refresh();
      });
    }
    const type = U.$("#typeFilter", root);
    if (type) {
      type.addEventListener("change", (e) => {
        state.typeFilter = e.target.value;
        AC.router.refresh();
      });
    }
  }

  return { render, mount, state };
})();
