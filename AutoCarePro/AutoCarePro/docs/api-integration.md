# Adding a real AQI / weather API

AutoCare Pro ships with two providers and a service that selects between them.
Adding a third is a ~40-line file plus one registry entry — the Wash Advisor
never changes.

---

## 1. The provider interface

A provider is any object with these three members:

```js
const MyProvider = {
  id: "myprovider",              // stable key, also stored on each reading
  label: "My Provider",          // shown in Settings
  needsNetwork: true,            // true → the service skips it when offline

  /**
   * @param {{lat:number, lon:number, label:string}} location
   * @returns {Promise<EnvironmentReading>}
   */
  async fetch(location) { /* … */ },
};
```

### The reading contract

Every provider must resolve to this exact shape. The Wash Advisor reads nothing
else, which is why providers are interchangeable.

| Field | Type | Notes |
|---|---|---|
| `location` | `{ label, lat, lon, source }` | Echo back what you were given |
| `aqi` | number | Composite index, 0–500 scale |
| `pm25` | number | µg/m³ |
| `pm10` | number | µg/m³ |
| `no2` | number | µg/m³ |
| `o3` | number | µg/m³ |
| `temperature` | number | °C |
| `humidity` | number | % relative |
| `precipitation` | number | mm in the last hour |
| `weather` | string | `Clear` `Cloudy` `Rain` `Showers` `Storm` `Snow` `Fog` |
| `provider` | string | Your `id` |
| `isDemo` | boolean | `true` only for offline/synthetic data |
| `fetchedAt` | ISO string | `new Date().toISOString()` |

`weather` matters: it feeds the soiling multiplier in the wash score. Map your
provider's condition codes onto the seven strings above — `AC.environment.describeWeather()`
already does this for WMO codes and is a good model.

---

## 2. What ships today

### `MockEnvironmentProvider` (default)

Deterministic offline data. Values oscillate with day-of-year so charts are not
flat lines, but the same day always produces the same reading — which makes
demos and viva walk-throughs reproducible. It also exposes a **synchronous**
`read(location)` used by `AC.environment.current()` so the UI always has a
reading, even before the first async fetch resolves.

### `LiveEnvironmentProvider`

[Open-Meteo](https://open-meteo.com) — chosen deliberately because it needs **no
API key**. A frontend-only application cannot keep a secret: anything in the
JavaScript is public. Two endpoints, both CORS-enabled, 8-second timeout via
`AbortController`:

```
https://air-quality-api.open-meteo.com/v1/air-quality
    ?latitude=..&longitude=..
    &current=pm10,pm2_5,nitrogen_dioxide,ozone,us_aqi&timezone=auto

https://api.open-meteo.com/v1/forecast
    ?latitude=..&longitude=..
    &current=temperature_2m,relative_humidity_2m,precipitation,weather_code&timezone=auto
```

---

## 3. Template: adding OpenWeather (keyed)

```js
/* js/providers/openweather.js — loaded after environment.js */
AC.environment.PROVIDERS.openweather = {
  id: "openweather",
  label: "OpenWeatherMap",
  needsNetwork: true,

  async fetch(location) {
    // NEVER hard-code a key here. See §4 for where it belongs.
    const key = AC.storage.getSettings().openWeatherKey;
    if (!key) throw new Error("No OpenWeather key configured.");

    const base = "https://api.openweathermap.org/data/2.5";
    const q = `lat=${location.lat}&lon=${location.lon}&appid=${key}`;

    const [airRes, wxRes] = await Promise.all([
      fetch(`${base}/air_pollution?${q}`),
      fetch(`${base}/weather?${q}&units=metric`),
    ]);
    if (!airRes.ok || !wxRes.ok) throw new Error("OpenWeather request failed.");

    const air = (await airRes.json()).list[0];
    const wx = await wxRes.json();

    // OpenWeather's AQI is 1–5; rescale to the 0–500 band the app expects.
    const aqi = [0, 40, 90, 150, 250, 400][air.main.aqi] || 0;

    return {
      location: { ...location, source: location.source || "manual" },
      aqi,
      pm25: Math.round(air.components.pm2_5),
      pm10: Math.round(air.components.pm10),
      no2: Math.round(air.components.no2),
      o3: Math.round(air.components.o3),
      temperature: Math.round(wx.main.temp),
      humidity: Math.round(wx.main.humidity),
      precipitation: (wx.rain && wx.rain["1h"]) || 0,
      weather: mapCondition(wx.weather[0].main),
      provider: "openweather",
      isDemo: false,
      fetchedAt: new Date().toISOString(),
    };
  },
};

function mapCondition(main) {
  return { Clear: "Clear", Clouds: "Cloudy", Rain: "Rain", Drizzle: "Rain",
           Thunderstorm: "Storm", Snow: "Snow", Mist: "Fog", Fog: "Fog",
           Haze: "Fog" }[main] || "Clear";
}
```

Then:

1. Add `<script src="js/providers/openweather.js"></script>` to `index.html`
   (after `js/environment.js`).
2. Add `"openweather"` to the provider buttons in
   `js/pages/settings.js → environmentSection()`.
3. Add the file to `SHELL_ASSETS` in `service-worker.js`, and add the API host to
   `ENV_HOSTS` so it uses the network-first strategy.

Nothing in `washAdvisor.js`, the pages or the components changes.

---

## 4. Where an API key belongs

**Not in the source.** Three acceptable options, best first:

1. **Key-free provider** — what the app does today. No secret, no problem.
2. **User-supplied key** — add a password field in Settings, store it in
   `settings`, and let each user bring their own. It is their key on their
   device; it is never committed and never shared.
3. **Backend proxy** — a tiny server route (`/api/environment?lat=..&lon=..`)
   that holds the key and forwards the request. This is the only correct answer
   for a production app with a shared key, and the provider then simply points
   at your own origin.

`.gitignore` already excludes `.env`. Never commit real credentials.

---

## 5. Failure handling (already built)

`EnvironmentService.load()`:

1. returns the cached reading if it is under 30 minutes old and the mode matches;
2. resolves the location (device geolocation if enabled, else manual, with a
   7-second timeout and a silent fallback);
3. skips a network provider entirely when `navigator.onLine` is false;
4. wraps the provider call in `try/catch` — **any** failure falls back to
   `MockEnvironmentProvider` and sets `reading.degraded` with the reason;
5. caches the result in `db.environment`.

The Wash Advisor and Dashboard both render a warning banner when `degraded` is
set, so a user is told they are looking at offline reference data. The
application never blocks, never spins forever and never throws because the
network is unavailable.

---

## 6. Location handling

```js
AC.environment.resolveLocation()   // → { label, lat, lon, source }
AC.environment.permissionState()   // → "granted" | "prompt" | "denied" | "unknown"
```

Device geolocation is **opt-in** (Settings → Location → Device). Nothing in the
app requires it: with `locationMode: "manual"` the configured coordinates are
used, and even in device mode a denial or timeout silently falls back to manual.
`permissionState()` reports the browser's permission without triggering a prompt,
which is what the Settings "Check" button shows.
