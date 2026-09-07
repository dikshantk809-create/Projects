/* ==========================================================================
   AutoCare Pro — seed.js
   First-run demo data.

   IMPORTANT DATA RULE: the seed runs only when the database does not already
   exist (or when the user explicitly resets). It never overwrites records the
   user created. Every seeded row is stamped `source: "demo"` so the UI can
   label it and the user can tell generated data from their own.

   Dates are generated relative to "today" so the demo always looks current
   whenever the project is opened or evaluated.
   ========================================================================== */

window.AC = window.AC || {};

AC.seed = (function () {
  "use strict";

  const U = AC.utils;

  const daysAgo = (n) => U.isoDate(U.addDays(U.today(), -n));

  /* ------------------------------------------------------------ vehicles -- */

  function buildVehicles() {
    return [
      {
        id: "veh_demo_i20",
        name: "Hyundai i20",
        make: "Hyundai",
        model: "i20 Sportz",
        year: 2022,
        fuelType: "Petrol",
        odometer: 35240,
        registration: "PB11 CX 4821",
        lastServiceDate: daysAgo(150),
        lastServiceOdometer: 30690,
        lastWashDate: daysAgo(12),
        odometerAtLastWash: 34900,
        notes: "Daily driver. Mostly city running with weekend highway trips.",
        isPrimary: true,
        source: "demo",
        createdAt: new Date().toISOString(),
      },
      {
        id: "veh_demo_city",
        name: "Honda City",
        make: "Honda",
        model: "City VX CVT",
        year: 2021,
        fuelType: "Petrol",
        odometer: 48120,
        registration: "PB11 AH 7734",
        lastServiceDate: daysAgo(120),
        lastServiceOdometer: 45300,
        lastWashDate: daysAgo(19),
        odometerAtLastWash: 47450,
        notes: "Family car. Long inter-city runs on the Chandigarh corridor.",
        isPrimary: false,
        source: "demo",
        createdAt: new Date().toISOString(),
      },
    ];
  }

  /* ------------------------------------------------------- maintenance -- */

  /**
   * Service history is designed so the algorithms produce a genuinely
   * interesting state on first launch:
   *   i20   -> Engine Oil DUE SOON in ~450 km  (health: GOOD)
   *   City  -> Oil Filter OVERDUE, no tyre/battery history
   *            (health: ATTENTION REQUIRED)
   * The statuses are still *computed* — nothing below stores a status.
   */
  function buildMaintenance() {
    const rows = [];
    const add = (vehicleId, type, days, odometer, cost, notes) =>
      rows.push({
        id: U.uid("mnt"),
        vehicleId,
        type,
        date: daysAgo(days),
        odometer,
        cost,
        notes: notes || "",
        nextServiceDate: null,
        nextServiceOdometer: null,
        source: "demo",
        createdAt: new Date().toISOString(),
      });

    // ---- Hyundai i20 -----------------------------------------------------
    add("veh_demo_i20", "general", 540, 18900, 4850, "Periodic service at authorised workshop.");
    add("veh_demo_i20", "engine_oil", 540, 18900, 2150, "5W-30 semi-synthetic.");
    add("veh_demo_i20", "air_filter", 540, 18900, 640, "");
    add("veh_demo_i20", "engine_oil", 360, 24600, 2300, "5W-30 semi-synthetic.");
    add("veh_demo_i20", "brake_service", 300, 26800, 1850, "Front pads cleaned, rear drums adjusted.");
    add("veh_demo_i20", "general", 210, 29400, 5400, "Periodic service, all filters checked.");
    add("veh_demo_i20", "air_filter", 210, 29400, 780, "");
    add("veh_demo_i20", "wheel_align", 210, 29400, 700, "Alignment and balancing.");
    add("veh_demo_i20", "engine_oil", 150, 30690, 2450, "5W-30 fully synthetic.");
    add("veh_demo_i20", "tyres", 60, 33100, 18600, "Four new tubeless tyres.");
    add("veh_demo_i20", "oil_filter", 60, 33100, 650, "Replaced with tyre change visit.");
    add("veh_demo_i20", "battery", 25, 34600, 6200, "New 35Ah battery, 48-month warranty.");

    // ---- Honda City ------------------------------------------------------
    add("veh_demo_city", "general", 500, 34000, 5200, "Periodic service.");
    add("veh_demo_city", "engine_oil", 500, 34000, 2450, "");
    add("veh_demo_city", "engine_oil", 330, 39200, 2600, "");
    add("veh_demo_city", "brake_pads", 330, 39200, 4800, "Front brake pads replaced.");
    add("veh_demo_city", "general", 260, 41500, 5900, "Periodic service.");
    add("veh_demo_city", "oil_filter", 260, 41500, 680, "");
    add("veh_demo_city", "air_filter", 260, 41500, 820, "");
    add("veh_demo_city", "engine_oil", 120, 45300, 2700, "0W-20 fully synthetic.");
    add("veh_demo_city", "spark_plugs", 120, 45300, 2900, "Iridium plugs.");
    add("veh_demo_city", "coolant", 95, 46100, 1400, "Coolant flush and refill.");

    return rows;
  }

  /* ----------------------------------------------------------- journeys -- */

  function buildJourneys() {
    const trips = [
      ["veh_demo_i20", "Patiala", "Chandigarh", 65, 6, 132, "moderate"],
      ["veh_demo_i20", "Chandigarh", "Patiala", 65, 5, 128, "moderate"],
      ["veh_demo_i20", "Patiala", "Rajpura", 28, 9, 148, "high"],
      ["veh_demo_i20", "Patiala", "Ludhiana", 92, 22, 156, "high"],
      ["veh_demo_i20", "Ludhiana", "Patiala", 92, 21, 151, "high"],
      ["veh_demo_i20", "Patiala", "Chandigarh", 65, 38, 118, "moderate"],
      ["veh_demo_i20", "Patiala", "Nabha", 31, 52, 104, "low"],
      ["veh_demo_i20", "Patiala", "Delhi", 245, 74, 214, "high"],
      ["veh_demo_i20", "Delhi", "Patiala", 245, 71, 208, "high"],
      ["veh_demo_city", "Chandigarh", "Pathankot", 230, 14, 118, "high"],
      ["veh_demo_city", "Pathankot", "Chandigarh", 230, 11, 112, "high"],
      ["veh_demo_city", "Patiala", "Chandigarh", 65, 27, 136, "moderate"],
      ["veh_demo_city", "Chandigarh", "Shimla", 112, 46, 74, "low"],
      ["veh_demo_city", "Shimla", "Chandigarh", 112, 44, 71, "low"],
      ["veh_demo_city", "Patiala", "Amritsar", 228, 88, 142, "moderate"],
    ];

    return trips.map(([vehicleId, from, to, distanceKm, days, avgAqi, dustLevel]) => ({
      id: U.uid("jny"),
      vehicleId,
      from,
      to,
      distanceKm,
      date: daysAgo(days),
      avgAqi,
      dustLevel,
      source: "demo",
      createdAt: new Date().toISOString(),
    }));
  }

  /* -------------------------------------------------------- wash history -- */

  function buildWashes() {
    const rows = [
      ["veh_demo_i20", 12, 34900, 250],
      ["veh_demo_i20", 31, 33800, 250],
      ["veh_demo_i20", 55, 32600, 200],
      ["veh_demo_i20", 84, 31400, 250],
      ["veh_demo_city", 19, 47450, 300],
      ["veh_demo_city", 48, 46300, 300],
      ["veh_demo_city", 79, 44900, 250],
    ];
    return rows.map(([vehicleId, days, odometer, cost]) => ({
      id: U.uid("wsh"),
      vehicleId,
      date: daysAgo(days),
      odometer,
      cost,
      source: "demo",
      createdAt: new Date().toISOString(),
    }));
  }

  /* ----------------------------------------------------------- expenses -- */

  /**
   * Expenses combine three streams so the analytics charts have shape:
   *   - a fuel fill roughly every 11 days per vehicle
   *   - one expense mirroring each maintenance record that cost money
   *   - one expense per wash
   *   - one annual insurance premium per vehicle
   */
  function buildExpenses(maintenance, washes) {
    const rows = [];
    const push = (vehicleId, category, amount, date, description, linkedRecordId) =>
      rows.push({
        id: U.uid("exp"),
        vehicleId,
        category,
        amount,
        date,
        description,
        linkedRecordId: linkedRecordId || null,
        source: "demo",
        createdAt: new Date().toISOString(),
      });

    // Fuel — deterministic variation keeps the monthly chart lively.
    [
      { id: "veh_demo_i20", base: 2100, spread: 480, every: 11 },
      { id: "veh_demo_city", base: 2650, spread: 520, every: 13 },
    ].forEach((cfg) => {
      for (let d = 4; d <= 185; d += cfg.every) {
        const wobble = Math.round(Math.sin(d / 7) * cfg.spread);
        push(cfg.id, "fuel", cfg.base + wobble, daysAgo(d), "Fuel fill");
      }
    });

    maintenance
      .filter((m) => m.cost > 0)
      .forEach((m) =>
        push(
          m.vehicleId,
          m.type === "repair" ? "repair" : "maintenance",
          m.cost,
          m.date,
          `${AC.constants.maintenanceLabel(m.type)} — workshop bill`,
          m.id
        )
      );

    washes.forEach((w) =>
      push(w.vehicleId, "wash", w.cost, w.date, "Vehicle wash", w.id)
    );

    push("veh_demo_i20", "insurance", 14800, daysAgo(96), "Comprehensive insurance renewal");
    push("veh_demo_city", "insurance", 17600, daysAgo(142), "Comprehensive insurance renewal");
    push("veh_demo_i20", "other", 1200, daysAgo(63), "Cabin accessories and floor mats");
    push("veh_demo_city", "repair", 3400, daysAgo(58), "Power window regulator repair");

    return rows;
  }

  /* ---------------------------------------------------------------- apply -- */

  /**
   * Populate an *empty* database document in place.
   * Returns the same object so callers can chain.
   */
  function apply(db) {
    if (!db) return db;
    const hasData =
      (db.vehicles && db.vehicles.length) ||
      (db.maintenanceRecords && db.maintenanceRecords.length) ||
      (db.expenses && db.expenses.length);
    if (hasData) return db; // never overwrite real data

    const maintenance = buildMaintenance();
    const washes = buildWashes();

    db.vehicles = buildVehicles();
    db.maintenanceRecords = maintenance;
    db.journeys = buildJourneys();
    db.washRecords = washes;
    db.expenses = buildExpenses(maintenance, washes);
    db.settings.seededDemoData = true;
    db.meta.seededAt = new Date().toISOString();

    return db;
  }

  return { apply, buildVehicles, buildMaintenance, buildJourneys, buildWashes, buildExpenses };
})();
