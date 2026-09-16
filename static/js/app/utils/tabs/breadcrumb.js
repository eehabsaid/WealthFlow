"use strict";
// Breadcrumb setter and legacy translation alias.
// Part of the app/utils module (split from the former monolithic tabs.js,
// 200-line rule). Do not edit directly.

function setBreadcrumb(title) {
  const bc = document.getElementById("breadcrumb");
  if (bc) bc.textContent = title;
}

// Legacy translation alias used by some modules

function translate(key) {
  const lang = localStorage.getItem("lang") || "en";
  return window.translations?.[lang]?.[key] || key;
}
