"use strict";
// Theme apply/toggle for auth pages.
// Part of the authentication module (split from the former monolithic
// shared.js, 200-line rule). Do not edit directly.

window.WFAuth = window.WFAuth || {};

(function () {
  function applyTheme(theme) {
    const targetTheme = theme || localStorage.getItem("theme") || "dark";
    const html = document.documentElement;
    const body = document.body;

    if (targetTheme === "light") {
      html.setAttribute("data-theme", "light");
      html.setAttribute("data-bs-theme", "light");
      if (body) {
        body.setAttribute("data-theme", "light");
        body.setAttribute("data-bs-theme", "light");
      }
    } else {
      html.setAttribute("data-theme", "dark");
      html.setAttribute("data-bs-theme", "dark");
      if (body) {
        body.setAttribute("data-theme", "dark");
        body.setAttribute("data-bs-theme", "dark");
      }
    }
    localStorage.setItem("theme", targetTheme);

    const btns = document.querySelectorAll("#theme-toggle, #themeToggleBtn");
    btns.forEach((btn) => {
      btn.textContent = targetTheme === "light" ? "☀️" : "🌙";
    });
  }

  function toggleTheme() {
    const current = localStorage.getItem("theme") === "light" ? "dark" : "light";
    applyTheme(current);
  }

  function initThemeToggle() {
    applyTheme();
  }

  window.toggleTheme = toggleTheme;

  Object.assign(window.WFAuth, {
    applyTheme,
    toggleTheme,
    initThemeToggle,
  });
})();
