"use strict";

window.WFAuth = (function () {
  const LANG_STORAGE_KEY = "lang";

  function getCookie(name) {
    const cookieStr = document.cookie || "";
    const parts = cookieStr.split(";");
    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i].trim();
      if (part.startsWith(`${name}=`)) {
        return decodeURIComponent(part.substring(name.length + 1));
      }
    }
    return "";
  }

  function syncCsrfInputs() {
    const token = getCookie("csrftoken");
    if (!token) {
      return;
    }
    document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach((input) => {
      input.value = token;
    });
  }

  async function loadLanguage(code) {
    const res = await fetch(`/static/i18n/${code}.json?v=${Date.now()}`);
    if (!res.ok) {
      return;
    }

    const translations = await res.json();
    localStorage.setItem(LANG_STORAGE_KEY, code);
    document.cookie = `wf_lang=${code}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = code;
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
          const rtlVal = String(translations.__rtl || "").toLowerCase();
          isRTL = rtlVal === "true" || rtlVal === "1";
        }
      } else {
        const rtlVal = String(translations.__rtl || "").toLowerCase();
        isRTL = rtlVal === "true" || rtlVal === "1";
      }
    } catch (e) {
      const rtlVal = String(translations.__rtl || "").toLowerCase();
      isRTL = rtlVal === "true" || rtlVal === "1";
    }
    document.documentElement.dir = isRTL ? "rtl" : "ltr";

    document.querySelectorAll(".lang-hidden-input").forEach((input) => {
      input.value = code;
    });

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (key && translations[key]) {
        el.textContent = translations[key];
      }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key && translations[key]) {
        el.setAttribute("placeholder", translations[key]);
      }
    });

    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.getAttribute("data-i18n-title");
      if (key && translations[key]) {
        el.setAttribute("title", translations[key]);
      }
    });

    if (document.title && document.querySelector("title[data-i18n]")) {
      const key = document.querySelector("title[data-i18n]").getAttribute("data-i18n");
      if (key && translations[key]) {
        document.title = translations[key];
      }
    }

    const select = document.getElementById("authLanguageSelect");
    if (select) {
      select.value = code;
    }
  }

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

  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("authLanguageSelect");
    const current = localStorage.getItem(LANG_STORAGE_KEY) || document.documentElement.lang || "en";
    syncCsrfInputs();
    initThemeToggle();

    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
      form.addEventListener("submit", () => {
        syncCsrfInputs();
      });
    });

    if (select) {
      select.value = current;
      select.addEventListener("change", (event) => {
        loadLanguage(event.target.value);
      });
    }
    loadLanguage(current);
    initFormSubmitLoading();
  });

  window.toggleTheme = toggleTheme;

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

  return {
    getCookie,
    syncCsrfInputs,
    loadLanguage,
    togglePassword,
    toggleTheme,
    applyTheme,
    setupCapsLockListener,
  };
})();
