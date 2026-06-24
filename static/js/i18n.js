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
    const isRTL = rtlVal === "true" || rtlVal === "1";
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
  if (!_t) return; // Guard clause if translations dictionary isn't ready
  const currentLang = document.documentElement.lang || "en";

  // 1. Static Text Framework
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (_t[key]) el.textContent = _t[key];
  });

  // 2. Dynamic Key Framework (Covers Recommendations, Actions, Dynamic Badges)
  document.querySelectorAll("[data-i18n-key]").forEach((el) => {

    const key = el.getAttribute("data-i18n-key");

    if (!key || !_t[key]) return;

    let text = _t[key];

    const goldAmount = el.getAttribute("data-gold-amount");
    const cashAmount = el.getAttribute("data-cash-amount");
    const certificateAmount = el.getAttribute("data-certificate-amount");

    if (goldAmount !== null) {
        text = text.replace(
            "{gold_amount}",
            fmtpresent(goldAmount)
        );
    }

    if (cashAmount !== null) {
        text = text.replace(
            "{cash_amount}",
            fmtpresent(cashAmount)
        );
    }

    if (certificateAmount !== null) {
        text = text.replace(
            "{certificate_amount}",
            fmtpresent(certificateAmount)
        );
    }

    el.textContent = text;
  });

  // 3. Dynamic Prefix Framework (Covers Table Metadata: type_cash, freq_monthly, etc.)
  document.querySelectorAll("[data-i18n-prefix]").forEach((el) => {
    const prefix = el.getAttribute("data-i18n-prefix");
    const rawVal = el.getAttribute("data-i18n-value");
    if (!rawVal) { el.textContent = "—"; return; }

    const combinedKey = `${prefix}${rawVal}`;
    if (_t[combinedKey]) {
      el.textContent = _t[combinedKey];
    } else {
      // Fallback: strip underscores and capitalize nicely
      el.textContent = rawVal.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }
  });

  // 4. Attribute / Safety Translators
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (_t[key]) el.setAttribute("placeholder", _t[key]);
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (_t[key]) el.setAttribute("title", _t[key]);
  });

  // 5. Dynamic Date Parsing Loop
  document.querySelectorAll(".local-date-field").forEach((td) => {
    const rawDate = td.getAttribute("data-expiry");
    if (!rawDate) return;
    const dateObj = new Date(rawDate);
    td.textContent = `${dateObj.toLocaleDateString(currentLang, { day: "2-digit" })}-${dateObj.toLocaleDateString(currentLang, { month: "short" })}-${dateObj.toLocaleDateString(currentLang, { year: "numeric" })}`;
  });

  // 6. Global App Currency/Number Refreshers
  document.querySelectorAll('.num-fmt').forEach(el => { const v = el.getAttribute('data-value'); if (v !== null) el.innerText = fmt(v); });
  document.querySelectorAll('.num-fmtpresent').forEach(el => { const v = el.getAttribute('data-value'); if (v !== null) el.innerText = fmtpresent(v); });
  document.querySelectorAll('.num-fmtint').forEach(el => { const v = el.getAttribute('data-value'); if (v !== null) el.innerText = fmtInt(v); });
}

// Correct version for simple JS strings only
function t(key, fallback) {
  // 1. Safety check: if global translations don't exist yet, return fallback immediately
  if (typeof _t === 'undefined' || !_t) {
    return fallback || key;
  }

  const lang = localStorage.getItem("lang") || "en";

  // 2. Case A: Standard dictionary structure (_t[lang][key])
  if (_t[lang] && _t[lang][key]) {
    return _t[lang][key];
  }

  // 3. Case B: Flat dictionary structure or global fallback (_t[key])
  if (_t[key]) {
    return _t[key];
  }

  // 4. Case C: No translation found anywhere, return the provided fallback or the key itself
  return fallback !== undefined ? fallback : key;
}

function currentLang() {
  return _lang;
  applyTranslations();
}
