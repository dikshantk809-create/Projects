/* ==========================================================================
   AutoCare Pro — environment.js
   Environmental Intelligence layer.

       LOCATION → ENVIRONMENT SERVICE → AQI + WEATHER → EXPOSURE → WASH SCORE

   The service is written against a provider interface so the data source can
   be swapped without touching the Wash Advisor:

       MockEnvironmentProvider   deterministic offline data (default)
       LiveEnvironmentProvider   Open-Meteo air-quality + forecast APIs

   Open-Meteo is used for the live provider because it needs NO API KEY, which
   keeps the promise that nothing secret ever ships in frontend source. To move
   to a keyed provider (OpenWeather, IQAir, WAQI) implement the same three
   methods and register it in PROVIDERS — see docs/api-integration.md.
   ========================================================================== */

window.AC = window.AC || {};

AC.environment = (function () {
  "use strict";

  const U = AC.utils;
  const C = AC.constants;
  const S = AC.storage;

  const CACHE_TTL_MIN = 30;

  /* ------------------------------------------------- provider interface --
     A provider must expose:
        id           : string
        label        : string
        needsNetwork : boolean
        fetch(location) -> Promise<EnvironmentReading>
  ---------------------------------------------------------------------- */

  /**
   * Deterministic offline data set. Values are realistic for a North-Indian
   * city and vary slightly by day-of-year so charts are not flat lines, but
   * they are reproducible: the same day always yields the same reading.
   */
  const MockEnvironmentProvider = {
    id: "mock",
    label: "Mock / Offline",
    needsNetwork: false,

    /** Synchronous so the UI always has a reading, even before the first fetch. */
    read(location) {
      const day = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / U.MS_DAY);
      // Cheap deterministic oscillation — no randomness, so results repeat.
      const wave = (offset, amp) => Math.sin((day + offset) / 9) * amp;
      const rainy = day % 11 === 0;

      return {
        location: location || { label: "Patiala, Punjab", lat: 30.3398, lon: 76.3869, source: "default" },
        aqi: Math.round(U.clamp(145 + wave(0, 42), 40, 340)),
        pm25: Math.round(U.clamp(68 + wave(3, 22), 8, 210)),
        pm10: Math.round(U.clamp(112 + wave(6, 34), 15, 320)),
        no2: Math.round(U.clamp(34 + wave(2, 11), 4, 120)),
        o3: Math.round(U.clamp(52 + wave(5, 16), 5, 160)),
        temperature: Math.round(U.clamp(32 + wave(8, 7), 4, 48)),
        humidity: Math.round(U.clamp(58 + wave(11, 20), 12, 96)),
        precipitation: rainy ? 3.4 : 0,
        weather: rainy ? "Rain" : "Clear",
        provider: "mock",
        isDemo: true,
        fetchedAt: new Date().toISOString(),
      };
    },

    fetch(location) {
      return Promise.resolve(MockEnvironmentProvider.read(location));
    },
  };

  /** WMO weather codes → the short labels the UI shows. */
  function describeWeather(code, precipitation) {
    if (precipitation > 0.2) return "Rain";
    if (code === 0) return "Clear";
    if (code <= 3) return "Cloudy";
    if (code >= 45 && code <= 48) return "Fog";
    if (code >= 51 && code <= 67) return "Rain";
    if (code >= 71 && code <= 77) return "Snow";
    if (code >= 80 && code <= 82) return "Showers";
    if (code >= 95) return "Storm";
    return "Clear";
  }

  const LiveEnvironmentProvider = {
    id: "live",
    label: "Open-Meteo (live, key-free)",
    needsNetwork: true,
    async fetch(location) {
      const loc = location || { lat: 30.3398, lon: 76.3869, label: "Patiala, Punjab" };
      const air =
        "https://air-quality-api.open-meteo.com/v1/air-quality" +
        `?latitude=${encodeURIComponent(loc.lat)}&longitude=${encodeURIComponent(loc.lon)}` +
        "&current=pm10,pm2_5,nitrogen_dioxide,ozone,us_aqi&timezone=auto";
      const wx =
        "https://api.open-meteo.com/v1/forecast" +
        `?latitude=${encodeURIComponent(loc.lat)}&longitude=${encodeURIComponent(loc.lon)}` +
        "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code&timezone=auto";

      const withTimeout = (url) => {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 8000);
        return fetch(url, { signal: ctrl.signal }).finally(() => clearTimeout(t));
      };

      const [airRes, wxRes] = await Promise.all([withTimeout(air), withTimeout(wx)]);
      if (!airRes.ok || !wxRes.ok) throw new Error("Environment provider returned an error.");

      const airJson = await airRes.json();
      const wxJson = await wxRes.json();
      const a = airJson.current || {};
      const w = wxJson.current || {};

      return {
        location: { ...loc, source: loc.source || "manual" },
        aqi: Math.round(Number(a.us_aqi) || 0),
        pm25: Math.round(Number(a.pm2_5) || 0),
        pm10: Math.round(Number(a.pm10) || 0),
        no2: Math.round(Number(a.nitrogen_dioxide) || 0),
        o3: Math.round(Number(a.ozone) || 0),
        temperature: Math.round(Number(w.temperature_2m) || 0),
        humidity: Math.round(Number(w.relative_humidity_2m) || 0),
        precipitation: Number(w.precipitation) || 0,
        weather: describeWeather(Number(w.weather_code), Number(w.precipitation) || 0),
        provider: "open-meteo",
        isDemo: false,
        fetchedAt: new Date().toISOString(),
      };
    },
  };

  const PROVIDERS = {
    mock: MockEnvironmentProvider,
    live: LiveEnvironmentProvider,
  };

  /* ------------------------------------------------------------ location -- */

  /**
   * Resolve the location to use. Device geolocation is *optional*: if the
   * user has not opted in, or permission is denied, or the browser has no
   * geolocation API, we silently fall back to the configured manual location.
   * The application never blocks on this.
   */
  function resolveLocation() {
    const settings = S.getSettings();
    const manual = { ...settings.manualLocation, source: "manual" };

    if (settings.locationMode !== "device" || !navigator.geolocation) {
      return Promise.resolve(manual);
    }

    return new Promise((resolve) => {
      let settled = false;
      const done = (value) => {
        if (!settled) {
          settled = true;
          resolve(value);
        }
      };
      const timer = setTimeout(() => done(manual), 7000);

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          clearTimeout(timer);
          done({
            label: "Current location",
            lat: U.round(pos.coords.latitude, 4),
            lon: U.round(pos.coords.longitude, 4),
            source: "device",
          });
        },
        () => {
          clearTimeout(timer);
          done(manual);
        },
        { enableHighAccuracy: false, timeout: 6000, maximumAge: 600000 }
      );
    });
  }

  /** Reports geolocation permission without prompting, where supported. */
  async function permissionState() {
    if (!navigator.permissions || !navigator.permissions.query) return "unknown";
    try {
      const status = await navigator.permissions.query({ name: "geolocation" });
      return status.state; // granted | prompt | denied
    } catch (err) {
      return "unknown";
    }
  }

  /* ------------------------------------------------------------- service -- */

  const cacheFresh = (env) => {
    if (!env || !env.fetchedAt) return false;
    return (Date.now() - new Date(env.fetchedAt).getTime()) / 60000 < CACHE_TTL_MIN;
  };

  /**
   * The reading every screen renders from. Never null: before the first
   * asynchronous fetch completes we synthesise the deterministic mock reading,
   * so wash scores computed on any route are consistent from the first paint.
   */
  function current() {
    const db = S.loadDB();
    if (db.environment && db.environment.cache) return db.environment.cache;
    return MockEnvironmentProvider.read({ ...db.settings.manualLocation, source: "manual" });
  }

  /**
   * Fetch (or reuse) an environment reading.
   * Guarantees a resolved reading — a live failure downgrades to mock and
   * flags `degraded` so the UI can tell the user what happened.
   */
  async function load({ force = false } = {}) {
    const settings = S.getSettings();
    // NOTE: read the *stored* cache here, not current() — current() synthesises
    // a reading when nothing is stored, which would look permanently fresh.
    const db = S.loadDB();
    const cached = db.environment ? db.environment.cache : null;
    if (!force && cacheFresh(cached) && cached.providerMode === settings.environmentMode) {
      return cached;
    }

    const provider = PROVIDERS[settings.environmentMode] || MockEnvironmentProvider;
    const location = await resolveLocation();

    let reading;
    let degraded = null;

    try {
      if (provider.needsNetwork && !navigator.onLine) {
        throw new Error("Device is offline.");
      }
      reading = await provider.fetch(location);
    } catch (err) {
      degraded = err.message || "Live environment data unavailable.";
      reading = await MockEnvironmentProvider.fetch(location);
    }

    reading.providerMode = settings.environmentMode;
    reading.degraded = degraded;

    S.update((db) => {
      db.environment = {
        cache: reading,
        fetchedAt: reading.fetchedAt,
        provider: reading.provider,
      };
    });

    return reading;
  }

  /* ------------------------------------------------------------ exposure -- */

  /**
   * Normalised pollution index (0–1) from the five pollutant readings.
   * AQI dominates; the individual pollutants refine it. These weights are the
   * ones documented in docs/algorithms.md.
   */
  function pollutionIndex(env) {
    if (!env) return 0;
    const parts = [
      { v: env.aqi, max: 300, w: 0.5 },
      { v: env.pm25, max: 150, w: 0.2 },
      { v: env.pm10, max: 200, w: 0.15 },
      { v: env.no2, max: 100, w: 0.08 },
      { v: env.o3, max: 120, w: 0.07 },
    ];
    return U.clamp(
      parts.reduce((acc, p) => acc + U.clamp((Number(p.v) || 0) / p.max, 0, 1) * p.w, 0),
      0,
      1
    );
  }

  /**
   * Normalised road-dust index (0–1).
   * Coarse particulate (PM10) is the primary signal; dry air lifts more dust,
   * rain suppresses it, and recent dusty journeys add to it.
   */
  function dustIndex(env, journeyDust = 0) {
    if (!env) return 0;
    const coarse = U.clamp((Number(env.pm10) || 0) / 200, 0, 1);
    const dryness = U.clamp((70 - (Number(env.humidity) || 50)) / 60, 0, 1);
    const rainRelief = (Number(env.precipitation) || 0) > 0.2 ? -0.25 : 0;
    return U.clamp(coarse * 0.6 + dryness * 0.2 + journeyDust * 0.2 + rainRelief, 0, 1);
  }

  const aqiLabel = (aqi) => C.aqiBand(Number(aqi) || 0);

  return {
    CACHE_TTL_MIN,
    PROVIDERS,
    MockEnvironmentProvider,
    LiveEnvironmentProvider,
    describeWeather,
    resolveLocation,
    permissionState,
    current,
    load,
    pollutionIndex,
    dustIndex,
    aqiLabel,
  };
})();
