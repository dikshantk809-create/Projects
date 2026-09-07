/* ==========================================================================
   AutoCare Pro — forms.js
   Every create/edit dialog in the application. Centralising them means the
   dashboard quick-actions, the command palette and the individual pages all
   open the *same* validated form instead of three near-copies.

   Flow for each dialog:
       build markup -> open modal -> on submit: validate -> persist ->
       toast -> refresh the current route
   ========================================================================== */

window.AC = window.AC || {};

AC.forms = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const UI = AC.ui;

  const vehicleOptions = () =>
    AC.vehicles.all().map((v) => ({ value: v.id, label: `${v.name} · ${v.registration || "No reg."}` }));

  const todayIso = () => U.isoDate(U.today());

  function guardNoVehicles() {
    if (AC.vehicles.count() === 0) {
      UI.toast("Add a vehicle first — records must belong to a vehicle.", {
        type: "warning",
        title: "No vehicles yet",
      });
      return true;
    }
    return false;
  }

  /* ============================================================ vehicle === */

  function vehicleModal(vehicleId = null) {
    const editing = vehicleId ? AC.vehicles.get(vehicleId) : null;
    const v = editing || {};

    const body = `
      <form id="vehicleForm" novalidate>
        <div class="form-grid">
          ${UI.field({ name: "name", label: "Vehicle name", value: v.name || "", required: true, attrs: 'maxlength="40" placeholder="Hyundai i20"' })}
          ${UI.field({ name: "registration", label: "Registration number", value: v.registration || "", attrs: 'maxlength="15" placeholder="PB11 CX 4821"' })}
          ${UI.field({ name: "make", label: "Make", value: v.make || "", required: true, attrs: 'maxlength="30" placeholder="Hyundai"' })}
          ${UI.field({ name: "model", label: "Model", value: v.model || "", required: true, attrs: 'maxlength="40" placeholder="i20 Sportz"' })}
          ${UI.field({ name: "year", label: "Model year", type: "number", value: v.year || "", required: true, attrs: `min="1950" max="${new Date().getFullYear() + 1}" placeholder="2022"` })}
          ${UI.selectField({
            name: "fuelType",
            label: "Fuel type",
            required: true,
            value: v.fuelType || "Petrol",
            options: C.FUEL_TYPES.map((f) => ({ value: f, label: f })),
          })}
          ${UI.field({ name: "odometer", label: "Current odometer (km)", type: "number", value: v.odometer ?? "", required: true, attrs: 'min="0" step="1" placeholder="35240"' })}
          ${UI.field({ name: "lastServiceDate", label: "Last service date", type: "date", value: v.lastServiceDate || "", attrs: `max="${todayIso()}"` })}
          ${UI.field({ name: "lastServiceOdometer", label: "Odometer at last service (km)", type: "number", value: v.lastServiceOdometer ?? "", attrs: 'min="0" step="1"' })}
          ${UI.field({ name: "lastWashDate", label: "Last wash date", type: "date", value: v.lastWashDate || "", attrs: `max="${todayIso()}"` })}
          ${UI.field({ name: "odometerAtLastWash", label: "Odometer at last wash (km)", type: "number", value: v.odometerAtLastWash ?? "", attrs: 'min="0" step="1"', hint: "Improves wash-score accuracy" })}
        </div>
        ${UI.textareaField({ name: "notes", label: "Notes", value: v.notes || "" })}
      </form>`;

    UI.openModal({
      title: editing ? "Edit vehicle" : "Add vehicle",
      subtitle: editing
        ? "Update the record. Health and service intervals recalculate immediately."
        : "Service history and wash dates are optional, but they make the intelligence far more accurate.",
      body,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Cancel</button>
        <button class="btn btn--primary" id="saveVehicle">${editing ? "Save changes" : "Add vehicle"}</button>`,
      onMount(modal) {
        const form = modal.querySelector("#vehicleForm");
        const submit = () => {
          const raw = UI.formValues(form);
          const result = AC.validation.validateVehicle(raw, {
            vehicles: AC.vehicles.all(),
            editingId: vehicleId,
          });
          if (!result.valid) {
            UI.showErrors(form, result.errors);
            return;
          }
          if (editing) {
            AC.vehicles.update(vehicleId, result.value);
            UI.toast(`${result.value.name} updated.`);
          } else {
            AC.vehicles.create(result.value);
            UI.toast(`${result.value.name} added to your garage.`);
          }
          UI.closeModal();
          AC.app.refreshAll();
        };
        modal.querySelector("#saveVehicle").addEventListener("click", submit);
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          submit();
        });
      },
    });
  }

  /* ======================================================== maintenance === */

  function maintenanceModal(prefill = {}) {
    if (guardNoVehicles()) return;
    const editing = prefill.recordId ? AC.storage.find("maintenanceRecords", prefill.recordId) : null;
    const r = editing || {};
    const vehicleId = r.vehicleId || prefill.vehicleId || (AC.vehicles.primary() || {}).id || "";
    const vehicle = AC.vehicles.get(vehicleId);

    const body = `
      <form id="maintenanceForm" novalidate>
        <div class="form-grid">
          ${UI.selectField({ name: "vehicleId", label: "Vehicle", required: true, value: vehicleId, options: vehicleOptions() })}
          ${UI.selectField({
            name: "type",
            label: "Service type",
            required: true,
            value: r.type || prefill.type || "engine_oil",
            options: C.MAINTENANCE_TYPES.map((t) => ({ value: t.key, label: t.label })),
          })}
          ${UI.field({ name: "date", label: "Service date", type: "date", value: r.date || todayIso(), required: true, attrs: `max="${todayIso()}"` })}
          ${UI.field({ name: "odometer", label: "Odometer (km)", type: "number", value: r.odometer ?? (vehicle ? vehicle.odometer : ""), required: true, attrs: 'min="0" step="1"' })}
          ${UI.field({ name: "cost", label: "Cost (₹)", type: "number", value: r.cost ?? "", attrs: 'min="0" step="1" placeholder="2450"' })}
          ${UI.field({ name: "nextServiceOdometer", label: "Next service odometer (km)", type: "number", value: r.nextServiceOdometer ?? "", attrs: 'min="0" step="1"', hint: "Leave blank to use the standard interval" })}
          ${UI.field({ name: "nextServiceDate", label: "Next service date", type: "date", value: r.nextServiceDate || "", hint: "Leave blank to use the standard interval" })}
        </div>
        ${UI.textareaField({ name: "notes", label: "Notes", value: r.notes || "" })}
        ${editing ? "" : `<div class="mt-4">${UI.switchField({ name: "logExpense", label: "Also record this cost as an expense", checked: true })}</div>`}
      </form>`;

    UI.openModal({
      title: editing ? "Edit service record" : "Log maintenance",
      subtitle: "Due dates, health scores and alerts all recalculate from these records.",
      body,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Cancel</button>
        <button class="btn btn--primary" id="saveMaintenance">${editing ? "Save changes" : "Save record"}</button>`,
      onMount(modal) {
        const form = modal.querySelector("#maintenanceForm");

        // Keep the odometer suggestion in step with the selected vehicle.
        form.querySelector('[name="vehicleId"]').addEventListener("change", (e) => {
          const veh = AC.vehicles.get(e.target.value);
          const odo = form.querySelector('[name="odometer"]');
          if (veh && !odo.value) odo.value = veh.odometer;
        });

        const submit = () => {
          const raw = UI.formValues(form);
          const result = AC.validation.validateMaintenance(raw, { vehicles: AC.vehicles.all() });
          if (!result.valid) {
            UI.showErrors(form, result.errors);
            return;
          }
          if (editing) {
            AC.maintenance.updateRecord(prefill.recordId, result.value);
            UI.toast("Maintenance record updated.");
          } else {
            AC.maintenance.addRecord(result.value);
            UI.toast(`${C.maintenanceLabel(result.value.type)} recorded.`);
          }
          UI.closeModal();
          AC.app.refreshAll();
        };
        modal.querySelector("#saveMaintenance").addEventListener("click", submit);
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          submit();
        });
      },
    });
  }

  /* ============================================================ expense === */

  function expenseModal(prefill = {}) {
    if (guardNoVehicles()) return;
    const editing = prefill.expenseId ? AC.storage.find("expenses", prefill.expenseId) : null;
    const e = editing || {};

    const body = `
      <form id="expenseForm" novalidate>
        <div class="form-grid">
          ${UI.selectField({
            name: "vehicleId",
            label: "Vehicle",
            required: true,
            value: e.vehicleId || prefill.vehicleId || (AC.vehicles.primary() || {}).id || "",
            options: vehicleOptions(),
          })}
          ${UI.selectField({
            name: "category",
            label: "Category",
            required: true,
            value: e.category || prefill.category || "fuel",
            options: C.EXPENSE_CATEGORIES.map((c) => ({ value: c.key, label: c.label })),
          })}
          ${UI.field({ name: "amount", label: "Amount (₹)", type: "number", value: e.amount ?? "", required: true, attrs: 'min="1" step="1" placeholder="2100"' })}
          ${UI.field({ name: "date", label: "Date", type: "date", value: e.date || todayIso(), required: true, attrs: `max="${todayIso()}"` })}
        </div>
        ${UI.textareaField({ name: "description", label: "Description", value: e.description || "" })}
      </form>`;

    UI.openModal({
      title: editing ? "Edit expense" : "Record expense",
      size: "sm",
      body,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Cancel</button>
        <button class="btn btn--primary" id="saveExpense">${editing ? "Save changes" : "Save expense"}</button>`,
      onMount(modal) {
        const form = modal.querySelector("#expenseForm");
        const submit = () => {
          const raw = UI.formValues(form);
          const result = AC.validation.validateExpense(raw, { vehicles: AC.vehicles.all() });
          if (!result.valid) {
            UI.showErrors(form, result.errors);
            return;
          }
          if (editing) {
            AC.expenses.update(prefill.expenseId, result.value);
            UI.toast("Expense updated.");
          } else {
            AC.expenses.create(result.value);
            UI.toast(`${U.formatCurrency(result.value.amount)} recorded.`);
          }
          UI.closeModal();
          AC.app.refreshAll();
        };
        modal.querySelector("#saveExpense").addEventListener("click", submit);
        form.addEventListener("submit", (ev) => {
          ev.preventDefault();
          submit();
        });
      },
    });
  }

  /* ============================================================ journey === */

  function journeyModal(prefill = {}) {
    if (guardNoVehicles()) return;
    const body = `
      <form id="journeyForm" novalidate>
        <div class="form-grid">
          ${UI.selectField({
            name: "vehicleId",
            label: "Vehicle",
            required: true,
            value: prefill.vehicleId || (AC.vehicles.primary() || {}).id || "",
            options: vehicleOptions(),
          })}
          ${UI.field({ name: "date", label: "Date", type: "date", value: todayIso(), required: true, attrs: `max="${todayIso()}"` })}
          ${UI.field({ name: "from", label: "From", value: "", required: true, attrs: 'maxlength="40" placeholder="Patiala"' })}
          ${UI.field({ name: "to", label: "To", value: "", required: true, attrs: 'maxlength="40" placeholder="Chandigarh"' })}
          ${UI.field({ name: "distanceKm", label: "Distance (km)", type: "number", value: "", required: true, attrs: 'min="1" step="1" placeholder="65"' })}
          ${UI.field({ name: "avgAqi", label: "Average AQI on route", type: "number", value: "", attrs: 'min="0" max="500" step="1"', hint: "Optional — leave blank to use the environment reading" })}
          ${UI.selectField({
            name: "dustLevel",
            label: "Road dust",
            value: "moderate",
            options: AC.journeys.DUST_LEVELS.map((d) => ({ value: d.key, label: d.label })),
          })}
        </div>
        ${UI.banner(
          "Logging a journey advances the vehicle odometer by the distance entered.",
          "info",
          "info"
        )}
      </form>`;

    UI.openModal({
      title: "Log journey",
      subtitle: "Journeys feed environmental exposure and the wash-score usage factor.",
      body,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Cancel</button>
        <button class="btn btn--primary" id="saveJourney">Save journey</button>`,
      onMount(modal) {
        const form = modal.querySelector("#journeyForm");
        const submit = () => {
          const raw = UI.formValues(form);
          const result = AC.validation.validateJourney(raw, { vehicles: AC.vehicles.all() });
          if (!result.valid) {
            UI.showErrors(form, result.errors);
            return;
          }
          AC.journeys.add(result.value);
          UI.toast(`${result.value.from} → ${result.value.to} logged.`);
          UI.closeModal();
          AC.app.refreshAll();
        };
        modal.querySelector("#saveJourney").addEventListener("click", submit);
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          submit();
        });
      },
    });
  }

  /* =============================================================== wash === */

  function washModal(prefill = {}) {
    if (guardNoVehicles()) return;
    const vehicleId = prefill.vehicleId || (AC.vehicles.primary() || {}).id || "";
    const vehicle = AC.vehicles.get(vehicleId);

    const body = `
      <form id="washForm" novalidate>
        <div class="form-grid">
          ${UI.selectField({ name: "vehicleId", label: "Vehicle", required: true, value: vehicleId, options: vehicleOptions() })}
          ${UI.field({ name: "date", label: "Wash date", type: "date", value: todayIso(), required: true, attrs: `max="${todayIso()}"` })}
          ${UI.field({ name: "odometer", label: "Odometer (km)", type: "number", value: vehicle ? vehicle.odometer : "", attrs: 'min="0" step="1"' })}
          ${UI.field({ name: "cost", label: "Cost (₹)", type: "number", value: "", attrs: 'min="0" step="1" placeholder="250"' })}
        </div>
        <div class="mt-4">${UI.switchField({ name: "logExpense", label: "Also record this cost as an expense", checked: true })}</div>
      </form>`;

    UI.openModal({
      title: "Record wash",
      size: "sm",
      subtitle: "Recording a wash resets the time and usage factors of the wash score.",
      body,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Cancel</button>
        <button class="btn btn--primary" id="saveWash">Save wash</button>`,
      onMount(modal) {
        const form = modal.querySelector("#washForm");
        const submit = () => {
          const raw = UI.formValues(form);
          const result = AC.validation.validateWash(raw, { vehicles: AC.vehicles.all() });
          if (!result.valid) {
            UI.showErrors(form, result.errors);
            return;
          }
          AC.wash.recordWash(result.value);
          UI.toast("Wash recorded. Wash score recalculated.");
          UI.closeModal();
          AC.app.refreshAll();
        };
        modal.querySelector("#saveWash").addEventListener("click", submit);
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          submit();
        });
      },
    });
  }

  /* ====================================================== vehicle detail == */

  function vehicleDetailModal(vehicleId) {
    const vehicle = AC.vehicles.get(vehicleId);
    if (!vehicle) return;
    const settings = AC.storage.getSettings();
    const s = AC.vehicles.summary(vehicle, AC.environment.current());
    const kv = (k, v) => `<div class="kv"><span class="kv__k">${U.esc(k)}</span><span class="kv__v">${v}</span></div>`;

    const schedule = s.schedule
      .slice(0, 6)
      .map(
        (row) => `
        <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--border-soft)">
          <span>${U.esc(row.label)}</span>
          <span class="flex gap-3" style="align-items:center">
            <span class="mono text-muted" style="font-size:var(--fs-xs)">${
              row.remainingKm === null ? "—" : U.formatDistance(row.remainingKm, settings.units)
            }</span>
            ${UI.statusPill(AC.maintenance.STATUS_META[row.status].label, UI.toneForStatus(row.status))}
          </span>
        </div>`
      )
      .join("");

    UI.openModal({
      title: vehicle.name,
      subtitle: `${vehicle.make} ${vehicle.model} · ${vehicle.year} · ${vehicle.fuelType}`,
      size: "lg",
      body: `
        <div class="vehicle-detail__grid">
          ${kv("Odometer", U.formatDistance(vehicle.odometer, settings.units))}
          ${kv("Registration", U.esc(vehicle.registration || "—"))}
          ${kv("Health", `${s.health.overall}% · ${s.health.band.label}`)}
          ${kv("Wash score", `${s.washScore.score}/100 · ${s.washScore.status}`)}
          ${kv("Last service", U.formatDate(vehicle.lastServiceDate))}
          ${kv("Last wash", vehicle.lastWashDate ? U.relativeDays(vehicle.lastWashDate) : "—")}
          ${kv("Total spend", U.formatCurrency(s.expenseTotal))}
          ${kv("Maintenance spend", U.formatCurrency(s.maintenanceCost))}
        </div>

        <div class="divider"></div>
        <h3 class="card__title" style="margin-bottom:8px">Service schedule</h3>
        ${schedule || '<p class="text-muted">No maintenance recorded yet.</p>'}

        ${vehicle.notes ? `<div class="divider"></div><p>${U.esc(vehicle.notes)}</p>` : ""}
      `,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Close</button>
        <button class="btn" id="detailMaintenance">Log service</button>
        <button class="btn btn--primary" id="detailEdit">Edit vehicle</button>`,
      onMount(modal) {
        modal.querySelector("#detailEdit").addEventListener("click", () => {
          UI.closeModal(true);
          vehicleModal(vehicleId);
        });
        modal.querySelector("#detailMaintenance").addEventListener("click", () => {
          UI.closeModal(true);
          maintenanceModal({ vehicleId });
        });
      },
    });
  }

  return {
    vehicleModal,
    maintenanceModal,
    expenseModal,
    journeyModal,
    washModal,
    vehicleDetailModal,
  };
})();
