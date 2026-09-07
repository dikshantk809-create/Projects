# Storage architecture

## 1. One key, one document

```
localStorage["autocareProDB"]
```

Everything the application knows lives in a single JSON document under one key.
Scattering `vehicles`, `settings`, `expenses`… across a dozen keys would make
export, import, migration and reset four separate problems; one document makes
them one problem each.

```jsonc
{
  "schemaVersion": 1,
  "meta": { "createdAt": "…", "updatedAt": "…", "app": "AutoCare Pro", "seededAt": "…" },

  "vehicles": [
    {
      "id": "veh_demo_i20",
      "name": "Hyundai i20",
      "make": "Hyundai",
      "model": "i20 Sportz",
      "year": 2022,
      "fuelType": "Petrol",
      "odometer": 35240,
      "registration": "PB11 CX 4821",
      "lastServiceDate": "2026-04-07",
      "lastServiceOdometer": 30690,
      "lastWashDate": "2026-08-23",
      "odometerAtLastWash": 34900,
      "notes": "…",
      "isPrimary": true,
      "source": "demo",
      "createdAt": "…"
    }
  ],

  "maintenanceRecords": [
    {
      "id": "mnt_…", "vehicleId": "veh_demo_i20", "type": "engine_oil",
      "date": "2026-04-07", "odometer": 30690, "cost": 2450, "notes": "…",
      "nextServiceDate": null, "nextServiceOdometer": null, "source": "demo"
    }
  ],

  "expenses": [
    {
      "id": "exp_…", "vehicleId": "veh_demo_i20", "category": "fuel",
      "amount": 2360, "date": "2026-08-31", "description": "Fuel fill",
      "linkedRecordId": null, "source": "demo"
    }
  ],

  "journeys": [
    {
      "id": "jny_…", "vehicleId": "veh_demo_i20", "from": "Patiala", "to": "Chandigarh",
      "distanceKm": 65, "date": "2026-08-29", "avgAqi": 132,
      "dustLevel": "moderate", "source": "demo"
    }
  ],

  "washRecords": [
    { "id": "wsh_…", "vehicleId": "veh_demo_i20", "date": "2026-08-23",
      "odometer": 34900, "cost": 250, "source": "demo" }
  ],

  "environment": { "cache": { /* last reading */ }, "fetchedAt": "…", "provider": "mock" },

  "settings": {
    "userName": "Vikrant",
    "userRole": "Vehicle Owner",
    "units": "km",
    "currency": "INR",
    "notifications": { "service": true, "wash": true, "environment": true, "expense": false },
    "environmentMode": "mock",
    "locationMode": "manual",
    "manualLocation": { "label": "Patiala, Punjab", "lat": 30.3398, "lon": 76.3869 },
    "reduceMotion": false,
    "seededDemoData": true
  }
}
```

### Conventions

- **Dates** are `YYYY-MM-DD` strings — the format `<input type="date">` uses and
  the format that sorts correctly as a string.
- **Distances** are always kilometres. Miles exist only in the presentation layer
  (`AC.utils.formatDistance`), so switching units can never corrupt data.
- **Money** is a plain number of rupees. Formatting happens at render time.
- **`source`** is `"user"`, `"demo"` or `"baseline"` — this is what lets the UI
  label generated rows as DEMO DATA.
- **`linkedRecordId`** ties an expense to the service or wash record that created
  it, so deleting the record deletes its expense and totals stay honest.

## 2. Repository API (`js/storage.js`)

`storage.js` is the **only** file in the project that mentions `localStorage`.

| Function | Purpose |
|---|---|
| `loadDB()` | Read + migrate + cache the document (creates it on first run) |
| `saveDB(db?)` | Persist and notify subscribers |
| `update(fn)` | Mutate inside a callback, then save exactly once |
| `subscribe(fn)` | Observe writes |
| `list(name)` / `find(name, id)` | Read a collection / one record |
| `insert(name, row)` | Add with a generated id and `createdAt` |
| `patch(name, id, changes)` | Merge changes and stamp `updatedAt` |
| `remove(name, id)` | Delete one record |
| `removeVehicleCascade(id)` | Delete a vehicle **and** all of its records, then repair the primary flag |
| `getSettings()` / `setSettings(changes)` | Deep-merged settings access |
| `exportDB()` / `importDB(json)` | Backup / restore |
| `resetDB({seed})` | Erase, optionally re-seed |
| `usageBytes()` | Approximate document size for the storage meter |
| `isAvailable()` | False when the browser blocks storage |

Reads and writes are wrapped in `try/catch`. In private-browsing modes where
`localStorage` throws, the app switches to an in-memory document and shows a
warning toast instead of crashing.

## 3. Migration

```js
function migrate(db) { /* backfill every collection and setting, stamp version */ }
```

`loadDB()` runs `migrate()` on whatever it finds. A document written by an older
build that lacks, say, `washRecords` or `settings.reduceMotion` is *upgraded*,
not rejected and not wiped. When the schema changes, bump `SCHEMA_VERSION` and
add the transformation — old user data survives.

## 4. Export / import

**Export** (`Settings → Data management → Export JSON`) downloads:

```jsonc
{
  "app": "AutoCare Pro",
  "exportedAt": "2026-09-04T08:11:38.910Z",
  "schemaVersion": 1,
  "data": { /* the whole document */ }
}
```

Filename: `autocare-pro-backup-YYYY-MM-DD.json`.

**Import** never trusts the file:

1. `JSON.parse` inside `try/catch` → *"The selected file is not valid JSON."*
2. Shape check — the payload must be an object with a `vehicles` array →
   *"The selected file is not valid AutoCare Pro data."*
3. `migrate()` drops unknown top-level keys and backfills missing ones.
4. Every collection is filtered to plain objects and given an id if one is missing.
5. Only then does it replace the database.

Both legacy shapes are accepted: a raw document, or one wrapped in `{ data: … }`.

## 5. Seeding rule

`js/seed.js` `apply(db)` refuses to run if `vehicles`, `maintenanceRecords` or
`expenses` already contain anything. It is called in exactly two places:

- `app.js` bootstrap, only when the database is brand new and has never been seeded;
- `storage.resetDB({ seed: true })`, when the user explicitly asks for demo data.

**Your data is never overwritten on refresh.**

Dates in the seed are generated relative to *today*, so the demo always looks
current whenever the project is opened or evaluated.

## 6. Migrating to a real backend

Because every read and write goes through the repository, moving to a server
touches two functions:

```js
// today
function read()      { return JSON.parse(localStorage.getItem(KEY)); }
function write(db)   { localStorage.setItem(KEY, JSON.stringify(db)); }

// with a REST API (sketch)
async function read()    { return (await fetch("/api/db")).json(); }
async function write(db) { await fetch("/api/db", { method: "PUT", body: JSON.stringify(db) }); }
```

For a document store (Firebase / Supabase / MongoDB) the collections map 1:1.
For SQL, each array becomes a table and `vehicleId` becomes a foreign key —
`removeVehicleCascade` is already written as a cascade delete, which is exactly
what `ON DELETE CASCADE` would do.

No page, no algorithm and no component would change.

## 7. Capacity

`localStorage` gives roughly 5 MB per origin. The seeded demo database is about
25 KB. Realistic personal use — say 5 vehicles over 10 years with monthly
records — lands under 1 MB. Settings shows a live storage meter so the limit is
never a surprise, and the export file doubles as an archive.
