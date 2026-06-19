// i18n.js — language engine
let _t = {};
let _lang = localStorage.getItem("lang") || "en";

async function loadLanguage(code) {
  try {
    const res = await fetch(`/static/i18n/${code}.json?v=${Date.now()}`);
    if (!res.ok) throw new Error("Not found");

    _t = await res.json();
    _lang = code;
    localStorage.setItem("lang", code);

    // --- BULLETPROOF RTL LOGIC ---
    // Extract value, normalize to string, compare to true-like values
    const rtlVal = String(_t.__rtl || "").toLowerCase();
    const isRTL = (rtlVal === "true" || rtlVal === "1");
    document.documentElement.setAttribute("dir", isRTL ? "rtl" : "ltr");
    document.documentElement.lang = code;
    // ----------------------------

    applyTranslations();

    await fetch("/api/settings/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "active_language", value: code }),
    });
  } catch (e) {
    console.warn("Language load failed:", e);
  }
  applyTranslations();
}

function applyTranslations() {
    // 1. Translate standard text content
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (_t && _t[key]) {
            element.textContent = _t[key];
        }
    });

    // 2. Translate placeholders with a safety check
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        if (_t && _t[key]) {
            element.setAttribute('placeholder', _t[key]);
        } else {
            console.warn(`Missing translation key: ${key}`);
        }
    });

// 3. Translate titles with a safety check
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        // Use _t (your active translation object) to avoid undefined errors
        if (_t && _t[key]) {
            el.setAttribute('title', _t[key]);
        } else {
            console.warn(`Missing translation key for title: ${key}`);
        }
    });
}

// Correct version for simple JS strings only
function t(key, fallback) {
  const lang = localStorage.getItem('lang') || 'en';
  // Assuming your _t object is structured as _t[lang][key]
  return (_t[lang] && _t[lang][key]) ? _t[lang][key] : (fallback || key);
}

function currentLang() {
  return _lang;
  applyTranslations();
}
