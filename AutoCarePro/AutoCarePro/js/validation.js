/* ==========================================================================
   AutoCare Pro — validation.js
   Reusable field rules plus one validator per entity. Validators are pure:
   they take raw form values, return { valid, errors, value } and never touch
   the DOM or the database. The UI layer decides how to display `errors`.
   ========================================================================== */

window.AC = window.AC || {};

AC.validation = (function () {
  "use strict";

  const U = AC.utils;

  /* ------------------------------------------------------------- rules -- */

  const required = (v, label = "This field") =>
    v === null || v === undefined || String(v).trim() === "" ? `${label} is required.` : null;

  function numberIn(v, { min, max, label = "Value", integer = true } = {}) {
    if (!U.isNum(v)) return `${label} must be a number.`;
    const n = Number(v);
    if (integer && !Number.isInteger(n)) return `${label} must be a whole number.`;
    if (min !== undefined && n < min) return `${label} cannot be less than ${min}.`;
    if (max !== undefined && n > max) return `${label} cannot be greater than ${U.formatNumber(max)}.`;
    return null;
  }

  function validDate(v, { label = "Date", allowFuture = false, notBefore } = {}) {
    const d = U.toDate(v);
    if (!d) return `${label} is not a valid date.`;
    if (!allowFuture && d > U.today()) return `${label} cannot be in the future.`;
    if (notBefore) {
      const nb = U.toDate(notBefore);
      if (nb && d < nb) return `${label} cannot be before ${U.formatDate(nb)}.`;
    }
    return null;
  }

  function validYear(v) {
    const max = new Date().getFullYear() + 1;
    const err = numberIn(v, { min: 1950, max, label: "Model year" });
    if (err) return err;
    return null;
  }

  /** Registration numbers are compared case- and space-insensitively. */
  const normalizeReg = (v) => String(v || "").toUpperCase().replace(/[\s-]/g, "");

  /* ------------------------------------------------------- entity checks -- */

  function validateVehicle(input, { vehicles = [], editingId = null } = {}) {
    const errors = {};
    const value = {
      name: String(input.name || "").trim(),
      make: String(input.make || "").trim(),
      model: String(input.model || "").trim(),
      year: Number(input.year),
      fuelType: String(input.fuelType || "").trim(),
      odometer: Number(input.odometer),
      registration: String(input.registration || "").trim().toUpperCase(),
      lastServiceDate: input.lastServiceDate || "",
      lastServiceOdometer:
        input.lastServiceOdometer === "" || input.lastServiceOdometer === null
          ? null
          : Number(input.lastServiceOdometer),
      lastWashDate: input.lastWashDate || "",
      odometerAtLastWash:
        input.odometerAtLastWash === "" || input.odometerAtLastWash === null
          ? null
          : Number(input.odometerAtLastWash),
      notes: String(input.notes || "").trim(),
    };

    errors.name = required(value.name, "Vehicle name");
    errors.make = required(value.make, "Make");
    errors.model = required(value.model, "Model");
    errors.year = required(input.year, "Model year") || validYear(input.year);
    errors.fuelType = required(value.fuelType, "Fuel type");
    errors.odometer =
      required(input.odometer, "Odometer") ||
      numberIn(input.odometer, { min: 0, max: 2000000, label: "Odometer" });

    if (value.registration && !/^[A-Z0-9\s-]{4,15}$/i.test(input.registration)) {
      errors.registration = "Use 4–15 letters, digits, spaces or hyphens.";
    } else if (value.registration) {
      const clash = vehicles.some(
        (v) => v.id !== editingId && normalizeReg(v.registration) === normalizeReg(value.registration)
      );
      if (clash) errors.registration = "Another vehicle already uses this registration number.";
    }

    if (value.lastServiceDate) {
      errors.lastServiceDate = validDate(value.lastServiceDate, { label: "Last service date" });
    }
    if (value.lastWashDate) {
      errors.lastWashDate = validDate(value.lastWashDate, { label: "Last wash date" });
    }

    if (value.lastServiceOdometer !== null) {
      errors.lastServiceOdometer =
        numberIn(value.lastServiceOdometer, { min: 0, max: 2000000, label: "Last service odometer" }) ||
        (value.lastServiceOdometer > value.odometer
          ? "Last service odometer cannot exceed the current odometer."
          : null);
    }

    if (value.odometerAtLastWash !== null) {
      errors.odometerAtLastWash =
        numberIn(value.odometerAtLastWash, { min: 0, max: 2000000, label: "Odometer at last wash" }) ||
        (value.odometerAtLastWash > value.odometer
          ? "Odometer at last wash cannot exceed the current odometer."
          : null);
    }

    return finalize(errors, value);
  }

  function validateMaintenance(input, { vehicles = [] } = {}) {
    const errors = {};
    const value = {
      vehicleId: String(input.vehicleId || ""),
      type: String(input.type || ""),
      date: input.date || "",
      odometer: Number(input.odometer),
      cost: input.cost === "" || input.cost === null ? 0 : Number(input.cost),
      notes: String(input.notes || "").trim(),
      nextServiceDate: input.nextServiceDate || "",
      nextServiceOdometer:
        input.nextServiceOdometer === "" || input.nextServiceOdometer === null
          ? null
          : Number(input.nextServiceOdometer),
      logExpense: Boolean(input.logExpense),
    };

    errors.vehicleId = required(value.vehicleId, "Vehicle");
    if (!errors.vehicleId && !vehicles.some((v) => v.id === value.vehicleId)) {
      errors.vehicleId = "Select a vehicle that exists.";
    }

    errors.type = required(value.type, "Service type");
    errors.date = required(value.date, "Service date") || validDate(value.date, { label: "Service date" });
    errors.odometer =
      required(input.odometer, "Odometer") ||
      numberIn(input.odometer, { min: 0, max: 2000000, label: "Odometer" });
    errors.cost = numberIn(value.cost, { min: 0, max: 10000000, label: "Cost", integer: false });

    if (value.nextServiceDate) {
      errors.nextServiceDate = validDate(value.nextServiceDate, {
        label: "Next service date",
        allowFuture: true,
        notBefore: value.date,
      });
    }
    if (value.nextServiceOdometer !== null) {
      errors.nextServiceOdometer =
        numberIn(value.nextServiceOdometer, { min: 0, max: 2000000, label: "Next service odometer" }) ||
        (value.nextServiceOdometer < value.odometer
          ? "Next service odometer must be greater than the service odometer."
          : null);
    }

    return finalize(errors, value);
  }

  function validateExpense(input, { vehicles = [] } = {}) {
    const errors = {};
    const value = {
      vehicleId: String(input.vehicleId || ""),
      category: String(input.category || ""),
      amount: Number(input.amount),
      date: input.date || "",
      description: String(input.description || "").trim(),
    };

    errors.vehicleId = required(value.vehicleId, "Vehicle");
    if (!errors.vehicleId && !vehicles.some((v) => v.id === value.vehicleId)) {
      errors.vehicleId = "Select a vehicle that exists.";
    }
    errors.category = required(value.category, "Category");
    errors.amount =
      required(input.amount, "Amount") ||
      numberIn(input.amount, { min: 1, max: 10000000, label: "Amount", integer: false });
    errors.date = required(value.date, "Date") || validDate(value.date, { label: "Date" });

    return finalize(errors, value);
  }

  function validateJourney(input, { vehicles = [] } = {}) {
    const errors = {};
    const value = {
      vehicleId: String(input.vehicleId || ""),
      from: String(input.from || "").trim(),
      to: String(input.to || "").trim(),
      distanceKm: Number(input.distanceKm),
      date: input.date || "",
      avgAqi: input.avgAqi === "" || input.avgAqi === null ? null : Number(input.avgAqi),
      dustLevel: String(input.dustLevel || "moderate"),
    };

    errors.vehicleId = required(value.vehicleId, "Vehicle");
    if (!errors.vehicleId && !vehicles.some((v) => v.id === value.vehicleId)) {
      errors.vehicleId = "Select a vehicle that exists.";
    }
    errors.from = required(value.from, "Origin");
    errors.to = required(value.to, "Destination");
    errors.distanceKm =
      required(input.distanceKm, "Distance") ||
      numberIn(input.distanceKm, { min: 1, max: 5000, label: "Distance" });
    errors.date = required(value.date, "Date") || validDate(value.date, { label: "Date" });
    if (value.avgAqi !== null) {
      errors.avgAqi = numberIn(value.avgAqi, { min: 0, max: 500, label: "Average AQI" });
    }

    return finalize(errors, value);
  }

  function validateWash(input, { vehicles = [] } = {}) {
    const errors = {};
    const value = {
      vehicleId: String(input.vehicleId || ""),
      date: input.date || "",
      odometer: input.odometer === "" || input.odometer === null ? null : Number(input.odometer),
      cost: input.cost === "" || input.cost === null ? 0 : Number(input.cost),
      logExpense: Boolean(input.logExpense),
    };

    errors.vehicleId = required(value.vehicleId, "Vehicle");
    if (!errors.vehicleId && !vehicles.some((v) => v.id === value.vehicleId)) {
      errors.vehicleId = "Select a vehicle that exists.";
    }
    errors.date = required(value.date, "Wash date") || validDate(value.date, { label: "Wash date" });
    if (value.odometer !== null) {
      errors.odometer = numberIn(value.odometer, { min: 0, max: 2000000, label: "Odometer" });
    }
    errors.cost = numberIn(value.cost, { min: 0, max: 100000, label: "Cost", integer: false });

    return finalize(errors, value);
  }

  /* ----------------------------------------------------------- helpers -- */

  function finalize(errors, value) {
    Object.keys(errors).forEach((k) => {
      if (!errors[k]) delete errors[k];
    });
    return { valid: Object.keys(errors).length === 0, errors, value };
  }

  return {
    required,
    numberIn,
    validDate,
    validYear,
    normalizeReg,
    validateVehicle,
    validateMaintenance,
    validateExpense,
    validateJourney,
    validateWash,
  };
})();
