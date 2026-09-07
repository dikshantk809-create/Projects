# Viva guide

Short, correct answers to the questions an examiner is most likely to ask, plus
a suggested demo route. Every answer maps to code you can open on the spot.

---

## A. Five-minute demo script

1. **Launch** — splash screen (grid → logo → accent line → loader), then the
   dashboard fades in. *"The splash is CSS keyframes only; it is removed from the
   DOM after ~1.4 s and respects `prefers-reduced-motion`."*
2. **Dashboard** — point at `02 / 01 / 01 / ₹79,420`. *"None of these are typed
   in. Vehicle count is `vehicles.length`; service-due and overdue come from the
   maintenance engine; cost is summed from records with linked expenses
   subtracted so nothing is double counted."*
3. **Health card** — 87%, ENGINE 82 / TYRES 90 / BATTERY 95 / BRAKES 85, and the
   sentence under the bars explaining the weighting.
4. **Maintenance** — Engine Oil card: *"450 km remaining, DUE SOON. The record was
   at 30,690 km, the interval is 5,000, the odometer is 35,240."* Switch the
   vehicle picker to Honda City and show the red OVERDUE card.
5. **Wash Advisor** — the gauge animates 0 → 59. Open **Why this score?**:
   36/60 time, 11/20 pollution, 5.4/10 dust, 6.3/10 usage. *"This is the whole
   point of the project — the recommendation is explainable."*
6. **Record a wash** → the gauge drops to ~15 CLEAN. *"Live recomputation, not a
   stored value."*
7. **Analytics** — eight charts, change the scope to one vehicle and the range to
   3M; everything redraws.
8. **Settings → Data management** — Export JSON, show the file; storage meter.
9. **DevTools → Application** — service worker active, cache populated; tick
   *Offline* and reload: the app still works.
10. **Resize to 390 px** — bottom navigation, single column, modals as sheets.

---

## B. Likely questions

### "Is this just CRUD?"

No. CRUD is the substrate. Three algorithms sit on top — a dual-deadline service
predictor, a weighted four-subsystem health score, and a four-factor
environmental wash score — and each one shows its working in the UI.
`js/health.js`, `js/washAdvisor.js`, `js/maintenance.js`.

### "How is the health score calculated?"

Four subsystems start at 100 and lose points for service wear (quadratic below
the interval, linear and steep past due), vehicle age (0.8/year, cap 10) and
distance (6 per 100,000 km, cap 10). The overall figure is a weighted mean —
engine 35%, brakes 25%, tyres 20%, battery 20% — minus 4 per overdue service.
Everything is clamped to 0–100. Worked example in `docs/algorithms.md §2`.

### "Why is the wear penalty quadratic?"

Because risk is not linear. Half-way through an oil interval a car is basically
fine (3.75 points lost); at 90% it is approaching due (12.2); past due it
degrades quickly (linear ×50). A linear penalty would report a healthy car as
50% unhealthy at the interval midpoint, which is wrong.

### "How does the wash score work? Why not 'every 7 days'?"

Four weighted factors summing to 100: time 60 (saturating at 20 days, multiplied
by a weather soiling factor), pollution 20 (AQI 50%, PM2.5 20%, PM10 15%, NO₂ 8%,
O₃ 7%), road dust 10 (PM10, air dryness, journey dust, minus a rain credit),
usage 10 (distance since wash + trip frequency). Seven days in clean humid air
with no driving scores ~21 (CLEAN); the same seven days in AQI-300 air after
400 dusty kilometres scores ~78 (WASH NOW). A calendar cannot tell those apart.

### "Where does the AQI come from? Do you need an API key?"

No key is needed. The default provider is deterministic offline data so the app
is fully functional with no network. Switching to *Live* in Settings uses
Open-Meteo, which is key-free by design — a frontend app cannot keep a secret,
so I chose a provider that does not require one. Adding a keyed provider means
implementing the same three-member interface; the Wash Advisor never changes.
`js/environment.js`, `docs/api-integration.md`.

### "What happens if the user denies location permission?"

Nothing breaks. Location is opt-in; the default is a configured manual location.
In device mode a denial or a 7-second timeout silently falls back to manual,
and a failed live fetch falls back to the offline provider with a banner
explaining why. `resolveLocation()` and `load()` in `js/environment.js`.

### "How is data stored? Why one key?"

One `localStorage` key, `autocareProDB`, holding one structured document with
five collections plus environment cache and settings. One document makes export,
import, migration and reset one operation each instead of a dozen. `storage.js`
is the only file that touches `localStorage`, which is the whole point — see the
next question.

### "How would you move this to a real database?"

Reimplement `read()` and `write()` in `js/storage.js`. Every other module goes
through the repository API (`list`, `find`, `insert`, `patch`, `remove`,
`removeVehicleCascade`), so no page, algorithm or component changes. For SQL
each array becomes a table with `vehicleId` as a foreign key —
`removeVehicleCascade` is already written as `ON DELETE CASCADE` semantics.

### "What is `schemaVersion` for?"

Migration. `loadDB()` runs `migrate()` on whatever it reads, backfilling
collections and settings that did not exist in older builds. Users upgrading
keep their data instead of losing it.

### "How does routing work without a framework?"

Hash routing. `router.js` parses `#route?key=value`, looks the name up in a page
registry, calls `render(params)` for HTML and `mount(root, params)` for
behaviour, syncs the navigation highlight and the document title, and falls back
to `#dashboard` for unknown routes. Browser back/forward work because
`hashchange` is the only trigger, and a refresh restores the same view.

### "Why not ES modules?"

Load order is explicit in `index.html`, it works from `file://` as well as
`http://`, and there is no bundler or transpiler to explain. Each file is an
IIFE attaching one object to a single `AC` namespace, so there is exactly one
global.

### "How do you avoid Chart.js memory leaks?"

`charts.js` keeps a `Map` of live chart instances keyed by canvas id. The router
calls `AC.charts.destroyAll()` **before** every `innerHTML` swap, so canvases and
resize listeners are released. Creating a chart on an id that already exists
destroys the old one first.

### "How do you prevent XSS?"

Every user- or file-supplied string passes through `AC.utils.esc()` before it is
interpolated into a template literal — vehicle names, notes, descriptions, place
names, imported data. Imported JSON is additionally parsed in a `try/catch`,
shape-checked, run through `migrate()` and re-mapped before it can reach the
database.

### "Show me the validation."

`js/validation.js` — pure functions returning `{ valid, errors, value }`. They
check required fields, number ranges, integer-ness, negative values, valid and
non-future dates, model year (1950 … next year), cross-field rules (last-service
odometer cannot exceed the current odometer; next-service odometer must exceed
the service odometer) and duplicate registration numbers, compared
case- and space-insensitively. Errors render inline under each field with
`aria-invalid` on the control.

### "What is the PWA part?"

`manifest.json` (name, start URL, standalone display, theme colour, nine icons
including a maskable one, three shortcuts) plus `service-worker.js` with three
strategies: stale-while-revalidate for the app shell, network-first with cache
fallback for the environment APIs, cache-first for fonts, and `index.html` as the
offline navigation fallback. The user's data is in `localStorage`, not the cache,
which is why the app is *functional* offline rather than merely viewable.

### "Which Web APIs did you use?"

LocalStorage, Geolocation, Service Worker, Cache Storage, Fetch + AbortController,
`matchMedia` (reduced motion), `requestAnimationFrame` (count-ups and bar
animations), FileReader (import), Blob + object URLs (export), Intl.NumberFormat
(Indian digit grouping), History/hashchange, Permissions, Online/offline events.

### "How is the responsive design different from just shrinking?"

Three genuinely different layouts. Desktop: fixed sidebar plus top bar.
Tablet ≤1024 px: the sidebar becomes an off-canvas drawer with a backdrop and a
hamburger. Phone ≤768 px: a mobile top bar plus bottom navigation, single-column
grids, full-width cards, modals converted to bottom sheets with safe-area
padding, and larger touch targets. Verified from 320 px to 1920 px with no
horizontal overflow.

### "What did you do for accessibility?"

Semantic landmarks, a skip link, labelled controls, `aria-label` on icon-only
buttons, `role="dialog"` + `aria-modal` + focus trapping + focus restoration on
modals, `aria-live` on the toast stack, visible focus rings, full keyboard
operation including the command palette, and reduced motion honoured from both
the OS setting and an in-app toggle.

### "Which part was hardest?"

Making the intelligence *explainable*. Producing a number is easy; producing a
number a user can audit means every factor has to carry its own points, cap and
plain-English reason through to the UI. That constraint shaped the return shape
of both scoring functions — see the `factors` arrays in `health.js` and
`washAdvisor.js`.

---

## C. Concepts this project demonstrates

| Area | Where |
|---|---|
| CRUD (all four operations, with cascade delete) | `vehicles.js`, `maintenance.js`, `expenses.js`, `journeys.js` |
| Original algorithms | `health.js`, `washAdvisor.js`, `maintenance.js` |
| Separation of concerns | `storage → logic → pages → DOM` |
| Repository / adapter patterns | `storage.js`, `environment.js` providers |
| Client-side routing | `router.js` |
| Data validation | `validation.js` |
| Data visualisation | `charts.js` + 10 charts |
| Web APIs | LocalStorage, Geolocation, Service Worker, Cache, Fetch, FileReader, Blob, Intl |
| PWA / offline | `manifest.json`, `service-worker.js` |
| Responsive CSS | Grid, Flexbox, custom properties, 5 breakpoints |
| Accessibility | ARIA, focus management, reduced motion |
| Security | Output escaping, input validation, import sanitisation, no secrets |
| Software design | Design tokens, component builders, event delegation, pure functions |
