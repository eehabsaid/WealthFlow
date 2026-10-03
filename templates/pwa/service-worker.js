/* WealthFlow service worker (version {{ cache_version }}).
 * Caches only public static assets and the offline page. Financial data
 * (the JSON API) and authenticated pages are NEVER cached: they always go to the
 * network, so nothing private can be served to another user on a shared device. */
"use strict";

const VERSION = "{{ cache_version }}";
const STATIC_CACHE = "wealthflow-static-" + VERSION;
const OFFLINE_URL = "{{ offline_url }}";
const PRECACHE_URLS = {{ precache_json|safe }};

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names
          .filter((name) => name.startsWith("wealthflow-") && name !== STATIC_CACHE)
          .map((name) => caches.delete(name))
      ))
      .then(() => self.clients.claim())
  );
});

async function staleWhileRevalidate(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((response) => {
      if (response && response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);
  return cached || network;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
