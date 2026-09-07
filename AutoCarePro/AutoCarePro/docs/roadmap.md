# Roadmap

Ordered by effort against the current architecture. Nothing here requires a
rewrite — the layering was chosen so each item is an addition.

## Near term (days)

- **Vehicle photos** — store a resized data-URL on the vehicle record; the
  storage meter in Settings already tracks the budget. Falls back to the SVG
  illustration when absent.
- **Fuel efficiency (km/l)** — add `litres` and `odometer` to fuel expenses and
  derive mileage between consecutive fills. Adds a chart and one dashboard tile.
- **CSV export** — alongside the JSON backup, for people who want the ledger in
  a spreadsheet. `AC.utils.downloadFile` already handles the download.
- **Per-vehicle budgets** — a monthly cap in settings; the existing alert engine
  gains one more rule and the dormant `notifications.expense` toggle goes live.
- **Insurance and PUC expiry** — two dates on the vehicle, two more alert rules.
- **Service-centre directory** — name, phone and address per record, so the
  history doubles as a contact list.

## Medium term (weeks)

- **Android build with Capacitor** — the business logic is already
  UI-independent and persistence is behind a repository, so this is packaging:
  swap `localStorage` for `@capacitor/preferences`, add the native geolocation
  plugin, keep everything else.
- **Cloud sync** — implement `read()`/`write()` in `storage.js` against Firebase
  or Supabase with an offline queue. No page or algorithm changes (see
  `docs/storage.md §6`).
- **Push reminders** — the service worker is already registered; add
  `periodicSync` (or a scheduled server push once sync exists) so a due service
  reaches the user without them opening the app.
- **Journey auto-capture** — sample `navigator.geolocation.watchPosition` while
  driving to log distance and route automatically, which upgrades the wash
  score's usage factor from estimated to measured.
- **Multi-vehicle comparison** — a side-by-side view of health, cost per km and
  exposure across the fleet.
- **Historical AQI along a route** — query the environment provider per journey
  instead of accepting a typed average.

## Long term (months)

- **OBD-II integration** — read live odometer, engine codes and battery voltage
  over Bluetooth. The health score already accepts subsystem inputs; real
  telemetry would replace inference for engine and battery.
- **Predictive failure model** — with enough history, learn per-vehicle wear
  rates instead of using manufacturer constants, and predict the *date* a
  service will actually be needed rather than the date it is nominally due.
- **Fleet / multi-user mode** — roles, assignment, and per-driver behaviour
  analytics. Needs the cloud-sync work first.
- **Workshop marketplace** — book a service from a due-soon card; pre-fill the
  record when the job is done.
- **Carbon exposure report** — turn the journey + AQI data already collected
  into a personal emissions and exposure summary.

## Deliberately out of scope

- **Light theme.** The instrument-cluster palette is the product's identity.
  Every colour is a CSS variable, so anyone who disagrees can retheme
  `css/variables.css` in one file.
- **A JavaScript framework.** The whole point of the exercise is that the
  architecture — repository, providers, router, component builders, event
  delegation — is legible without one.
