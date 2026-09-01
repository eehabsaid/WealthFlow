"use strict";

// Backward compatibility shim forwarding to WFAuth in static/js/authentication/shared.js
if (typeof window.WFAuth === "undefined") {
  const script = document.createElement("script");
  script.src = "/static/js/authentication/shared.js";
  document.head.appendChild(script);
}

function togglePassword(inputId, iconId) {
  if (window.WFAuth && typeof window.WFAuth.togglePassword === "function") {
    window.WFAuth.togglePassword(inputId, iconId);
  } else {
    const inp = document.getElementById(inputId || "passwordInput");
    const icon = document.getElementById(iconId || "eyeIcon");
    if (inp && icon) {
      if (inp.type === "password") {
        inp.type = "text";
        icon.className = "bi bi-eye-slash";
      } else {
        inp.type = "password";
        icon.className = "bi bi-eye";
      }
    }
  }
}
