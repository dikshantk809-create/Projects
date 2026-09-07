/* ==========================================================================
   AutoCare Pro — service-worker.js
   Offline strategy:

     App shell (HTML / CSS / JS / icons / Chart.js)
        -> cache-first, refreshed in the background (stale-while-revalidate).
           The shell rarely changes and must open instantly with no network.

     Environment APIs (Open-Meteo)
        -> network-first with a short cache fallback. Fresh air-quality data
           matters; a stale reading is better than none.

     Everything else
        -> network-first, falling back to the cache, then to the shell for
           navigation requests.

   The user's data lives in localStorage, not in the cache, so the entire
   application remains fully functional offline.
   ========================================================================== */

const VERSION = "v1.0.0";
const SHELL_CACHE = `autocare-shell-${VERSION}`;
const RUNTIME_CACHE = `autocare-runtime-${VERSION}`;

const SHELL_ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./vendor/chart.umd.js",

  "./css/variables.css",
  "./css/reset.css",
  "./css/animations.css",
  "./css/layout.css",
  "./css/components.css",
  "./css/style.css",
  "./css/dashboard.css",
  "./css/vehicles.css",
  "./css/maintenance.css",
  "./css/wash-advisor.css",
  "./css/analytics.css",
  "./css/expenses.css",
  "./css/settings.css",
  "./css/responsive.css",

  "./js/utils.js",
  "./js/constants.js",
  "./js/icons.js",
  "./js/storage.js",
  "./js/seed.js",
  "./js/validation.js",
  "./js/maintenance.js",
  "./js/health.js",
  "./js/environment.js",
  "./js/journeys.js",
  "./js/washAdvisor.js",
  "./js/expenses.js",
  "./js/vehicles.js",
  "./js/analytics.js",
  "./js/notifications.js",
  "./js/ui.js",
  "./js/charts.js",
  "./js/forms.js",
  "./js/router.js",
  "./js/pages/dashboard.js",
  "./js/pages/vehicles.js",
  "./js/pages/maintenance.js",
  "./js/pages/wash.js",
  "./js/pages/analytics.js",
  "./js/pages/expenses.js",
  "./js/pages/settings.js",
  "./js/app.js",

  "./assets/icons/favicon-32.png",
  "./assets/icons/apple-touch-icon.png",
  "./assets/icons/icon-192.png",
  "./assets/icons/icon-512.png",
  "./assets/icons/maskable-512.png",
];

const ENV_HOSTS = ["air-quality-api.open-meteo.com", "api.open-meteo.com"];

/* ------------------------------------------------------------- install -- */

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      // addAll rejects the whole batch if any single request fails, so add
      // individually and tolerate misses (e.g. an icon size not generated).
      .then((cache) =>
        Promise.all(
          SHELL_ASSETS.map((url) =>
            cache.add(new Request(url, { cache: "reload" })).catch((err) => {
              console.warn("[AutoCare SW] Skipped precache:", url, err.message);
            })
          )
        )
      )
      .then(() => self.skipWaiting())
  );
});

/* ------------------------------------------------------------ activate -- */

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== SHELL_CACHE && k !== RUNTIME_CACHE)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

/* --------------------------------------------------------------- fetch -- */

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Environment APIs — always try the network first.
  if (ENV_HOSTS.includes(url.hostname)) {
    event.respondWith(networkFirst(request, RUNTIME_CACHE));
    return;
  }

  // Same-origin shell assets — cache first, revalidate in the background.
  if (url.origin === self.location.origin) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Cross-origin (web fonts) — cache first, network fallback.
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).catch(() => cached))
  );
});

/* ----------------------------------------------------------- strategies -- */

async function staleWhileRevalidate(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request, { ignoreSearch: true });

  const network = fetch(request)
    .then((response) => {
      if (response && response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);

  if (cached) return cached;

  const fresh = await network;
  if (fresh) return fresh;

  // Offline navigation with nothing cached for that exact URL: serve the shell.
  if (request.mode === "navigate") {
    const shell = await cache.match("./index.html");
    if (shell) return shell;
  }

  return new Response("Offline and this resource is not cached.", {
    status: 503,
    statusText: "Offline",
    headers: { "Content-Type": "text/plain" },
  });
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: "offline" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}

/* Allow the page to trigger an immediate update. */
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});
