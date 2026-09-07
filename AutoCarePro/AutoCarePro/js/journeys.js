/* ==========================================================================
   AutoCare Pro — journeys.js
   Journeys are how the app learns *where* and *how hard* a vehicle is used.
   They feed two things: the distance-since-wash term of the Wash Score and
   the environmental-exposure analytics.
   ========================================================================== */

window.AC = window.AC || {};

AC.journeys = (function () {
  "use strict";

  const U = AC.utils;
  const S = AC.storage;

  /** Qualitative dust levels mapped onto the 0–1 scale the maths needs. */
  const DUST_LEVELS = [
    { key: "low", label: "Low", value: 0.2 },
    { key: "moderate", label: "Moderate", value: 0.55 },
    { key: "high", label: "High", value: 0.85 },
  ];

  const dustValue = (key) => (DUST_LEVELS.find((d) => d.key === key) || DUST_LEVELS[1]).value;
  const dustLabel = (key) => (DUST_LEVELS.find((d) => d.key === key) || DUST_LEVELS[1]).label;

  const all = () => U.sortBy(S.list("journeys"), (j) => j.date, "desc");

  const forVehicle = (vehicleId) => all().filter((j) => j.vehicleId === vehicleId);

  /** Journeys taken on or after `fromIso`. */
  function since(vehicleId, fromIso) {
    if (!fromIso) return forVehicle(vehicleId);
    return forVehicle(vehicleId).filter((j) => j.date >= fromIso);
  }

  const distanceSince = (vehicleId, fromIso) => U.sum(since(vehicleId, fromIso), (j) => j.distanceKm);

  /**
   * Exposure summary for a vehicle over the supplied journeys.
   * `dust` and `exposure` are 0–1 indices; `exposure` blends the pollution
   * the vehicle drove through with the distance it covered.
   */
  function exposureSummary(vehicleId, list = null) {
    const rows = list || forVehicle(vehicleId);
    if (!rows.length) {
      return { count: 0, totalDistance: 0, avgAqi: null, dust: 0, exposure: 0, label: "NO DATA" };
    }

    const totalDistance = U.sum(rows, (j) => j.distanceKm);
    const withAqi = rows.filter((j) => U.isNum(j.avgAqi));

    // Distance-weighted AQI: a 300 km drive through smog matters more than a
    // 5 km errand through the same air.
    const avgAqi = withAqi.length
      ? Math.round(
          U.sum(withAqi, (j) => Number(j.avgAqi) * Number(j.distanceKm)) /
            Math.max(1, U.sum(withAqi, (j) => j.distanceKm))
        )
      : null;

    const dust = U.clamp(
      U.sum(rows, (j) => dustValue(j.dustLevel) * Number(j.distanceKm)) /
        Math.max(1, totalDistance),
      0,
      1
    );

    const aqiComponent = avgAqi === null ? 0.4 : U.clamp(avgAqi / 300, 0, 1);
    const distanceComponent = U.clamp(totalDistance / 1500, 0, 1);
    const exposure = U.clamp(aqiComponent * 0.55 + dust * 0.3 + distanceComponent * 0.15, 0, 1);

    return {
      count: rows.length,
      totalDistance,
      avgAqi,
      dust,
      exposure,
      label: AC.constants.levelBand(exposure).label,
      tone: AC.constants.levelBand(exposure).tone,
    };
  }

  /**
   * Adding a journey advances the odometer, because kilometres driven are
   * kilometres driven — the two must never disagree.
   */
  function add(value) {
    const row = S.insert("journeys", {
      vehicleId: value.vehicleId,
      from: value.from,
      to: value.to,
      distanceKm: Number(value.distanceKm),
      date: value.date,
      avgAqi: U.isNum(value.avgAqi) ? Number(value.avgAqi) : null,
      dustLevel: value.dustLevel || "moderate",
      source: "user",
    });

    S.update((db) => {
      const v = db.vehicles.find((x) => x.id === value.vehicleId);
      if (v) v.odometer = (Number(v.odometer) || 0) + Number(value.distanceKm);
    });

    return row;
  }

  const remove = (id) => S.remove("journeys", id);

  /** Monthly distance series for the analytics charts. */
  function monthlyDistance(vehicleId = null, months = 6) {
    const rows = (vehicleId ? forVehicle(vehicleId) : all()).slice();
    const buckets = new Map();
    for (let i = months - 1; i >= 0; i -= 1) {
      const key = U.formatMonthKey(U.addMonths(U.today(), -i));
      buckets.set(key, 0);
    }
    rows.forEach((j) => {
      const key = U.formatMonthKey(j.date);
      if (buckets.has(key)) buckets.set(key, buckets.get(key) + Number(j.distanceKm));
    });
    return Array.from(buckets.entries()).map(([key, value]) => ({
      key,
      label: U.monthLabel(key),
      value,
    }));
  }

  return {
    DUST_LEVELS,
    dustValue,
    dustLabel,
    all,
    forVehicle,
    since,
    distanceSince,
    exposureSummary,
    add,
    remove,
    monthlyDistance,
  };
})();
