/* ==========================================================================
   AutoCare Pro — notifications.js
   The alert engine. Alerts are *computed* from current state every time the
   UI asks for them — there is no stored list of hard-coded alert cards.
   Priority order: CRITICAL > WARNING > INFO > SUCCESS.
   ========================================================================== */

window.AC = window.AC || {};

AC.notifications = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const M = AC.maintenance;

  const PRIORITY = { critical: 0, warning: 1, info: 2, success: 3 };

  /**
   * Build the current alert list.
   * @param {object} env   optional environment reading (avoids a refetch)
   * @returns {object[]}   sorted, most urgent first
   */
  function generate(env = null) {
    const settings = AC.storage.getSettings();
    const vehicles = AC.vehicles.all();
    const alerts = [];

    if (!vehicles.length) {
      alerts.push({
        id: "no-vehicles",
        priority: "info",
        icon: "car",
        title: "No vehicles registered",
        meta: "Add your first vehicle to unlock health, maintenance and wash tracking.",
        action: { label: "Add vehicle", event: "vehicle:new" },
      });
      return alerts;
    }

    vehicles.forEach((vehicle) => {
      /* --- maintenance ------------------------------------------------- */
      if (settings.notifications.service) {
        M.scheduleFor(vehicle).forEach((row) => {
          if (row.status === M.STATUS.OVERDUE) {
            alerts.push({
              id: `overdue-${vehicle.id}-${row.type}`,
              priority: "critical",
              icon: "alert",
              vehicleId: vehicle.id,
              title: `${row.label.toUpperCase()} OVERDUE`,
              meta: `${vehicle.name} · ${describeRemaining(row, settings.units)}`,
              action: { label: "Log service", event: "maintenance:new", payload: { vehicleId: vehicle.id, type: row.type } },
            });
          } else if (row.status === M.STATUS.DUE_SOON) {
            alerts.push({
              id: `due-${vehicle.id}-${row.type}`,
              priority: "warning",
              icon: "wrench",
              vehicleId: vehicle.id,
              title: `${row.label.toUpperCase()} DUE SOON`,
              meta: `${vehicle.name} · ${describeRemaining(row, settings.units)}`,
              action: { label: "Log service", event: "maintenance:new", payload: { vehicleId: vehicle.id, type: row.type } },
            });
          }
        });
      }

      /* --- health ------------------------------------------------------ */
      const health = AC.health.calculateVehicleHealth(vehicle);
      if (health.overall < 50) {
        alerts.push({
          id: `health-${vehicle.id}`,
          priority: "critical",
          icon: "heart",
          vehicleId: vehicle.id,
          title: "VEHICLE HEALTH CRITICAL",
          meta: `${vehicle.name} is at ${health.overall}%. ${weakest(health)}`,
          action: { label: "Open vehicle", hash: "vehicles" },
        });
      } else if (health.overall < 75) {
        alerts.push({
          id: `health-${vehicle.id}`,
          priority: "warning",
          icon: "heart",
          vehicleId: vehicle.id,
          title: "VEHICLE HEALTH NEEDS ATTENTION",
          meta: `${vehicle.name} is at ${health.overall}%. ${weakest(health)}`,
          action: { label: "Open vehicle", hash: "vehicles" },
        });
      }

      /* --- wash -------------------------------------------------------- */
      if (settings.notifications.wash) {
        const wash = AC.wash.calculateWashScore(vehicle, env);
        if (wash.score >= 76) {
          alerts.push({
            id: `wash-${vehicle.id}`,
            priority: "warning",
            icon: "droplet",
            vehicleId: vehicle.id,
            title: "WASH RECOMMENDED",
            meta: `${vehicle.name} · wash score ${wash.score}/100 · ${wash.daysSinceWash} days since last wash`,
            action: { label: "Open advisor", hash: "wash" },
          });
        } else if (wash.score >= 56) {
          alerts.push({
            id: `wash-${vehicle.id}`,
            priority: "info",
            icon: "droplet",
            vehicleId: vehicle.id,
            title: "WASH RECOMMENDED SOON",
            meta: `${vehicle.name} · wash score ${wash.score}/100`,
            action: { label: "Open advisor", hash: "wash" },
          });
        }
      }
    });

    /* --- environment ---------------------------------------------------- */
    const reading = env || AC.environment.current();
    if (settings.notifications.environment && reading && reading.aqi >= 201) {
      const band = C.aqiBand(reading.aqi);
      alerts.push({
        id: "env-aqi",
        priority: reading.aqi >= 301 ? "warning" : "info",
        icon: "wind",
        title: "HIGH POLLUTION EXPOSURE",
        meta: `AQI ${reading.aqi} (${band.label}) at ${
          reading.location ? reading.location.label : "your location"
        }. Contamination builds up faster than usual.`,
        action: { label: "Open advisor", hash: "wash" },
      });
    }

    /* --- all clear ------------------------------------------------------ */
    if (!alerts.length) {
      alerts.push({
        id: "all-clear",
        priority: "success",
        icon: "check",
        title: "ALL SYSTEMS NOMINAL",
        meta: "No overdue services, no wash required and vehicle health is within range.",
      });
    }

    return alerts.sort((a, b) => PRIORITY[a.priority] - PRIORITY[b.priority]);
  }

  function describeRemaining(row, units) {
    const bits = [];
    if (row.remainingKm !== null) {
      bits.push(
        row.remainingKm < 0
          ? `${U.formatDistance(Math.abs(row.remainingKm), units)} past due`
          : `${U.formatDistance(row.remainingKm, units)} remaining`
      );
    }
    if (row.remainingDays !== null) {
      bits.push(
        row.remainingDays < 0
          ? `${Math.abs(row.remainingDays)} days past due`
          : `${row.remainingDays} days remaining`
      );
    }
    return bits.join(" · ") || "Interval reached";
  }

  const weakest = (health) => {
    const w = U.sortBy(health.factors, (f) => f.score, "asc")[0];
    return w ? `${U.titleCase(w.label)} at ${w.score}% — ${w.reason}.` : "";
  };

  const criticalCount = (alerts) => alerts.filter((a) => a.priority === "critical").length;

  const actionableCount = (alerts) =>
    alerts.filter((a) => a.priority === "critical" || a.priority === "warning").length;

  return { PRIORITY, generate, criticalCount, actionableCount };
})();
