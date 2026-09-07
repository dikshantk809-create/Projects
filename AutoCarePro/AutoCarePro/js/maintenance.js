/* ==========================================================================
   AutoCare Pro — maintenance.js
   Maintenance records + the "when is this due?" intelligence.

   ALGORITHM — Service due calculation
   ----------------------------------
   For every serviceable type we take the most recent record for the vehicle
   and derive two independent deadlines:

     dueOdometer = record.nextServiceOdometer  ?? record.odometer + interval.km
     dueDate     = record.nextServiceDate      ?? record.date + interval.months

   Remaining distance and remaining days are then compared against the
   thresholds in constants.js:

     remainingKm < 0   OR remainingDays < 0   -> OVERDUE
     remainingKm <= 500 OR remainingDays <= 15 -> DUE SOON
     otherwise                                 -> UPCOMING

   Whichever deadline is closer decides the status, so a car that is driven
   rarely is still flagged on time, and a car driven hard is flagged early.
   ========================================================================== */

window.AC = window.AC || {};

AC.maintenance = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const S = AC.storage;

  const STATUS = {
    OVERDUE: "overdue",
    DUE_SOON: "due-soon",
    UPCOMING: "upcoming",
    UNKNOWN: "unknown",
  };

  const STATUS_META = {
    [STATUS.OVERDUE]: { label: "OVERDUE", tone: "critical", rank: 0 },
    [STATUS.DUE_SOON]: { label: "DUE SOON", tone: "warning", rank: 1 },
    [STATUS.UPCOMING]: { label: "UPCOMING", tone: "success", rank: 2 },
    [STATUS.UNKNOWN]: { label: "NOT RECORDED", tone: "muted", rank: 3 },
  };

  /* ------------------------------------------------------------ queries -- */

  const all = () => S.list("maintenanceRecords");

  const forVehicle = (vehicleId) =>
    U.sortBy(all().filter((r) => r.vehicleId === vehicleId), (r) => r.date, "desc");

  /** Most recent record per service type for one vehicle. */
  function latestByType(vehicleId) {
    const map = {};
    forVehicle(vehicleId).forEach((rec) => {
      const prev = map[rec.type];
      if (!prev || U.toDate(rec.date) > U.toDate(prev.date)) map[rec.type] = rec;
    });
    return map;
  }

  /* ---------------------------------------------------------- algorithm -- */

  /**
   * Compute the due-state of one service type for one vehicle.
   * Returns null when the type has no interval (repairs, "other").
   */
  function statusFor(vehicle, typeDef, record) {
    if (!typeDef || (!typeDef.km && !typeDef.months)) return null;

    if (!record) {
      return {
        type: typeDef.key,
        label: typeDef.label,
        system: typeDef.system,
        status: STATUS.UNKNOWN,
        remainingKm: null,
        remainingDays: null,
        dueOdometer: null,
        dueDate: null,
        consumed: 0,
        interval: { km: typeDef.km, months: typeDef.months },
        record: null,
      };
    }

    const odo = Number(vehicle.odometer) || 0;

    const dueOdometer = U.isNum(record.nextServiceOdometer)
      ? Number(record.nextServiceOdometer)
      : typeDef.km
      ? (Number(record.odometer) || 0) + typeDef.km
      : null;

    const dueDate = record.nextServiceDate
      ? U.toDate(record.nextServiceDate)
      : typeDef.months
      ? U.addMonths(record.date, typeDef.months)
      : null;

    const remainingKm = dueOdometer === null ? null : dueOdometer - odo;
    const remainingDays = dueDate === null ? null : -U.daysBetween(dueDate);

    // Fraction of the interval already consumed — drives the progress bar.
    const kmConsumed =
      dueOdometer !== null && typeDef.km
        ? U.clamp((odo - (Number(record.odometer) || 0)) / typeDef.km, 0, 2)
        : 0;
    const dayConsumed =
      dueDate !== null && typeDef.months
        ? U.clamp(U.daysBetween(record.date) / (typeDef.months * 30.44), 0, 2)
        : 0;
    const consumed = Math.max(kmConsumed, dayConsumed);

    let status = STATUS.UPCOMING;
    const overdue =
      (remainingKm !== null && remainingKm < 0) || (remainingDays !== null && remainingDays < 0);
    const dueSoon =
      (remainingKm !== null && remainingKm <= C.SERVICE_THRESHOLDS.dueSoonKm) ||
      (remainingDays !== null && remainingDays <= C.SERVICE_THRESHOLDS.dueSoonDays);

    if (overdue) status = STATUS.OVERDUE;
    else if (dueSoon) status = STATUS.DUE_SOON;

    return {
      type: typeDef.key,
      label: typeDef.label,
      system: typeDef.system,
      status,
      remainingKm,
      remainingDays,
      dueOdometer,
      dueDate: dueDate ? U.isoDate(dueDate) : null,
      consumed,
      interval: { km: typeDef.km, months: typeDef.months },
      record,
    };
  }

  /**
   * Full service schedule for a vehicle, most urgent first.
   * `includeUnrecorded` adds types the owner has never logged so the UI can
   * invite them to record a baseline.
   */
  function scheduleFor(vehicle, { includeUnrecorded = false } = {}) {
    if (!vehicle) return [];
    const latest = latestByType(vehicle.id);
    const rows = [];

    C.MAINTENANCE_TYPES.forEach((typeDef) => {
      const rec = latest[typeDef.key];
      if (!rec && !includeUnrecorded) return;
      const st = statusFor(vehicle, typeDef, rec || null);
      if (st) rows.push(st);
    });

    return rows.sort((a, b) => {
      const rank = STATUS_META[a.status].rank - STATUS_META[b.status].rank;
      if (rank !== 0) return rank;
      const ak = a.remainingKm === null ? Infinity : a.remainingKm;
      const bk = b.remainingKm === null ? Infinity : b.remainingKm;
      return ak - bk;
    });
  }

  /** The single most urgent service for a vehicle (used on the hero card). */
  function nextService(vehicle) {
    const rows = scheduleFor(vehicle).filter((r) => r.status !== STATUS.UNKNOWN);
    return rows.length ? rows[0] : null;
  }

  /** Aggregate due/overdue counts across a fleet — powers dashboard metrics. */
  function fleetSummary(vehicles) {
    let dueSoon = 0;
    let overdue = 0;
    const items = [];
    vehicles.forEach((v) => {
      scheduleFor(v).forEach((row) => {
        if (row.status === STATUS.OVERDUE) {
          overdue += 1;
          items.push({ vehicle: v, row });
        } else if (row.status === STATUS.DUE_SOON) {
          dueSoon += 1;
          items.push({ vehicle: v, row });
        }
      });
    });
    return { dueSoon, overdue, items };
  }

  /* -------------------------------------------------------------- writes -- */

  /**
   * Persist a maintenance record. Side effects, all intentional:
   *   - the vehicle's odometer moves forward if the record is newer
   *   - lastServiceDate / lastServiceOdometer are refreshed
   *   - an optional linked expense is created in the same transaction
   */
  function addRecord(value) {
    const record = S.insert("maintenanceRecords", {
      vehicleId: value.vehicleId,
      type: value.type,
      date: value.date,
      odometer: Number(value.odometer),
      cost: Number(value.cost) || 0,
      notes: value.notes || "",
      nextServiceDate: value.nextServiceDate || null,
      nextServiceOdometer: U.isNum(value.nextServiceOdometer)
        ? Number(value.nextServiceOdometer)
        : null,
      source: "user",
    });

    S.update((db) => {
      const v = db.vehicles.find((x) => x.id === value.vehicleId);
      if (!v) return;
      if (Number(value.odometer) > (Number(v.odometer) || 0)) v.odometer = Number(value.odometer);
      const prevDate = U.toDate(v.lastServiceDate);
      const thisDate = U.toDate(value.date);
      if (!prevDate || (thisDate && thisDate >= prevDate)) {
        v.lastServiceDate = value.date;
        v.lastServiceOdometer = Number(value.odometer);
      }
    });

    if (value.logExpense && Number(value.cost) > 0) {
      S.insert("expenses", {
        vehicleId: value.vehicleId,
        category: value.type === "repair" ? "repair" : "maintenance",
        amount: Number(value.cost),
        date: value.date,
        description: `${C.maintenanceLabel(value.type)} — logged with service record`,
        linkedRecordId: record.id,
        source: "user",
      });
    }

    return record;
  }

  function updateRecord(id, value) {
    return S.patch("maintenanceRecords", id, {
      type: value.type,
      date: value.date,
      odometer: Number(value.odometer),
      cost: Number(value.cost) || 0,
      notes: value.notes || "",
      nextServiceDate: value.nextServiceDate || null,
      nextServiceOdometer: U.isNum(value.nextServiceOdometer)
        ? Number(value.nextServiceOdometer)
        : null,
    });
  }

  /** Deleting a record also removes the expense it created, if any. */
  function deleteRecord(id) {
    S.update((db) => {
      db.maintenanceRecords = db.maintenanceRecords.filter((r) => r.id !== id);
      db.expenses = db.expenses.filter((e) => e.linkedRecordId !== id);
    });
  }

  /** Total spent on maintenance + repair records (optionally per vehicle). */
  function totalCost(vehicleId = null) {
    return U.sum(
      all().filter((r) => !vehicleId || r.vehicleId === vehicleId),
      (r) => r.cost
    );
  }

  return {
    STATUS,
    STATUS_META,
    all,
    forVehicle,
    latestByType,
    statusFor,
    scheduleFor,
    nextService,
    fleetSummary,
    addRecord,
    updateRecord,
    deleteRecord,
    totalCost,
  };
})();
