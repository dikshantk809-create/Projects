/* ==========================================================================
   AutoCare Pro — pages/vehicles.js
   Full CRUD over the garage: add, view, edit, delete and set primary.
   ========================================================================== */

window.AC = window.AC || {};
AC.pages = AC.pages || {};

AC.pages.vehicles = (function () {
  "use strict";

  const U = AC.utils;
  const UI = AC.ui;
  const I = AC.icons;

  let filter = { q: "", fuel: "all", sort: "primary" };

  function render() {
    const settings = AC.storage.getSettings();
    const env = AC.environment.current();
    const vehicles = applyFilter(AC.vehicles.all());

    return `
      <section class="page">
        <header class="page-head">
          <div>
            <div class="page-head__eyebrow">Garage</div>
            <h1>Vehicles</h1>
            <p class="page-head__sub">
              Every vehicle you manage, with a live health score, the next service due and
              wash status computed from its own records.
            </p>
          </div>
          <div class="page-head__actions">
            <button class="btn" data-action="journey:new">${I.get("route", { size: 16 })}<span>Log journey</span></button>
            <button class="btn btn--primary" data-action="vehicle:new">${I.get("plus", { size: 16 })}<span>Add vehicle</span></button>
          </div>
        </header>

        ${toolbar(vehicles.length)}

        ${
          vehicles.length
            ? `<div class="grid grid--cards stagger">${vehicles
                .map((v) => card(v, settings, env))
                .join("")}</div>`
            : AC.vehicles.count() === 0
            ? UI.emptyState({
                icon: "car",
                title: "No vehicles registered",
                text: "Add your first vehicle to start tracking maintenance, expenses and health.",
                actionLabel: "Add vehicle",
                actionEvent: "vehicle:new",
              })
            : UI.emptyState({
                icon: "filter",
                title: "No vehicles match this filter",
                text: "Try a different search term or fuel type.",
              })
        }
      </section>`;
  }

  function toolbar(shown) {
    return `
      <div class="toolbar">
        <div class="field" style="min-width:220px">
          <input class="input" id="vehSearch" type="search" placeholder="Search name, make, model or registration"
                 value="${U.esc(filter.q)}" aria-label="Search vehicles" />
        </div>
        <select class="select" id="vehFuel" aria-label="Filter by fuel type">
          <option value="all">All fuel types</option>
          ${AC.constants.FUEL_TYPES.map(
            (f) => `<option value="${f}"${filter.fuel === f ? " selected" : ""}>${f}</option>`
          ).join("")}
        </select>
        <select class="select" id="vehSort" aria-label="Sort vehicles">
          <option value="primary"${filter.sort === "primary" ? " selected" : ""}>Primary first</option>
          <option value="health"${filter.sort === "health" ? " selected" : ""}>Lowest health first</option>
          <option value="odometer"${filter.sort === "odometer" ? " selected" : ""}>Highest odometer</option>
          <option value="name"${filter.sort === "name" ? " selected" : ""}>Name A–Z</option>
        </select>
        <div class="toolbar__spacer"></div>
        <span class="count-note">${U.pad2(shown)} shown</span>
      </div>`;
  }

  function applyFilter(list) {
    const q = filter.q.trim().toLowerCase();
    let out = list.filter((v) => {
      if (filter.fuel !== "all" && v.fuelType !== filter.fuel) return false;
      if (!q) return true;
      return [v.name, v.make, v.model, v.registration].join(" ").toLowerCase().includes(q);
    });

    if (filter.sort === "health") {
      out = U.sortBy(out, (v) => AC.health.calculateVehicleHealth(v).overall, "asc");
    } else if (filter.sort === "odometer") {
      out = U.sortBy(out, (v) => Number(v.odometer) || 0, "desc");
    } else if (filter.sort === "name") {
      out = U.sortBy(out, (v) => String(v.name).toLowerCase(), "asc");
    }
    return out;
  }

  function card(vehicle, settings, env) {
    const health = AC.health.calculateVehicleHealth(vehicle);
    const next = AC.maintenance.nextService(vehicle);
    const wash = AC.wash.calculateWashScore(vehicle, env);
    const washDays = U.daysBetween(vehicle.lastWashDate);

    return `
      <article class="vehicle-card${vehicle.isPrimary ? " is-primary" : ""}" data-vehicle="${U.esc(vehicle.id)}">
        ${vehicle.isPrimary ? '<span class="vehicle-card__ribbon">Primary</span>' : ""}

        <div class="vehicle-card__head">
          <span class="vehicle-card__badge">${I.get("car", { size: 22 })}</span>
          <div style="min-width:0">
            <h3 class="vehicle-card__name">${U.esc(vehicle.name)}</h3>
            <div class="vehicle-card__spec">
              ${U.esc(vehicle.fuelType)} · ${U.esc(vehicle.year)} · ${U.esc(vehicle.registration || "No reg.")}
            </div>
          </div>
        </div>

        <div class="flex-between">
          <div class="vehicle-card__odo">
            ${U.formatDistance(vehicle.odometer, settings.units, false)}<small>${U.unitLabel(settings.units)}</small>
          </div>
          ${UI.statusPill(health.band.label, health.band.tone)}
        </div>

        ${UI.progressBar({
          label: "Health",
          value: health.overall,
          tone: health.overall >= 75 ? "success" : health.overall >= 50 ? "warning" : "critical",
        })}

        <div class="vehicle-card__grid">
          <div class="vehicle-card__cell">
            <span class="k">Next service</span>
            <span class="v${next && next.remainingKm < 0 ? " text-critical" : ""}">${
              next && next.remainingKm !== null
                ? U.formatDistance(Math.abs(next.remainingKm), settings.units, false)
                : "—"
            }</span>
            <span class="k">${
              next
                ? `${U.esc(next.label)}${next.remainingKm < 0 ? " · overdue" : ""}`
                : "No history"
            }</span>
          </div>
          <div class="vehicle-card__cell">
            <span class="k">Wash score</span>
            <span class="v text-${wash.tone === "success" ? "success" : wash.tone}">${wash.score}</span>
            <span class="k">${U.esc(wash.status)}</span>
          </div>
          <div class="vehicle-card__cell">
            <span class="k">Last wash</span>
            <span class="v">${washDays === null ? "—" : U.pad2(washDays)}</span>
            <span class="k">${washDays === null ? "Not recorded" : "days ago"}</span>
          </div>
        </div>

        <div class="vehicle-card__actions">
          <button class="btn btn--sm" data-action="vehicle:view" data-id="${U.esc(vehicle.id)}">
            ${I.get("activity", { size: 14 })}<span>Details</span>
          </button>
          <button class="btn btn--sm" data-action="vehicle:edit" data-id="${U.esc(vehicle.id)}">
            ${I.get("edit", { size: 14 })}<span>Edit</span>
          </button>
          ${
            vehicle.isPrimary
              ? ""
              : `<button class="btn btn--sm" data-action="vehicle:primary" data-id="${U.esc(vehicle.id)}">
                   ${I.get("star", { size: 14 })}<span>Set primary</span>
                 </button>`
          }
          <button class="btn btn--sm btn--icon btn--danger" data-action="vehicle:delete"
                  data-id="${U.esc(vehicle.id)}" aria-label="Delete ${U.esc(vehicle.name)}">
            ${I.get("trash", { size: 14 })}
          </button>
        </div>
        ${vehicle.source === "demo" ? `<div>${UI.demoFlag()}</div>` : ""}
      </article>`;
  }

  /* --------------------------------------------------------------- mount -- */

  function mount(root) {
    const search = U.$("#vehSearch", root);
    if (search) {
      search.addEventListener(
        "input",
        U.debounce((e) => {
          filter.q = e.target.value;
          AC.router.refresh();
          const again = U.$("#vehSearch");
          if (again) {
            again.focus();
            again.setSelectionRange(again.value.length, again.value.length);
          }
        }, 260)
      );
    }

    const fuel = U.$("#vehFuel", root);
    if (fuel) {
      fuel.addEventListener("change", (e) => {
        filter.fuel = e.target.value;
        AC.router.refresh();
      });
    }

    const sort = U.$("#vehSort", root);
    if (sort) {
      sort.addEventListener("change", (e) => {
        filter.sort = e.target.value;
        AC.router.refresh();
      });
    }
  }

  return { render, mount };
})();
