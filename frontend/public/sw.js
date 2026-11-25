/* Ledger-x service worker.
 *
 * Scope: installability + an offline fallback page. It deliberately does NOT
 * cache HTML of app routes, RSC payloads or any API response, so no
 * authenticated data is ever stored in Cache Storage.
 *
 * Bump CACHE_VERSION to invalidate every cache on the next deploy.
 */

const CACHE_VERSION = "v1";
const STATIC_CACHE = `ledgerx-static-${CACHE_VERSION}`;
const SHELL_CACHE = `ledgerx-shell-${CACHE_VERSION}`;
const OFFLINE_URL = "/offline";
const PRECACHE_ASSETS = [
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/manifest.webmanifest",
];
const MAX_STATIC_ENTRIES = 200;

self.addEventListener("install", (event) => {
  event.waitUntil(precache());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([STATIC_CACHE, SHELL_CACHE]);
      const names = await caches.keys();
      await Promise.all(
        names
          .filter((name) => name.startsWith("ledgerx-") && !keep.has(name))
          .map((name) => caches.delete(name)),
      );
      await self.clients.claim();
    })(),
  );
});

// A new worker waits until the user accepts the update prompt in the UI.
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only same-origin GETs are handled. The API lives on another origin and
  // chat streaming is a POST, so both go straight to the network.
  if (request.method !== "GET") return;
  if (request.headers.has("range")) return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/_next/static/")) {
    // Content-hashed filenames: safe to serve from cache forever.
    event.respondWith(cacheFirst(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  if (PRECACHE_ASSETS.includes(url.pathname)) {
    event.respondWith(staleWhileRevalidate(request));
  }
  // Anything else (RSC fetches, images, ...) is not intercepted.
});

async function precache() {
  const shell = await caches.open(SHELL_CACHE);
  const response = await fetch(OFFLINE_URL, { cache: "reload" });
  if (!response.ok) throw new Error(`Offline page unavailable: ${response.status}`);

  // The offline page is hydrated by JS; cache the chunks it references so it
  // renders even when the very first visit happens right before going offline.
  const html = await response.clone().text();
  await shell.put(OFFLINE_URL, response);

  const assets = new Set(html.match(/\/_next\/static\/[^"'\s\\)]+\.(?:js|css)/g) || []);
  const statics = await caches.open(STATIC_CACHE);
  await Promise.all([
    ...[...assets].map((asset) => statics.add(asset).catch(() => undefined)),
    ...PRECACHE_ASSETS.map((asset) => shell.add(asset).catch(() => undefined)),
  ]);
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok) {
    await cache.put(request, response.clone());
    await trim(cache, MAX_STATIC_ENTRIES);
  }
  return response;
}

async function networkFirstNavigation(request) {
  try {
    return await fetch(request);
  } catch {
    const shell = await caches.open(SHELL_CACHE);
    return (await shell.match(OFFLINE_URL)) || Response.error();
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => undefined);
  return cached || (await network) || Response.error();
}

// Cache.keys() returns entries in insertion order, so the oldest go first.
async function trim(cache, maxEntries) {
  const keys = await cache.keys();
  const excess = keys.length - maxEntries;
  for (let i = 0; i < excess; i += 1) {
    await cache.delete(keys[i]);
  }
}
