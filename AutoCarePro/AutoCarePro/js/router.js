/* ==========================================================================
   AutoCare Pro — router.js
   A tiny hash router that gives the app single-page navigation without a
   framework. Responsibilities:
     - map `#route?key=value` to a registered page module
     - render into #view and run the page's mount hook
     - keep sidebar / bottom-bar active states in sync
     - destroy live charts before swapping pages (no canvas leaks)
     - fall back to #dashboard for unknown routes
   Browser back/forward and a hard refresh all restore the same view.
   ========================================================================== */

window.AC = window.AC || {};

AC.router = (function () {
  "use strict";

  const U = AC.utils;
  const DEFAULT = "dashboard";

  const pages = {};
  let current = null;
  const listeners = new Set();

  /** Register a page module: { render(params) -> html, mount?(root, params) }. */
  function register(name, page) {
    pages[name] = page;
  }

  /** Parse `#vehicles?id=abc` into { name: "vehicles", params: { id: "abc" } }. */
  function parse(hash = window.location.hash) {
    const raw = String(hash || "").replace(/^#\/?/, "");
    if (!raw) return { name: DEFAULT, params: {} };
    const [name, query] = raw.split("?");
    const params = {};
    if (query) {
      query.split("&").forEach((pair) => {
        const [k, v] = pair.split("=");
        if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || "");
      });
    }
    return { name: pages[name] ? name : DEFAULT, params };
  }

  function navigate(name, params = {}) {
    const query = Object.keys(params)
      .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
      .join("&");
    const next = `#${name}${query ? `?${query}` : ""}`;
    if (window.location.hash === next) render();
    else window.location.hash = next;
  }

  /** Re-render the current route in place (used after every data mutation). */
  const refresh = () => render();

  function render() {
    const route = parse();
    const page = pages[route.name];
    const view = U.$("#view");
    if (!page || !view) return;

    // Chart.js keeps references to canvases; clear them before the DOM swap.
    AC.charts.destroyAll();

    try {
      view.innerHTML = page.render(route.params) || "";
      if (typeof page.mount === "function") page.mount(view, route.params);
      AC.ui.activate(view);
    } catch (err) {
      console.error(`[AutoCare] Failed to render "${route.name}"`, err);
      view.innerHTML = renderCrash(route.name, err);
    }

    current = route;
    syncNav(route.name);
    document.title = `${titleFor(route.name)} · AutoCare Pro`;

    // Keep the reading position sensible on navigation.
    window.scrollTo({ top: 0, behavior: U.prefersReducedMotion() ? "auto" : "smooth" });

    listeners.forEach((fn) => fn(route));
  }

  function renderCrash(name, err) {
    return `
      <section class="page">
        <div class="empty">
          <span class="empty__icon">${AC.icons.get("alert", { size: 24 })}</span>
          <h3 class="empty__title">This screen could not be displayed</h3>
          <p class="empty__text">
            An error occurred while rendering the ${U.esc(name)} view. Your data is safe —
            try another page, or reload the application.
          </p>
          <code style="max-width:60ch">${U.esc(err && err.message ? err.message : String(err))}</code>
        </div>
      </section>`;
  }

  function titleFor(name) {
    const route = AC.constants.ROUTES.find((r) => r.hash === name);
    return route ? route.label : "Dashboard";
  }

  function syncNav(name) {
    U.$$("[data-route]").forEach((el) => {
      const active = el.dataset.route === name;
      el.classList.toggle("is-active", active);
      if (el.hasAttribute("aria-current") || active) {
        if (active) el.setAttribute("aria-current", "page");
        else el.removeAttribute("aria-current");
      }
    });
  }

  function onChange(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function start() {
    window.addEventListener("hashchange", render);
    if (!window.location.hash) window.location.hash = `#${DEFAULT}`;
    render();
  }

  return {
    DEFAULT,
    register,
    parse,
    navigate,
    refresh,
    render,
    start,
    onChange,
    get current() {
      return current;
    },
  };
})();
