"use strict";

// ── Income Analytics tab (Advanced Reports) — entry, state, shared helpers ──

const INCOME_SOURCE_IDS = ["salary", "bonus", "perdiem", "cert", "bank", "rent", "manual", "sale"];

function _incomeLocale() {
  const lang = localStorage.getItem("lang") || "en";
  return { en: "en-GB", ar: "ar-EG-u-nu-latn", fr: "fr-FR", de: "de-DE" }[lang] || "en-GB";
}

function _incomeIsAr() {
  return (localStorage.getItem("lang") || "en") === "ar";
}

function _incomeFmt(v) {
  return Number(v || 0).toLocaleString(_incomeLocale(), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function _incomeFmt0(v) {
  return Number(v || 0).toLocaleString(_incomeLocale(), {
    notation: "compact",
    maximumFractionDigits: 1,
  });
}

function _incomeMonthName(m, style) {
  return new Intl.DateTimeFormat(_incomeLocale(), { month: style || "long" }).format(
    new Date(2024, m - 1, 1)
  );
}

function _incomeSourceColor(id) {
  const el = document.querySelector(".income-page");
  if (el) {
    const v = getComputedStyle(el).getPropertyValue("--inc-" + id).trim();
    if (v) return v;
  }
  const s = (window._incomeData && window._incomeData.sources || []).find((x) => x.id === id);
  return (s && s.color) || "#1a6ef5";
}

function _incomeT(key) {
  return t(key, key);
}

function _incomeSourceLabel(id) {
  return t("income_src_" + id, id);
}

function _incomeItemLabel(src, key) {
  if (key.startsWith("m") && key[1] >= "0" && key[1] <= "9" && src !== "cert") {
    const m = parseInt(key.slice(1), 10);
    if (m >= 1 && m <= 12) return _incomeMonthName(m);
  }
  if (src === "cert") return t("income_cert_no", "Certificate") + " " + key;
  return key;
}

function _incomeDefaults(d) {
  const p = d.periods || [];
  const s = {
    mode: d.mode || "off",
    basis: d.basis || "net",
    months: [],
    sources: INCOME_SOURCE_IDS.slice(),
    year: p[0] ? p[0].year : new Date().getFullYear() - 1,
    ya: p[0] ? p[0].year : new Date().getFullYear() - 1,
    yb: p[1] ? p[1].year : new Date().getFullYear(),
    ma: p[0] && p[0].month ? p[0].month : new Date().getMonth() + 1,
    mya: p[0] ? p[0].year : new Date().getFullYear(),
    mb: p[1] && p[1].month ? p[1].month : new Date().getMonth() + 1,
    myb: p[1] ? p[1].year : new Date().getFullYear(),
  };
  return s;
}

function _incomeParams() {
  const S = window._incomeState;
  const p = new URLSearchParams();
  p.set("mode", S.mode);
  p.set("basis", S.basis);
  if (S.mode === "off") p.set("year", S.year);
  if (S.mode === "yoy") {
    p.set("ya", S.ya);
    p.set("yb", S.yb);
  }
  if (S.mode === "mom") {
    p.set("ma", S.ma);
    p.set("mya", S.mya);
    p.set("mb", S.mb);
    p.set("myb", S.myb);
  }
  if (S.mode !== "mom" && S.months.length) p.set("months", S.months.join(","));
  if (S.sources.length !== INCOME_SOURCE_IDS.length) p.set("sources", S.sources.join(","));
  return p;
}

async function _incomeFetch() {
  const res = await fetch("/api/reports/income/?" + _incomeParams().toString());
  if (!res.ok) throw new Error("income api " + res.status);
  window._incomeData = await res.json();
}

async function renderIncomeReport() {
  const mc = document.getElementById("main-content");
  mc.innerHTML =
    '<div style="display:flex;justify-content:center;padding:60px"><div class="spinner-border" style="color:var(--accent-primary)"></div></div>';
  let first;
  try {
    const res = await fetch("/api/reports/income/");
    first = await res.json();
  } catch (e) {
    mc.innerHTML =
      '<div class="card" style="padding:40px;text-align:center;color:var(--text-muted)"><div style="font-size:36px">🗂️</div><div style="font-weight:700;margin-top:8px" data-i18n="income_no_data">No income recorded for this selection</div></div>';
    applyTranslations();
    return;
  }
  window._incomeData = first;
  window._incomeState = _incomeDefaults(first);
  mc.innerHTML =
    '<div class="income-page">' +
    '<div class="income-filters" id="incomeFilters"></div>' +
    '<div id="incomeContent"></div>' +
    "</div>" +
    '<div class="income-drawer-bg" id="incomeDrawerBg"></div>' +
    '<aside class="income-drawer" id="incomeDrawer" aria-hidden="true">' +
    "<header><span id=\"incomeDrawerTitle\"></span><button class=\"income-btn\" id=\"incomeDrawerClose\" data-i18n=\"income_close\">Close</button></header>" +
    '<div class="income-drawer-body" id="incomeDrawerBody"></div>' +
    "</aside>";
  _incomeBindShell();
  _incomeRenderFilters();
  _incomeRenderContent();
  applyTranslations();
}

async function _incomeRefresh() {
  const content = document.getElementById("incomeContent");
  if (content) content.style.opacity = "0.5";
  try {
    await _incomeFetch();
  } catch (e) {
    if (content) content.style.opacity = "1";
    return;
  }
  _incomeRenderFilters();
  _incomeRenderContent();
  applyTranslations();
  if (content) content.style.opacity = "1";
}
