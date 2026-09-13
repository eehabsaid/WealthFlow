"use strict";
// i18n: applyTranslations DOM binder
// This file is part of the i18n module. Do not edit directly.

function applyTranslations(container = document) {
  if (!_t) return;
  const root = container || document;

  const formatTemplateValue = (name, value) => {
    const num = Number(value);
    if (!Number.isFinite(num)) return String(value ?? "");
    if (/(days|count|month|year|week)/i.test(name)) return fmtInt(num);
    if (/(ratio|trend|signal|gap|coverage|pct)/i.test(name)) return fmt(num);
    return fmtpresent(num);
  };

  const parseI18nParams = (raw) => {
    if (!raw) return {};
    const candidates = [raw];
    try {
      const decoded = decodeURIComponent(raw);
      if (decoded !== raw) candidates.push(decoded);
    } catch (_) {
      // Keep raw as the only candidate.
    }

    for (const candidate of candidates) {
      try {
        const parsed = JSON.parse(candidate);
        if (parsed && typeof parsed === "object") return parsed;
      } catch (_) {
        // Try next candidate.
      }
    }
    return {};
  };

  const applyTemplateParams = (text, params) => {
    let out = String(text ?? "");
    Object.entries(params || {}).forEach(([name, value]) => {
      const replacement = formatTemplateValue(name, value);
      out = out.split(`{${name}}`).join(replacement);
    });
    return out;
  };

  // 1. Static text — [data-i18n]
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");

    // Ignore missing or empty translations
    if (!_t[key]) return;

    // Do not overwrite with empty values
    if (_t[key].trim() === "") return;

    el.textContent = _t[key];
  });

  // 2. Dynamic keys with template placeholders — [data-i18n-key]
  root.querySelectorAll("[data-i18n-key]").forEach((el) => {
    const key = el.getAttribute("data-i18n-key");
    if (!key || !_t[key]) return;

    let text = _t[key];

    const templateParams = {
      ...parseI18nParams(el.getAttribute("data-i18n-params")),
    };

    const goldAmt = el.getAttribute("data-gold-amount");
    const cashAmt = el.getAttribute("data-cash-amount");
    const certAmt = el.getAttribute("data-certificate-amount");
    const daysLeft = el.getAttribute("data-days-left");

    if (goldAmt !== null) templateParams.gold_amount = goldAmt;
    if (cashAmt !== null) templateParams.cash_amount = cashAmt;
    if (certAmt !== null) templateParams.certificate_amount = certAmt;
    if (daysLeft !== null) templateParams.days_left = daysLeft;

    text = applyTemplateParams(text, templateParams);

    el.textContent = text;
  });

  // 2.5 Dynamic keys with template placeholders (HTML allowed) — [data-i18n-html-key]
  root.querySelectorAll("[data-i18n-html-key]").forEach((el) => {
    const key = el.getAttribute("data-i18n-html-key");
    if (!key || !_t[key]) return;

    let text = _t[key];
    const templateParams = {
      ...parseI18nParams(el.getAttribute("data-i18n-params")),
    };

    text = applyTemplateParams(text, templateParams);
    el.innerHTML = text;
  });

  // 3. Prefix-based keys — [data-i18n-prefix] + [data-i18n-value]
  root.querySelectorAll("[data-i18n-prefix]").forEach((el) => {
    const prefix = el.getAttribute("data-i18n-prefix");
    const raw = el.getAttribute("data-i18n-value");
    if (!raw) {
      el.textContent = "—";
      return;
    }
    const combined = `${prefix}${raw}`;
    el.textContent =
      _t[combined] || raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  });

  // 4. Attribute translators — placeholder and title
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (_t[key]) el.setAttribute("placeholder", _t[key]);
  });

  root.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (_t[key]) el.setAttribute("title", _t[key]);
  });

  // 5. Date formatting — .local-date-field
  root.querySelectorAll(".local-date-field").forEach((td) => {
    const raw =
      td.getAttribute("data-expiry") ||
      td.getAttribute("data-date") ||
      td.getAttribute("data-value");
    if (!raw) return;
    td.textContent = formatDate(raw);
  });

  // 6. Number formatter classes
  root.querySelectorAll(".num-fmt").forEach((el) => {
    const v = el.getAttribute("data-value");
    if (v !== null) el.innerText = fmt(v);
  });
  root.querySelectorAll(".num-fmtpresent").forEach((el) => {
    const v = el.getAttribute("data-value");
    if (v !== null) el.innerText = fmtpresent(v);
  });
  root.querySelectorAll(".num-fmtint").forEach((el) => {
    const v = el.getAttribute("data-value");
    if (v !== null) el.innerText = fmtInt(v);
  });
  root.querySelectorAll(".num-fmtRate").forEach((el) => {
    const v = el.getAttribute("data-value");
    if (v !== null) el.innerText = fmtRate(v);
  });

  // Auto-apply collapsible behaviour to any new tables rendered since last call
  if (typeof initCollapsibleTables === "function") initCollapsibleTables();
}
