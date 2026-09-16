"use strict";
// DOMContentLoaded bootstrap for auth pages: CSRF sync, theme init, language
// select wiring, form submit loading. Loaded last of the shared/ siblings
// since it calls into window.WFAuth.* set up by csrf_lang.js, theme.js, and
// ui_helpers.js.
// Part of the authentication module (split from the former monolithic
// shared.js, 200-line rule). Do not edit directly.

document.addEventListener("DOMContentLoaded", () => {
  const LANG_STORAGE_KEY = "lang";
  const select = document.getElementById("authLanguageSelect");
  const current = localStorage.getItem(LANG_STORAGE_KEY) || document.documentElement.lang || "en";
  window.WFAuth.syncCsrfInputs();
  window.WFAuth.initThemeToggle();

  document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
    form.addEventListener("submit", () => {
      window.WFAuth.syncCsrfInputs();
    });
  });

  if (select) {
    select.value = current;
    select.addEventListener("change", (event) => {
      window.WFAuth.loadLanguage(event.target.value);
    });
  }
  window.WFAuth.loadLanguage(current);
  window.WFAuth.initFormSubmitLoading();
});
