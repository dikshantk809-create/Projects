# Architecture

## 1. Layer diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                             │
│                                                                      │
│   index.html  ──  app shell (splash, sidebar, topbar, #view)         │
│        │                                                             │
│        ▼                                                             │
│   ┌──────────────────────── ROUTING ───────────────────────────┐     │
│   │  router.js   #dashboard #vehicles #maintenance #wash        │     │
│   │              #analytics #expenses #settings                 │     │
│   └───────────────────────────┬─────────────────────────────────┘     │
│                               ▼                                      │
│   ┌───────────────────────── VIEW ─────────────────────────────┐     │
│   │  pages/*.js   render(params) -> HTML   mount(root, params)  │     │
│   │  ui.js  forms.js  charts.js  icons.js                       │     │
│   └───────────────────────────┬─────────────────────────────────┘     │
│                               ▼                                      │
│   ┌──────────────────── BUSINESS LOGIC ────────────────────────┐     │
│   │  vehicles · maintenance · health · washAdvisor · journeys   │     │
│   │  expenses · analytics · notifications · environment         │     │
│   │  validation · constants · utils                             │     │
│   └───────────────────────────┬─────────────────────────────────┘     │
│                               ▼                                      │
│   ┌────────────────────────  DATA  ────────────────────────────┐     │
│   │  storage.js  →  localStorage["autocareProDB"]               │     │
│   │  seed.js     →  first-run demo document                     │     │
│   └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│   service-worker.js  ── app-shell cache · network-first for APIs     │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼  (only in "live" mode, optional)
                    Open-Meteo air-quality + forecast APIs
```

**The rule that keeps it clean:** a page never calls `localStorage`; a
business-logic module never calls `document`. Everything crosses the boundary
through `AC.storage.*` on one side and `render()/mount()` on the other.

## 2. Module namespace

There is no bundler, so every file is an IIFE that attaches one object to a
single global namespace:

```js
window.AC = window.AC || {};
AC.health = (function () { "use strict"; /* … */ return { … }; })();
```

This was a deliberate choice over ES modules:

- it works from `file://` as well as `http://` (a marker can just open the file);
- load order is explicit and visible in `index.html`;
- it stays trivial to explain in a viva — no imports, no bundler, no transpiler.

The cost is that load order matters. `index.html` groups the scripts as
**foundation → business logic → presentation → pages → bootstrap**, which is
also the dependency order.

## 3. Rendering lifecycle

```
hashchange / navigate()
        │
        ▼
router.render()
        │  1. AC.charts.destroyAll()      ← prevents Chart.js canvas leaks
        │  2. view.innerHTML = page.render(params)
        │  3. page.mount(view, params)    ← event listeners, charts, animations
        │  4. AC.ui.activate(view)        ← count-ups + progress-bar animations
        │  5. syncNav() + document.title + scroll to top
        ▼
    page visible
```

`render()` is a pure string builder — given the same database it always produces
the same HTML. `mount()` owns everything stateful. Any error inside either is
caught by the router and replaced with a readable error card, so a bug in one
screen can never white-screen the app.

## 4. Event architecture

One delegated listener in `app.js` handles the entire application:

```js
document.addEventListener("click", (e) => {
  const trigger = e.target.closest("[data-action]");
  if (!trigger) return;
  AC.app.dispatch(trigger.dataset.action, { …trigger.dataset });
});
```

Adding a button anywhere in any page therefore needs **no wiring** — just
`data-action="expense:new"`. The dispatcher is the single switch that maps
actions to behaviour, which is also where confirmations live, so a destructive
action can never be triggered without one.

Actions follow `entity:verb`: `vehicle:new`, `vehicle:edit`, `vehicle:delete`,
`vehicle:primary`, `vehicle:view`, `maintenance:new/edit/delete`,
`expense:new/edit/delete`, `journey:new/delete`, `wash:new/delete`,
`env:refresh`, `alerts:open`, `palette:open`, `drawer:toggle`, `nav:<route>`.

## 5. State

There is no global state object beyond the database. Three small pieces of
transient UI state live inside their page modules (`state` in
`pages/vehicles.js`, `pages/maintenance.js`, `pages/analytics.js`,
`pages/expenses.js`, `pages/wash.js`) — filters, the selected vehicle, the
chart window, the ledger page size. They survive navigation within a session
because the module closure outlives the DOM, and they reset on reload.

After every mutation the flow is always the same:

```js
AC.<module>.<write>()      // storage write
AC.ui.toast(…)             // feedback
AC.app.refreshAll()        // re-render chrome + current route from fresh data
```

Because the whole screen is recomputed from the database, the UI can never drift
out of sync with the data.

## 6. Environment service

```
                        ┌─────────────────────────┐
resolveLocation()  ───► │   EnvironmentService    │
  manual | device       │   load({force})         │
                        │   · 30-min cache        │
                        │   · degrade on failure  │
                        └──────────┬──────────────┘
                                   │ selects
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
    MockEnvironmentProvider                LiveEnvironmentProvider
    (deterministic, offline)               (Open-Meteo, key-free)
                └──────────────────┬──────────────────┘
                                   ▼
                     reading { aqi, pm25, pm10, no2, o3,
                               temperature, humidity,
                               precipitation, weather, … }
                                   ▼
              pollutionIndex()            dustIndex()
                                   ▼
                        AC.wash.calculateWashScore()
```

`current()` never returns `null`: if nothing is cached yet it synthesises the
deterministic mock reading, so a wash score computed on the Vehicles page during
the first paint matches the one on the Wash Advisor a moment later.

## 7. Service worker strategies

| Request | Strategy | Why |
|---|---|---|
| Same-origin shell (HTML/CSS/JS/icons/Chart.js) | stale-while-revalidate | Instant cold start, silent background updates |
| Open-Meteo API | network-first, cache fallback | Fresh air data matters; stale beats nothing |
| Cross-origin (fonts) | cache-first, network fallback | Fonts rarely change |
| Offline navigation with no match | serve `index.html` | The SPA can route itself |

The user's records are **not** in the cache — they are in `localStorage`, which
is why the app is fully functional offline rather than merely viewable.

## 8. Design system

`css/variables.css` is the single source of truth for colour, type, spacing,
radius, elevation, layout and motion. No other stylesheet contains a raw hex
value except inside gradients that mix tokens. Retheming the product means
editing one file.

Motion is transform/opacity only (GPU-friendly), and every animation is disabled
by `@media (prefers-reduced-motion: reduce)` and by the manual
`.reduce-motion` class the Settings toggle applies to `<html>`.

## 9. Capacitor readiness

Business logic never assumes a DOM, a URL or a server:

- all algorithms are pure functions over plain objects;
- persistence is behind a repository (swap `read()`/`write()` for
  `@capacitor/preferences` or SQLite);
- routing is hash-based, which survives a `file://` WebView;
- network access is optional and already degrades.

Wrapping the folder with Capacitor is therefore a packaging step, not a rewrite.
