/* ==========================================================================
   AutoCare Pro — analytics.js
   Every number shown on the dashboard and the analytics page is derived here
   from the stored records. Nothing in this file is a literal metric value.
   ========================================================================== */

window.AC = window.AC || {};

AC.analytics = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;

  /* ---------------------------------------------------- dashboard tiles -- */

  function dashboardMetrics(env = null) {
    const vehicles = AC.vehicles.all();
    const { dueSoon, overdue } = AC.maintenance.fleetSummary(vehicles);

    const maintenanceCost =
      AC.maintenance.totalCost() +
      AC.expenses.total({ category: "repair" }) +
      AC.expenses.total({ category: "maintenance" }) -
      // maintenance expenses created *from* a service record would otherwise
      // be counted twice, so subtract the linked ones
      U.sum(
        AC.expenses.all().filter((e) => e.linkedRecordId && e.category !== "wash"),
        (e) => e.amount
      );

    const washScores = vehicles.map((v) => AC.wash.calculateWashScore(v, env).score);

    return {
      totalVehicles: vehicles.length,
      serviceDue: dueSoon,
      overdue,
      maintenanceCost: Math.max(0, Math.round(maintenanceCost)),
      totalExpenses: AC.expenses.total(),
      monthExpenses: AC.expenses.monthToDate(),
      fleetHealth: AC.health.fleetHealth(vehicles),
      avgWashScore: washScores.length
        ? Math.round(U.sum(washScores) / washScores.length)
        : 0,
      totalDistance: U.sum(vehicles, (v) => v.odometer),
    };
  }

  /* ------------------------------------------------------------- series -- */

  /**
   * Odometer growth reconstructed from the recorded odometer readings
   * (maintenance records, wash records and journeys all carry one).
   * Months with no reading inherit the previous known value.
   */
  function odometerGrowth(vehicleId, months = 6) {
    const vehicle = AC.vehicles.get(vehicleId);
    if (!vehicle) return [];

    const points = [];
    AC.maintenance.forVehicle(vehicleId).forEach((r) =>
      points.push({ date: r.date, odo: Number(r.odometer) || 0 })
    );
    AC.wash.history(vehicleId).forEach((w) =>
      points.push({ date: w.date, odo: Number(w.odometer) || 0 })
    );

    const sorted = U.sortBy(points, (p) => p.date, "asc");
    const buckets = [];

    for (let i = months - 1; i >= 0; i -= 1) {
      const monthDate = U.addMonths(U.today(), -i);
      const key = U.formatMonthKey(monthDate);
      const upto = sorted.filter((p) => U.formatMonthKey(p.date) <= key);
      const value = upto.length ? Math.max(...upto.map((p) => p.odo)) : null;
      buckets.push({ key, label: U.monthLabel(key), value });
    }

    // Forward-fill, then anchor the final point to the live odometer.
    let last = null;
    buckets.forEach((b) => {
      if (b.value === null) b.value = last;
      else last = b.value;
    });
    const firstKnown = buckets.find((b) => b.value !== null);
    buckets.forEach((b) => {
      if (b.value === null) b.value = firstKnown ? firstKnown.value : Number(vehicle.odometer) || 0;
    });
    buckets[buckets.length - 1].value = Math.max(
      buckets[buckets.length - 1].value,
      Number(vehicle.odometer) || 0
    );

    return buckets;
  }

  /** Maintenance spend grouped by service type. */
  function maintenanceCostByType(vehicleId = null) {
    const rows = vehicleId ? AC.maintenance.forVehicle(vehicleId) : AC.maintenance.all();
    const grouped = U.groupBy(rows, (r) => r.type);
    return Object.keys(grouped)
      .map((key) => ({
        key,
        label: C.maintenanceLabel(key),
        value: U.sum(grouped[key], (r) => r.cost),
      }))
      .filter((r) => r.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }

  /** Environmental exposure per month, derived from journeys. */
  function exposureSeries(vehicleId = null, months = 6) {
    const rows = vehicleId ? AC.journeys.forVehicle(vehicleId) : AC.journeys.all();
    const out = [];
    for (let i = months - 1; i >= 0; i -= 1) {
      const key = U.formatMonthKey(U.addMonths(U.today(), -i));
      const monthRows = rows.filter((j) => U.formatMonthKey(j.date) === key);
      const summary = AC.journeys.exposureSummary(vehicleId, monthRows);
      out.push({
        key,
        label: U.monthLabel(key),
        distance: summary.totalDistance,
        aqi: summary.avgAqi,
        dust: U.round(summary.dust * 100),
      });
    }
    return out;
  }

  /* ------------------------------------------------------------ insights -- */

  /**
   * Short, factual observations generated from the data. These are computed
   * statements, not canned marketing copy — each one names the number that
   * produced it.
   */
  function insights(vehicleId = null) {
    const out = [];
    const vehicles = vehicleId ? [AC.vehicles.get(vehicleId)].filter(Boolean) : AC.vehicles.all();
    if (!vehicles.length) return out;

    // Compare the two most recent *meaningful* months: early in a new month the
    // current bucket is nearly empty, which would produce a misleading "-100%".
    const spendSeries = AC.expenses.monthly(vehicleId ? { vehicleId } : {}, 4);
    const dayOfMonth = new Date().getDate();
    const pair = dayOfMonth <= 7 ? spendSeries.slice(-3, -1) : spendSeries.slice(-2);
    if (pair.length >= 2) {
      const [prev, curr] = pair;
      if (prev.value > 0) {
        const delta = ((curr.value - prev.value) / prev.value) * 100;
        out.push({
          title: "SPEND TREND",
          text: `${curr.label} spending is ${Math.abs(Math.round(delta))}% ${
            delta >= 0 ? "higher" : "lower"
          } than ${prev.label} (${U.formatCurrency(curr.value)} vs ${U.formatCurrency(prev.value)}).`,
        });
      }
    }

    const cats = AC.expenses.byCategory(vehicleId ? { vehicleId } : {});
    if (cats.length) {
      out.push({
        title: "LARGEST CATEGORY",
        text: `${cats[0].label} accounts for ${Math.round(cats[0].share * 100)}% of recorded spend (${U.formatCurrency(
          cats[0].amount
        )}).`,
      });
    }

    const worst = U.sortBy(
      vehicles.map((v) => ({ v, h: AC.health.calculateVehicleHealth(v) })),
      (x) => x.h.overall,
      "asc"
    )[0];
    if (worst) {
      out.push({
        title: "LOWEST HEALTH",
        text: `${worst.v.name} is at ${worst.h.overall}% (${worst.h.band.label}). Weakest subsystem: ${
          U.sortBy(worst.h.factors, (f) => f.score, "asc")[0].label
        }.`,
      });
    }

    const { overdue, dueSoon } = AC.maintenance.fleetSummary(vehicles);
    out.push({
      title: "SERVICE PIPELINE",
      text: overdue
        ? `${overdue} service${overdue === 1 ? " is" : "s are"} overdue and ${dueSoon} due soon across ${vehicles.length} vehicle${
            vehicles.length === 1 ? "" : "s"
          }.`
        : `No overdue services. ${dueSoon} item${dueSoon === 1 ? "" : "s"} due soon.`,
    });

    const cpk = vehicleId ? AC.expenses.costPerKm(vehicleId) : null;
    if (cpk) {
      out.push({
        title: "RUNNING COST",
        text: `Approximately ${U.formatCurrency(cpk * 100)} per 100 km based on recorded spend and distance.`,
      });
    }

    return out;
  }

  return {
    dashboardMetrics,
    odometerGrowth,
    maintenanceCostByType,
    exposureSeries,
    insights,
  };
})();
