/* ==========================================================================
   AutoCare Pro — storage.js
   The persistence layer. ONE localStorage key holds ONE structured document;
   every module reads and writes through this repository API instead of
   touching localStorage directly.

   Why a single document?
     - the whole application state can be exported/imported as one JSON file
     - a schema version lets us migrate old data instead of wiping it
     - swapping localStorage for Firebase/Supabase/REST later means
       reimplementing only `read()` / `write()` below — nothing else changes.
   ========================================================================== */

window.AC = window.AC || {};

AC.storage = (function () {
  "use strict";

  const KEY = "autocareProDB";
  const SCHEMA_VERSION = 1;

  const COLLECTIONS = [
    "vehicles",
    "maintenanceRecords",
    "expenses",
    "journeys",
    "washRecords",
  ];

  const DEFAULT_SETTINGS = {
    userName: "Vikrant",
    userRole: "Vehicle Owner",
    units: "km", // "km" | "mi"
    currency: "INR",
    notifications: {
      service: true,
      wash: true,
      environment: true,
      expense: false,
    },
    environmentMode: "mock", // "mock" | "live"
    locationMode: "manual", // "manual" | "device"
    manualLocation: { label: "Patiala, Punjab", lat: 30.3398, lon: 76.3869 },
    reduceMotion: false,
    seededDemoData: false,
  };

  function emptyDB() {
    return {
      schemaVersion: SCHEMA_VERSION,
      meta: {
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        app: "AutoCare Pro",
      },
      vehicles: [],
      maintenanceRecords: [],
      expenses: [],
      journeys: [],
      washRecords: [],
      environment: { cache: null, fetchedAt: null, provider: null },
      settings: JSON.parse(JSON.stringify(DEFAULT_SETTINGS)),
    };
  }

  /* --------------------------------------------------------- raw access -- */

  let cache = null;
  const listeners = new Set();
  let storageAvailable = true;

  function read() {
    try {
      const raw = window.localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      // Private-mode Safari, disabled storage, or corrupt JSON.
      storageAvailable = false;
      console.warn("[AutoCare] localStorage unavailable — running in memory.", err);
      return null;
    }
  }

  function write(db) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(db));
      storageAvailable = true;
      return true;
    } catch (err) {
      storageAvailable = false;
      console.warn("[AutoCare] Unable to persist database.", err);
      return false;
    }
  }

  /* ---------------------------------------------------------- migration -- */

  /**
   * Bring a document written by an older build up to the current schema.
   * Missing collections/settings are backfilled so the app never crashes on
   * data produced before a field existed.
   */
  function migrate(db) {
    const base = emptyDB();
    if (!db || typeof db !== "object") return base;

    const next = {
      ...base,
      ...db,
      meta: { ...base.meta, ...(db.meta || {}) },
      environment: { ...base.environment, ...(db.environment || {}) },
      settings: {
        ...base.settings,
        ...(db.settings || {}),
        notifications: {
          ...base.settings.notifications,
          ...((db.settings && db.settings.notifications) || {}),
        },
        manualLocation: {
          ...base.settings.manualLocation,
          ...((db.settings && db.settings.manualLocation) || {}),
        },
      },
    };

    COLLECTIONS.forEach((name) => {
      next[name] = Array.isArray(db[name]) ? db[name] : [];
    });

    next.schemaVersion = SCHEMA_VERSION;
    return next;
  }

  /* --------------------------------------------------------- public API -- */

  /** Load (and cache) the database, creating it on first run. */
  function loadDB() {
    if (cache) return cache;
    const stored = read();
    cache = stored ? migrate(stored) : emptyDB();
    if (!stored) write(cache);
    return cache;
  }

  /** Persist the in-memory database and notify subscribers. */
  function saveDB(db = cache) {
    cache = db;
    cache.meta.updatedAt = new Date().toISOString();
    write(cache);
    listeners.forEach((fn) => {
      try {
        fn(cache);
      } catch (err) {
        console.error("[AutoCare] storage listener failed", err);
      }
    });
    return cache;
  }

  /** Mutate the database inside a callback, then save exactly once. */
  function update(mutator) {
    const db = loadDB();
    mutator(db);
    return saveDB(db);
  }

  function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  /* ------------------------------------------------------- collections -- */

  const list = (name) => (loadDB()[name] || []).slice();

  const find = (name, id) => (loadDB()[name] || []).find((r) => r.id === id) || null;

  function insert(name, record) {
    const row = { id: AC.utils.uid(name.slice(0, 3)), createdAt: new Date().toISOString(), ...record };
    update((db) => {
      db[name] = db[name] || [];
      db[name].push(row);
    });
    return row;
  }

  function patch(name, id, changes) {
    let updated = null;
    update((db) => {
      const idx = (db[name] || []).findIndex((r) => r.id === id);
      if (idx === -1) return;
      db[name][idx] = { ...db[name][idx], ...changes, updatedAt: new Date().toISOString() };
      updated = db[name][idx];
    });
    return updated;
  }

  function remove(name, id) {
    let removed = false;
    update((db) => {
      const before = (db[name] || []).length;
      db[name] = (db[name] || []).filter((r) => r.id !== id);
      removed = db[name].length !== before;
    });
    return removed;
  }

  /** Delete every record in every collection that belongs to a vehicle. */
  function removeVehicleCascade(vehicleId) {
    update((db) => {
      db.vehicles = db.vehicles.filter((v) => v.id !== vehicleId);
      db.maintenanceRecords = db.maintenanceRecords.filter((r) => r.vehicleId !== vehicleId);
      db.expenses = db.expenses.filter((r) => r.vehicleId !== vehicleId);
      db.journeys = db.journeys.filter((r) => r.vehicleId !== vehicleId);
      db.washRecords = db.washRecords.filter((r) => r.vehicleId !== vehicleId);
      // If the deleted vehicle was primary, promote the first remaining one.
      if (db.vehicles.length && !db.vehicles.some((v) => v.isPrimary)) {
        db.vehicles[0].isPrimary = true;
      }
    });
  }

  /* ---------------------------------------------------------- settings -- */

  const getSettings = () => loadDB().settings;

  function setSettings(changes) {
    update((db) => {
      db.settings = {
        ...db.settings,
        ...changes,
        notifications: { ...db.settings.notifications, ...(changes.notifications || {}) },
        manualLocation: { ...db.settings.manualLocation, ...(changes.manualLocation || {}) },
      };
    });
    return getSettings();
  }

  /* --------------------------------------------- import / export / reset -- */

  function exportDB() {
    const db = loadDB();
    return JSON.stringify(
      {
        app: "AutoCare Pro",
        exportedAt: new Date().toISOString(),
        schemaVersion: SCHEMA_VERSION,
        data: db,
      },
      null,
      2
    );
  }

  /**
   * Import a previously exported file. The payload is *never* trusted:
   * unknown keys are dropped by `migrate`, and every record is filtered to
   * plain objects with an id so a malformed file cannot corrupt the app.
   */
  function importDB(jsonText) {
    let parsed;
    try {
      parsed = JSON.parse(jsonText);
    } catch (err) {
      throw new Error("The selected file is not valid JSON.");
    }

    const payload = parsed && parsed.data ? parsed.data : parsed;
    if (!payload || typeof payload !== "object" || !Array.isArray(payload.vehicles)) {
      throw new Error("The selected file is not valid AutoCare Pro data.");
    }

    const clean = migrate(payload);
    COLLECTIONS.forEach((name) => {
      clean[name] = clean[name]
        .filter((r) => r && typeof r === "object")
        .map((r) => ({ ...r, id: r.id || AC.utils.uid(name.slice(0, 3)) }));
    });

    cache = clean;
    saveDB(cache);
    return cache;
  }

  function resetDB({ seed = true } = {}) {
    cache = emptyDB();
    if (seed && AC.seed) AC.seed.apply(cache);
    saveDB(cache);
    return cache;
  }

  /** Approximate bytes used by the database — surfaced in Settings. */
  function usageBytes() {
    try {
      const raw = window.localStorage.getItem(KEY) || "";
      return new Blob([raw]).size;
    } catch (err) {
      return 0;
    }
  }

  const isAvailable = () => storageAvailable;

  return {
    KEY,
    SCHEMA_VERSION,
    COLLECTIONS,
    DEFAULT_SETTINGS,
    emptyDB,
    loadDB,
    saveDB,
    update,
    subscribe,
    list,
    find,
    insert,
    patch,
    remove,
    removeVehicleCascade,
    getSettings,
    setSettings,
    exportDB,
    importDB,
    resetDB,
    usageBytes,
    isAvailable,
  };
})();
