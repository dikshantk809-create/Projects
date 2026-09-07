/* ==========================================================================
   AutoCare Pro — constants.js
   Domain knowledge that the algorithms depend on, kept in one place so it can
   be explained (and tuned) without hunting through the codebase.

   Service intervals are typical Indian passenger-car manufacturer
   recommendations. They are deliberately data, not code: change a number here
   and every due-date, health score and alert recalculates.
   ========================================================================== */

window.AC = window.AC || {};

AC.constants = (function () {
  "use strict";

  /**
   * key      — stored on each maintenance record
   * label    — shown in the UI
   * km       — recommended interval in kilometres (null = not mileage based)
   * months   — recommended interval in months (null = not time based)
   * system   — which health subsystem this service feeds
   */
  const MAINTENANCE_TYPES = [
    { key: "engine_oil",    label: "Engine Oil",     km: 5000,  months: 6,  system: "engine" },
    { key: "oil_filter",    label: "Oil Filter",     km: 5000,  months: 6,  system: "engine" },
    { key: "air_filter",    label: "Air Filter",     km: 10000, months: 12, system: "engine" },
    { key: "fuel_filter",   label: "Fuel Filter",    km: 20000, months: 24, system: "engine" },
    { key: "spark_plugs",   label: "Spark Plugs",    km: 30000, months: 24, system: "engine" },
    { key: "coolant",       label: "Coolant",        km: 40000, months: 24, system: "engine" },
    { key: "brake_service", label: "Brake Service",  km: 15000, months: 12, system: "brakes" },
    { key: "brake_pads",    label: "Brake Pads",     km: 30000, months: 24, system: "brakes" },
    { key: "tyres",         label: "Tyres",          km: 40000, months: 36, system: "tyres" },
    { key: "wheel_align",   label: "Wheel Alignment", km: 10000, months: 12, system: "tyres" },
    { key: "battery",       label: "Battery",        km: 60000, months: 36, system: "battery" },
    { key: "chain_service", label: "Chain Service",  km: 5000,  months: 6,  system: "engine" },
    { key: "general",       label: "General Service", km: 10000, months: 12, system: "engine" },
    { key: "repair",        label: "Repair",         km: null,  months: null, system: null },
    { key: "other",         label: "Other",          km: null,  months: null, system: null },
  ];

  const MAINTENANCE_BY_KEY = MAINTENANCE_TYPES.reduce((acc, t) => {
    acc[t.key] = t;
    return acc;
  }, {});

  const maintenanceLabel = (key) =>
    (MAINTENANCE_BY_KEY[key] && MAINTENANCE_BY_KEY[key].label) || "Other";

  const EXPENSE_CATEGORIES = [
    { key: "fuel",        label: "Fuel",        color: "var(--viz-1)", hex: "#e10600" },
    { key: "maintenance", label: "Maintenance", color: "var(--viz-2)", hex: "#4aa8ff" },
    { key: "repair",      label: "Repair",      color: "var(--viz-4)", hex: "#ff9d2e" },
    { key: "wash",        label: "Wash",        color: "var(--viz-6)", hex: "#22d3ee" },
    { key: "insurance",   label: "Insurance",   color: "var(--viz-5)", hex: "#a06bff" },
    { key: "other",       label: "Other",       color: "var(--viz-8)", hex: "#7d8794" },
  ];

  const EXPENSE_BY_KEY = EXPENSE_CATEGORIES.reduce((acc, c) => {
    acc[c.key] = c;
    return acc;
  }, {});

  const FUEL_TYPES = ["Petrol", "Diesel", "CNG", "Electric", "Hybrid"];

  /** Health score bands — used for colour and the plain-English verdict. */
  const HEALTH_BANDS = [
    { min: 90, label: "EXCELLENT", tone: "success" },
    { min: 75, label: "GOOD", tone: "success" },
    { min: 50, label: "ATTENTION REQUIRED", tone: "warning" },
    { min: 0,  label: "CRITICAL", tone: "critical" },
  ];

  const healthBand = (score) =>
    HEALTH_BANDS.find((b) => score >= b.min) || HEALTH_BANDS[HEALTH_BANDS.length - 1];

  /** Wash score bands, per the Smart Wash Advisor specification. */
  const WASH_BANDS = [
    {
      min: 76,
      key: "now",
      label: "WASH NOW",
      tone: "critical",
      message: "High contamination exposure detected. Wash recommended.",
    },
    {
      min: 56,
      key: "soon",
      label: "WASH SOON",
      tone: "warning",
      message: "Vehicle wash is recommended soon.",
    },
    {
      min: 31,
      key: "monitor",
      label: "MONITOR",
      tone: "info",
      message: "Monitor vehicle condition and environmental exposure.",
    },
    {
      min: 0,
      key: "clean",
      label: "CLEAN",
      tone: "success",
      message: "Vehicle condition is good. No wash required.",
    },
  ];

  const washBand = (score) =>
    WASH_BANDS.find((b) => score >= b.min) || WASH_BANDS[WASH_BANDS.length - 1];

  /** Maximum points each factor may contribute to the 0–100 wash score. */
  const WASH_WEIGHTS = { time: 60, pollution: 20, dust: 10, usage: 10 };

  /** Weights used to combine subsystem health into an overall figure. */
  const HEALTH_WEIGHTS = { engine: 0.35, brakes: 0.25, tyres: 0.2, battery: 0.2 };

  /** Thresholds that turn a computed remainder into a status. */
  const SERVICE_THRESHOLDS = { dueSoonKm: 500, dueSoonDays: 15 };

  /** AQI descriptive bands (CPCB-style, simplified). */
  const AQI_BANDS = [
    { min: 401, label: "SEVERE", tone: "critical" },
    { min: 301, label: "VERY POOR", tone: "critical" },
    { min: 201, label: "POOR", tone: "warning" },
    { min: 101, label: "MODERATE", tone: "warning" },
    { min: 51,  label: "SATISFACTORY", tone: "success" },
    { min: 0,   label: "GOOD", tone: "success" },
  ];

  const aqiBand = (aqi) => AQI_BANDS.find((b) => aqi >= b.min) || AQI_BANDS[AQI_BANDS.length - 1];

  const LEVEL_BANDS = [
    { min: 0.7, label: "HIGH", tone: "critical" },
    { min: 0.4, label: "MODERATE", tone: "warning" },
    { min: 0,   label: "LOW", tone: "success" },
  ];

  const levelBand = (ratio) => LEVEL_BANDS.find((b) => ratio >= b.min) || LEVEL_BANDS[2];

  const ROUTES = [
    { hash: "dashboard",   label: "Dashboard",    icon: "gauge",    group: "MAIN MENU" },
    { hash: "vehicles",    label: "Vehicles",     icon: "car",      group: "MAIN MENU" },
    { hash: "maintenance", label: "Maintenance",  icon: "wrench",   group: "MAIN MENU" },
    { hash: "wash",        label: "Wash Advisor", icon: "droplet",  group: "MAIN MENU" },
    { hash: "analytics",   label: "Analytics",    icon: "chart",    group: "ANALYTICS" },
    { hash: "expenses",    label: "Expenses",     icon: "rupee",    group: "ANALYTICS" },
    { hash: "settings",    label: "Settings",     icon: "settings", group: "SYSTEM" },
  ];

  return {
    MAINTENANCE_TYPES,
    MAINTENANCE_BY_KEY,
    maintenanceLabel,
    EXPENSE_CATEGORIES,
    EXPENSE_BY_KEY,
    FUEL_TYPES,
    HEALTH_BANDS,
    healthBand,
    WASH_BANDS,
    washBand,
    WASH_WEIGHTS,
    HEALTH_WEIGHTS,
    SERVICE_THRESHOLDS,
    AQI_BANDS,
    aqiBand,
    LEVEL_BANDS,
    levelBand,
    ROUTES,
  };
})();
