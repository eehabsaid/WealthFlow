"use strict";
// Privacy / Terms pages: edited legal text is rendered by the server in the
// visitor's language and carries no data-i18n keys, so the shared language
// switcher cannot swap it. Reload once the language cookie has changed so the
// server renders the chosen language (built-in text swaps without a reload).
document.addEventListener("DOMContentLoaded", () => {
  const main = document.getElementById("legalMain");
  const select = document.getElementById("authLanguageSelect");
  if (!main || !select || main.dataset.legalOverridden !== "true") return;
  const rendered = document.documentElement.lang || "en";
  select.addEventListener("change", () => {
    setTimeout(() => {
      if ((localStorage.getItem("lang") || rendered) !== rendered) window.location.reload();
    }, 400);
  });
});
