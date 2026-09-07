/* ==========================================================================
   AutoCare Pro — vehicles.js
   Vehicle CRUD and the derived "summary" object that every screen renders
   from. Keeping the derivation here means the dashboard, the vehicles page
   and the command palette all agree on what a vehicle's numbers are.
   ========================================================================== */

window.AC = window.AC || {};

AC.vehicles = (function () {
  "use strict";

  const U = AC.utils;
  const S = AC.storage;

  const all = () => U.sortBy(S.list("vehicles"), (v) => (v.isPrimary ? 0 : 1), "asc");

  const get = (id) => S.find("vehicles", id);

  const count = () => S.list("vehicles").length;

  /** The primary vehicle, falling back to the first one on file. */
  function primary() {
    const list = S.list("vehicles");
    return list.find((v) => v.isPrimary) || list[0] || null;
  }

  /** Exactly one vehicle may be primary at a time. */
  function setPrimary(id) {
    S.update((db) => {
      db.vehicles.forEach((v) => {
        v.isPrimary = v.id === id;
      });
    });
    return get(id);
  }

  function create(value) {
    const isFirst = count() === 0;
    const row = S.insert("vehicles", {
      name: value.name,
      make: value.make,
      model: value.model,
      year: Number(value.year),
      fuelType: value.fuelType,
      odometer: Number(value.odometer),
      registration: value.registration || "",
      lastServiceDate: value.lastServiceDate || null,
      lastServiceOdometer: U.isNum(value.lastServiceOdometer)
        ? Number(value.lastServiceOdometer)
        : null,
      lastWashDate: value.lastWashDate || null,
      odometerAtLastWash: U.isNum(value.odometerAtLastWash)
        ? Number(value.odometerAtLastWash)
        : null,
      notes: value.notes || "",
      isPrimary: isFirst,
      source: "user",
    });

    // A baseline service record makes the health and due-date maths meaningful
    // from day one instead of reporting "no history".
    if (value.lastServiceDate && U.isNum(value.lastServiceOdometer)) {
      S.insert("maintenanceRecords", {
        vehicleId: row.id,
        type: "general",
        date: value.lastServiceDate,
        odometer: Number(value.lastServiceOdometer),
        cost: 0,
        notes: "Baseline service recorded when the vehicle was added.",
        nextServiceDate: null,
        nextServiceOdometer: null,
        source: "baseline",
      });
    }

    return row;
  }

  function update(id, value) {
    return S.patch("vehicles", id, {
      name: value.name,
      make: value.make,
      model: value.model,
      year: Number(value.year),
      fuelType: value.fuelType,
      odometer: Number(value.odometer),
      registration: value.registration || "",
      lastServiceDate: value.lastServiceDate || null,
      lastServiceOdometer: U.isNum(value.lastServiceOdometer)
        ? Number(value.lastServiceOdometer)
        : null,
      lastWashDate: value.lastWashDate || null,
      odometerAtLastWash: U.isNum(value.odometerAtLastWash)
        ? Number(value.odometerAtLastWash)
        : null,
      notes: value.notes || "",
    });
  }

  /** Removes the vehicle and everything attached to it, then repairs primary. */
  const remove = (id) => S.removeVehicleCascade(id);

  /**
   * Everything a card needs about a vehicle, computed once.
   * `env` is optional — pass the current reading to avoid recomputing it.
   */
  function summary(vehicle, env = null) {
    if (!vehicle) return null;
    const health = AC.health.calculateVehicleHealth(vehicle);
    const next = AC.maintenance.nextService(vehicle);
    const washScore = AC.wash.calculateWashScore(vehicle, env);
    const schedule = AC.maintenance.scheduleFor(vehicle);

    return {
      vehicle,
      health,
      next,
      washScore,
      schedule,
      overdue: schedule.filter((r) => r.status === AC.maintenance.STATUS.OVERDUE).length,
      dueSoon: schedule.filter((r) => r.status === AC.maintenance.STATUS.DUE_SOON).length,
      maintenanceCost: AC.maintenance.totalCost(vehicle.id),
      expenseTotal: AC.expenses.total({ vehicleId: vehicle.id }),
      daysSinceWash: U.daysBetween(vehicle.lastWashDate),
    };
  }

  const displayName = (v) => (v ? `${v.make} ${v.model}`.trim() || v.name : "—");

  return { all, get, count, primary, setPrimary, create, update, remove, summary, displayName };
})();
