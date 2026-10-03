// Registers the PWA service worker (served from the site root so its scope covers the app).
"use strict";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(() => {
      // Registration is best-effort: the app works normally without a service worker.
    });
  });
}
