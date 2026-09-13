"use strict";
// i18n: language loading
// This file is part of the i18n module. Do not edit directly.

async function loadLanguage(code) {
  try {
    // Added cache buster to force the browser to download the newly injected translations
    const res = await fetch(`/static/i18n/${code}.json?v=${Date.now()}`);
    if (!res.ok) throw new Error("Not found");

    _t = await res.json();
    _lang = code;
    localStorage.setItem("lang", code);

    // RTL detection — read from available_languages setting, fallback to _t.__rtl
    let isRTL = false;
    try {
      const sRes = await fetch(`/api/settings/?v=${Date.now()}`);
      if (sRes.ok) {
        const sData = await sRes.json();
        const langs = JSON.parse(sData.settings?.available_languages || "[]");
        const found = langs.find((l) => l.code === code);
        if (found !== undefined && found.rtl !== undefined) {
          isRTL = found.rtl === true || found.rtl === "true" || found.rtl === 1;
        } else {
          const rtlVal = String(_t.__rtl || "").toLowerCase();
          isRTL = rtlVal === "true" || rtlVal === "1";
        }
      } else {
        const rtlVal = String(_t.__rtl || "").toLowerCase();
        isRTL = rtlVal === "true" || rtlVal === "1";
      }
    } catch (e) {
      const rtlVal = String(_t.__rtl || "").toLowerCase();
      isRTL = rtlVal === "true" || rtlVal === "1";
    }

    document.documentElement.setAttribute("dir", isRTL ? "rtl" : "ltr");
    document.documentElement.lang = code;

    applyTranslations();

    // Persist active language to server
    await fetch("/api/settings/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "active_language", value: code }),
    });

    // Re-render active route so runtime-computed labels update immediately.
    if (window.__wfRouterReady && typeof window.route === "function") {
      window.route();
    }

    document.dispatchEvent(new CustomEvent("languageChanged", { detail: { code } }));
  } catch (e) {
    // Silently ignore language load failures; UI falls back to existing translations.
  }
  applyTranslations();
}
