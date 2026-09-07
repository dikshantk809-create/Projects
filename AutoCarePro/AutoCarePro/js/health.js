/* ==========================================================================
   AutoCare Pro — health.js
   Vehicle Health Score (0–100) per subsystem and overall.

   ALGORITHM
   ---------
   Each subsystem (engine / brakes / tyres / battery) starts at 100 and loses
   points for three transparent reasons:

   1. SERVICE WEAR — for every maintenance type that belongs to the subsystem
      we know how much of its recommended interval has been consumed
      (`consumed`, from maintenance.js — 1.0 means exactly due, 1.4 means 40%
      past due). The worst type in the subsystem drives the penalty:

         consumed <= 1 :  penalty = consumed² * 15          (0 … 15)
         consumed  > 1 :  penalty = 15 + (consumed-1) * 50  (capped at 60)

      The curve is quadratic on purpose: being halfway through an oil-change
      interval is not "half unhealthy", but the last stretch before a service
      matters, and going past due degrades quickly.

      A subsystem with no service history at all is penalised a flat 25 —
      an unknown history is not the same as a healthy one.

   2. AGE — 0.8 points per year since the model year, capped at 10.

   3. ODOMETER — 6 points per 100,000 km travelled, capped at 10.

   The overall score is the weighted mean of the four subsystems
   (engine 35%, brakes 25%, tyres 20%, battery 20%) with an extra deduction
   for every currently OVERDUE service, because an overdue item is a present
   risk rather than gradual wear.

   Every value is clamped to 0–100 and the reasons are returned alongside the
   numbers so the UI can explain the score instead of just showing it.
   ========================================================================== */

window.AC = window.AC || {};

AC.health = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const M = AC.maintenance;

  const SYSTEMS = ["engine", "tyres", "battery", "brakes"];

  const NO_HISTORY_PENALTY = 25;
  const AGE_PER_YEAR = 0.8;
  const AGE_CAP = 10;
  const ODO_PER_100K = 6;
  const ODO_CAP = 10;
  const OVERDUE_PENALTY = 4;

  function wearPenalty(consumed) {
    if (consumed <= 1) return consumed * consumed * 15;
    return Math.min(60, 15 + (consumed - 1) * 50);
  }

  /**
   * @param {object} vehicle
   * @returns {{overall:number, engine:number, tyres:number, battery:number,
   *            brakes:number, band:object, factors:object[]}}
   */
  function calculateVehicleHealth(vehicle) {
    if (!vehicle) {
      return { overall: 0, engine: 0, tyres: 0, battery: 0, brakes: 0, band: C.healthBand(0), factors: [] };
    }

    const schedule = M.scheduleFor(vehicle);
    const byType = schedule.reduce((acc, row) => {
      acc[row.type] = row;
      return acc;
    }, {});

    const currentYear = new Date().getFullYear();
    const ageYears = Math.max(0, currentYear - (Number(vehicle.year) || currentYear));
    const agePenalty = Math.min(AGE_CAP, ageYears * AGE_PER_YEAR);
    const odoPenalty = Math.min(ODO_CAP, ((Number(vehicle.odometer) || 0) / 100000) * ODO_PER_100K);

    const scores = {};
    const factors = [];

    SYSTEMS.forEach((system) => {
      const types = C.MAINTENANCE_TYPES.filter((t) => t.system === system);
      let worst = null;

      types.forEach((t) => {
        const row = byType[t.key];
        if (!row || row.status === M.STATUS.UNKNOWN) return;
        if (!worst || row.consumed > worst.consumed) worst = row;
      });

      let penalty;
      let reason;
      if (!worst) {
        penalty = NO_HISTORY_PENALTY;
        reason = "No service history recorded";
      } else {
        penalty = wearPenalty(worst.consumed);
        const pct = Math.round(worst.consumed * 100);
        reason = `${worst.label}: ${pct}% of interval used`;
      }

      const score = U.clamp(Math.round(100 - penalty - agePenalty - odoPenalty), 0, 100);
      scores[system] = score;
      factors.push({
        system,
        label: system.toUpperCase(),
        score,
        reason,
        wear: Math.round(penalty),
        age: Math.round(agePenalty),
        usage: Math.round(odoPenalty),
      });
    });

    const overdueCount = schedule.filter((r) => r.status === M.STATUS.OVERDUE).length;

    const weighted =
      scores.engine * C.HEALTH_WEIGHTS.engine +
      scores.brakes * C.HEALTH_WEIGHTS.brakes +
      scores.tyres * C.HEALTH_WEIGHTS.tyres +
      scores.battery * C.HEALTH_WEIGHTS.battery;

    const overall = U.clamp(Math.round(weighted - overdueCount * OVERDUE_PENALTY), 0, 100);

    return {
      overall,
      engine: scores.engine,
      tyres: scores.tyres,
      battery: scores.battery,
      brakes: scores.brakes,
      band: C.healthBand(overall),
      overdueCount,
      ageYears,
      factors,
    };
  }

  /** Fleet average — the dashboard headline when several vehicles exist. */
  function fleetHealth(vehicles) {
    if (!vehicles.length) return 0;
    return Math.round(
      U.sum(vehicles, (v) => calculateVehicleHealth(v).overall) / vehicles.length
    );
  }

  /**
   * Reconstruct a health trend by replaying the odometer/service history
   * backwards month by month. This is an approximation used for the trend
   * chart only — the headline number always comes from live data.
   */
  function healthTrend(vehicle, months = 6) {
    if (!vehicle) return [];
    const points = [];
    const records = M.forVehicle(vehicle.id);
    const perDayKm = estimateDailyKm(vehicle, records);

    for (let i = months - 1; i >= 0; i -= 1) {
      const when = U.addMonths(U.today(), -i);
      const daysBack = U.daysBetween(when) * -1; // negative offset from today
      const snapshotOdo = Math.max(0, (Number(vehicle.odometer) || 0) + daysBack * perDayKm);
      const snapshot = {
        ...vehicle,
        odometer: Math.round(snapshotOdo),
      };
      // Only records that existed at that time count towards the snapshot.
      const asOf = U.isoDate(when);
      const historical = records.filter((r) => r.date <= asOf);
      points.push({
        label: U.monthLabel(U.formatMonthKey(when)),
        value: scoreWithRecords(snapshot, historical, asOf),
      });
    }
    return points;
  }

  /** Health score computed against an explicit record set and "as of" date. */
  function scoreWithRecords(vehicle, records, asOfIso) {
    const asOf = U.toDate(asOfIso) || U.today();
    const byType = {};
    records.forEach((r) => {
      const prev = byType[r.type];
      if (!prev || U.toDate(r.date) > U.toDate(prev.date)) byType[r.type] = r;
    });

    const ageYears = Math.max(0, asOf.getFullYear() - (Number(vehicle.year) || asOf.getFullYear()));
    const agePenalty = Math.min(AGE_CAP, ageYears * AGE_PER_YEAR);
    const odoPenalty = Math.min(ODO_CAP, ((Number(vehicle.odometer) || 0) / 100000) * ODO_PER_100K);

    const scores = {};
    SYSTEMS.forEach((system) => {
      const types = C.MAINTENANCE_TYPES.filter((t) => t.system === system);
      let worstConsumed = null;
      types.forEach((t) => {
        const rec = byType[t.key];
        if (!rec) return;
        const kmC = t.km ? U.clamp(((vehicle.odometer || 0) - (rec.odometer || 0)) / t.km, 0, 2) : 0;
        const dayC = t.months
          ? U.clamp(U.daysBetween(rec.date, asOf) / (t.months * 30.44), 0, 2)
          : 0;
        const c = Math.max(kmC, dayC);
        if (worstConsumed === null || c > worstConsumed) worstConsumed = c;
      });
      const penalty = worstConsumed === null ? NO_HISTORY_PENALTY : wearPenalty(worstConsumed);
      scores[system] = U.clamp(Math.round(100 - penalty - agePenalty - odoPenalty), 0, 100);
    });

    return U.clamp(
      Math.round(
        scores.engine * C.HEALTH_WEIGHTS.engine +
          scores.brakes * C.HEALTH_WEIGHTS.brakes +
          scores.tyres * C.HEALTH_WEIGHTS.tyres +
          scores.battery * C.HEALTH_WEIGHTS.battery
      ),
      0,
      100
    );
  }

  /**
   * Average daily distance for a vehicle. Preference order:
   *   1. journeys logged in the last 90 days
   *   2. odometer spread across the maintenance history
   *   3. odometer spread across the vehicle's age
   *   4. a conservative 25 km/day fallback
   */
  function estimateDailyKm(vehicle, records = null) {
    const journeys = AC.storage.list("journeys").filter((j) => j.vehicleId === vehicle.id);
    const recent = journeys.filter((j) => (U.daysBetween(j.date) ?? 999) <= 90);
    if (recent.length >= 2) {
      const span = Math.max(1, U.daysBetween(U.sortBy(recent, (j) => j.date, "asc")[0].date));
      return U.clamp(U.sum(recent, (j) => j.distanceKm) / span, 3, 400);
    }

    const recs = records || AC.maintenance.forVehicle(vehicle.id);
    if (recs.length >= 2) {
      const asc = U.sortBy(recs, (r) => r.date, "asc");
      const first = asc[0];
      const days = Math.max(1, U.daysBetween(first.date));
      const km = Math.max(0, (Number(vehicle.odometer) || 0) - (Number(first.odometer) || 0));
      if (km > 0) return U.clamp(km / days, 3, 400);
    }

    const ageDays = Math.max(365, (new Date().getFullYear() - (Number(vehicle.year) || new Date().getFullYear())) * 365);
    const byAge = (Number(vehicle.odometer) || 0) / ageDays;
    return U.clamp(byAge || 25, 3, 400);
  }

  return {
    SYSTEMS,
    calculateVehicleHealth,
    fleetHealth,
    healthTrend,
    estimateDailyKm,
    wearPenalty,
  };
})();
