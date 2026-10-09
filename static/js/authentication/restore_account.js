"use strict";

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    const prefilled = document.getElementById("restoreUsernameInput")?.value;
    document.getElementById(prefilled ? "restorePasswordInput" : "restoreUsernameInput")?.focus();
  }, 100);
});
