// Offline fallback page: translate the static text from the cached language file.
"use strict";

(async function translateOfflinePage() {
  const lang = localStorage.getItem("lang") || "en";
  try {
    const response = await fetch(`/static/i18n/${lang}.json`);
    if (!response.ok) return;
    const messages = await response.json();
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const text = messages[el.dataset.i18n];
      if (text) el.textContent = text;
    });
  } catch (_err) {
    // Offline and language file not cached: the English defaults stay.
  }
})();

document.getElementById("pwa-offline-retry")?.addEventListener("click", () => {
  window.location.href = "/";
});
