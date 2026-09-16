"use strict";
// Password visibility toggle, form-submit loading state, and caps-lock
// warning helpers for auth pages.
// Part of the authentication module (split from the former monolithic
// shared.js, 200-line rule). Do not edit directly.

window.WFAuth = window.WFAuth || {};

(function () {
  function togglePassword(inputId, iconId) {
    const inp = document.getElementById(inputId || "passwordInput");
    const icon = document.getElementById(iconId || "eyeIcon");
    if (!inp || !icon) return;
    if (inp.type === "password") {
      inp.type = "text";
      icon.className = "bi bi-eye-slash";
    } else {
      inp.type = "password";
      icon.className = "bi bi-eye";
    }
  }

  function initFormSubmitLoading() {
    document.querySelectorAll("form").forEach((form) => {
      form.addEventListener("submit", function () {
        const btn = form.querySelector('button[type="submit"]');
        if (btn && !btn.disabled) {
          btn.disabled = true;
          const originalText = btn.innerHTML;
          btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${originalText}`;
        }
      });
    });
  }

  function setupCapsLockListener(inputId, warningId) {
    const input = document.getElementById(inputId);
    const warning = document.getElementById(warningId);
    if (!input || !warning) return;

    function checkCaps(e) {
      if (e.getModifierState && e.getModifierState("CapsLock")) {
        warning.classList.remove("d-none");
      } else {
        warning.classList.add("d-none");
      }
    }

    input.addEventListener("keydown", checkCaps);
    input.addEventListener("keyup", checkCaps);
    input.addEventListener("blur", () => warning.classList.add("d-none"));
  }

  Object.assign(window.WFAuth, {
    togglePassword,
    initFormSubmitLoading,
    setupCapsLockListener,
  });
})();
