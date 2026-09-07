/* ==========================================================================
   AutoCare Pro — washAdvisor.js
   The Smart Wash Advisor: a 0–100 Wash Score built from four weighted
   factors instead of a naive "wash every 7 days" rule.

   ALGORITHM — calculateWashScore(vehicle, environment)
   ---------------------------------------------------
   TIME  (max 60)  Days since the last wash, scaled so that 20 days saturates
                   the factor. Weather multiplies elapsed time because road
                   spray, fog and snow soil a vehicle faster than dry air:
                       Rain/Showers/Storm x1.20   Snow x1.25   Fog x1.10

   POLLUTION (max 20)  environment.pollutionIndex() — a weighted blend of
                   AQI (50%), PM2.5 (20%), PM10 (15%), NO2 (8%), O3 (7%).

   ROAD DUST (max 10)  environment.dustIndex() — coarse particulate, air
                   dryness and the dust level of journeys since the last wash,
                   with a rain credit.

   USAGE (max 10)  Distance driven since the wash (7 pts, saturating at
                   500 km) plus journey frequency (3 pts, saturating at 6
                   trips).

   The four are summed and clamped to 0–100, then mapped to a band:
       0–30 CLEAN · 31–55 MONITOR · 56–75 WASH SOON · 76–100 WASH NOW

   Every factor returns its own points, cap and a plain-English note, which is
   what the "Why this score?" panel renders — the score is always explainable.
   ========================================================================== */

window.AC = window.AC || {};

AC.wash = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const S = AC.storage;
  const ENV = AC.environment;
  const J = AC.journeys;

  const TIME_SATURATION_DAYS = 20;
  const USAGE_SATURATION_KM = 500;
  const USAGE_SATURATION_TRIPS = 6;

  const WEATHER_MULTIPLIER = {
    Rain: 1.2,
    Showers: 1.2,
    Storm: 1.2,
    Snow: 1.25,
    Fog: 1.1,
    Cloudy: 1.0,
    Clear: 1.0,
  };

  /* -------------------------------------------------- distance since wash -- */

  /**
   * How far has the vehicle travelled since it was last washed?
   * Preference order (most trustworthy first):
   *   1. odometer delta, when the odometer at the last wash was recorded
   *   2. sum of journeys logged since the last wash date
   *   3. days elapsed x the vehicle's estimated daily distance
   */
  function distanceSinceWash(vehicle) {
    const odo = Number(vehicle.odometer) || 0;

    if (U.isNum(vehicle.odometerAtLastWash)) {
      return {
        km: Math.max(0, odo - Number(vehicle.odometerAtLastWash)),
        source: "odometer",
      };
    }

    const trips = J.since(vehicle.id, vehicle.lastWashDate);
    if (trips.length) {
      return { km: U.sum(trips, (t) => t.distanceKm), source: "journeys" };
    }

    const days = Math.max(0, U.daysBetween(vehicle.lastWashDate) ?? 0);
    return {
      km: Math.round(days * AC.health.estimateDailyKm(vehicle)),
      source: "estimated",
    };
  }

  /* -------------------------------------------------------------- scoring -- */

  /**
   * @param {object} vehicle
   * @param {object} environment reading from AC.environment
   * @returns {object} score, band, factors and the conditions used
   */
  function calculateWashScore(vehicle, environment) {
    const env = environment || ENV.current();

    if (!vehicle) {
      return emptyResult();
    }

    const days = Math.max(0, U.daysBetween(vehicle.lastWashDate) ?? TIME_SATURATION_DAYS);
    const weather = (env && env.weather) || "Clear";
    const weatherMult = WEATHER_MULTIPLIER[weather] || 1;
    const effectiveDays = days * weatherMult;

    /* ---- 1. TIME ------------------------------------------------------- */
    const timeRatio = U.clamp(effectiveDays / TIME_SATURATION_DAYS, 0, 1);
    const timePoints = U.round(timeRatio * C.WASH_WEIGHTS.time, 1);

    /* ---- 2. POLLUTION -------------------------------------------------- */
    const pollution = ENV.pollutionIndex(env);
    const pollutionPoints = U.round(pollution * C.WASH_WEIGHTS.pollution, 1);

    /* ---- 3. ROAD DUST -------------------------------------------------- */
    const tripsSinceWash = J.since(vehicle.id, vehicle.lastWashDate);
    const journeyDust = tripsSinceWash.length
      ? U.clamp(
          U.sum(tripsSinceWash, (t) => J.dustValue(t.dustLevel) * Number(t.distanceKm)) /
            Math.max(1, U.sum(tripsSinceWash, (t) => t.distanceKm)),
          0,
          1
        )
      : 0;
    const dust = ENV.dustIndex(env, journeyDust);
    const dustPoints = U.round(dust * C.WASH_WEIGHTS.dust, 1);

    /* ---- 4. USAGE ------------------------------------------------------ */
    const distance = distanceSinceWash(vehicle);
    const distanceRatio = U.clamp(distance.km / USAGE_SATURATION_KM, 0, 1);
    const tripRatio = U.clamp(tripsSinceWash.length / USAGE_SATURATION_TRIPS, 0, 1);
    const usagePoints = U.round(distanceRatio * 7 + tripRatio * 3, 1);

    const score = U.clamp(
      Math.round(timePoints + pollutionPoints + dustPoints + usagePoints),
      0,
      100
    );

    const band = C.washBand(score);

    return {
      score,
      band,
      status: band.label,
      tone: band.tone,
      key: band.key,
      message: band.message,
      daysSinceWash: days,
      distanceSinceWash: distance.km,
      distanceSource: distance.source,
      tripsSinceWash: tripsSinceWash.length,
      factors: [
        {
          key: "time",
          name: "TIME SINCE WASH",
          points: timePoints,
          max: C.WASH_WEIGHTS.time,
          note:
            weatherMult > 1
              ? `${days} days elapsed, weighted x${weatherMult} for ${weather.toLowerCase()} conditions`
              : `${days} day${days === 1 ? "" : "s"} since the last recorded wash`,
        },
        {
          key: "pollution",
          name: "POLLUTION EXPOSURE",
          points: pollutionPoints,
          max: C.WASH_WEIGHTS.pollution,
          note: env
            ? `AQI ${env.aqi} · PM2.5 ${env.pm25} · PM10 ${env.pm10} µg/m³`
            : "No environmental reading available",
        },
        {
          key: "dust",
          name: "ROAD DUST",
          points: dustPoints,
          max: C.WASH_WEIGHTS.dust,
          note: env
            ? `Humidity ${env.humidity}% · ${C.levelBand(dust).label.toLowerCase()} dust deposition`
            : "No environmental reading available",
        },
        {
          key: "usage",
          name: "VEHICLE USAGE",
          points: usagePoints,
          max: C.WASH_WEIGHTS.usage,
          note: `${U.formatNumber(distance.km)} km${
            distance.source === "estimated" ? " (estimated)" : ""
          } over ${tripsSinceWash.length} logged trip${tripsSinceWash.length === 1 ? "" : "s"}`,
        },
      ],
      conditions: {
        aqi: env ? env.aqi : null,
        aqiBand: env ? C.aqiBand(env.aqi) : null,
        pollution,
        dust,
        dustBand: C.levelBand(dust),
        weather,
        temperature: env ? env.temperature : null,
        humidity: env ? env.humidity : null,
        location: env ? env.location : null,
        provider: env ? env.provider : null,
        isDemo: env ? Boolean(env.isDemo) : true,
        degraded: env ? env.degraded || null : null,
      },
    };
  }

  function emptyResult() {
    const band = C.washBand(0);
    return {
      score: 0,
      band,
      status: band.label,
      tone: band.tone,
      key: band.key,
      message: "Add a vehicle to start tracking wash recommendations.",
      daysSinceWash: 0,
      distanceSinceWash: 0,
      distanceSource: "none",
      tripsSinceWash: 0,
      factors: [],
      conditions: {},
    };
  }

  /* --------------------------------------------------------------- writes -- */

  /**
   * Record a wash. This resets the two inputs the time and usage factors read
   * (last wash date + odometer at last wash) so the gauge visibly drops.
   */
  function recordWash(value) {
    const vehicle = S.find("vehicles", value.vehicleId);
    const odometer = U.isNum(value.odometer) ? Number(value.odometer) : Number(vehicle.odometer) || 0;

    const row = S.insert("washRecords", {
      vehicleId: value.vehicleId,
      date: value.date,
      odometer,
      cost: Number(value.cost) || 0,
      source: "user",
    });

    S.update((db) => {
      const v = db.vehicles.find((x) => x.id === value.vehicleId);
      if (!v) return;
      v.lastWashDate = value.date;
      v.odometerAtLastWash = odometer;
      if (odometer > (Number(v.odometer) || 0)) v.odometer = odometer;
    });

    if (value.logExpense && Number(value.cost) > 0) {
      S.insert("expenses", {
        vehicleId: value.vehicleId,
        category: "wash",
        amount: Number(value.cost),
        date: value.date,
        description: "Vehicle wash",
        linkedRecordId: row.id,
        source: "user",
      });
    }

    return row;
  }

  const history = (vehicleId = null) =>
    U.sortBy(
      S.list("washRecords").filter((w) => !vehicleId || w.vehicleId === vehicleId),
      (w) => w.date,
      "desc"
    );

  /** Washes per month, for the analytics "Wash Frequency" chart. */
  function monthlyFrequency(vehicleId = null, months = 6) {
    const rows = history(vehicleId);
    const buckets = new Map();
    for (let i = months - 1; i >= 0; i -= 1) {
      buckets.set(U.formatMonthKey(U.addMonths(U.today(), -i)), 0);
    }
    rows.forEach((w) => {
      const key = U.formatMonthKey(w.date);
      if (buckets.has(key)) buckets.set(key, buckets.get(key) + 1);
    });
    return Array.from(buckets.entries()).map(([key, value]) => ({
      key,
      label: U.monthLabel(key),
      value,
    }));
  }

  return {
    TIME_SATURATION_DAYS,
    USAGE_SATURATION_KM,
    WEATHER_MULTIPLIER,
    distanceSinceWash,
    calculateWashScore,
    recordWash,
    history,
    monthlyFrequency,
  };
})();
