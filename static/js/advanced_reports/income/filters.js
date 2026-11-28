"use strict";

// ── Income Analytics — sticky filter bar ──

function _incomeYearSelect(id, value, years) {
  const opts = years
    .map((y) => `<option value="${y}" ${y === value ? "selected" : ""}>${y}</option>`)
    .join("");
  return `<select id="${id}" class="income-select">${opts}</select>`;
}

function _incomeMonthSelect(id, value) {
  const opts = Array.from({ length: 12 }, (_, i) => {
    const m = i + 1;
    return `<option value="${m}" ${m === value ? "selected" : ""}>${_incomeMonthName(m)}</option>`;
  }).join("");
  return `<select id="${id}" class="income-select">${opts}</select>`;
}

function _incomeRenderPeriodBox() {
  const S = window._incomeState;
  const D = window._incomeData;
  const years = D.years_available || [];
  let h = "";
  if (S.mode === "off") {
    h = `<div class="income-fgroup"><span class="income-flabel" data-i18n="income_year">Year</span>${_incomeYearSelect("incomeFYear", S.year, years)}</div>`;
  } else if (S.mode === "yoy") {
    h =
      `<div class="income-fgroup"><span class="income-flabel income-pa" data-i18n="income_period_a">Period A</span>${_incomeYearSelect("incomeFYa", S.ya, years)}</div>` +
      '<span class="income-vs">VS</span>' +
      `<div class="income-fgroup"><span class="income-flabel income-pb" data-i18n="income_period_b">Period B</span>${_incomeYearSelect("incomeFYb", S.yb, years)}</div>`;
  } else {
    h =
      `<div class="income-fgroup"><span class="income-flabel income-pa" data-i18n="income_period_a">Period A</span>` +
      `<div class="income-pair">${_incomeMonthSelect("incomeFMa", S.ma)}${_incomeYearSelect("incomeFMya", S.mya, years)}</div></div>` +
      '<span class="income-vs">VS</span>' +
      `<div class="income-fgroup"><span class="income-flabel income-pb" data-i18n="income_period_b">Period B</span>` +
      `<div class="income-pair">${_incomeMonthSelect("incomeFMb", S.mb)}${_incomeYearSelect("incomeFMyb", S.myb, years)}</div></div>`;
  }
  return h;
}

function _incomeRenderFilters() {
  const S = window._incomeState;
  const D = window._incomeData;
  const box = document.getElementById("incomeFilters");
  if (!box) return;

  const monthChips =
    `<button class="income-chip income-month-chip ${S.months.length ? "" : "on"}" data-m="0" data-i18n="income_all">All</button>` +
    Array.from({ length: 12 }, (_, i) => {
      const m = i + 1;
      return `<button class="income-chip income-month-chip ${S.months.includes(m) ? "on" : ""}" data-m="${m}">${_incomeMonthName(m, "short")}</button>`;
    }).join("");

  const srcChips = (D.sources || [])
    .map((s) => {
      const on = S.sources.includes(s.id);
      const n = S.mode === "mom" ? s.count_a + s.count_b : s.count_a;
      return (
        `<button class="income-chip ${on ? "on" : ""} ${n ? "" : "empty"}" data-s="${s.id}">` +
        `<span class="income-dot" style="background:${s.color}"></span>${_incomeSourceLabel(s.id)}` +
        `<span class="income-cnt">${n}</span></button>`
      );
    })
    .join("");

  box.innerHTML =
    '<div class="income-frow">' +
    '<div class="income-fgroup"><span class="income-flabel" data-i18n="income_compare">Compare</span>' +
    '<div class="income-seg" id="incomeModeSeg">' +
    `<button data-v="off" class="${S.mode === "off" ? "on" : ""}" data-i18n="income_off">Off</button>` +
    `<button data-v="yoy" class="${S.mode === "yoy" ? "on" : ""}" data-i18n="income_yoy">Year vs Year</button>` +
    `<button data-v="mom" class="${S.mode === "mom" ? "on" : ""}" data-i18n="income_mom">Month vs Month</button>` +
    "</div></div>" +
    `<div class="income-frow" id="incomePeriodBox" style="gap:10px">${_incomeRenderPeriodBox()}</div>` +
    '<div class="income-spacer"></div>' +
    '<div class="income-fgroup"><span class="income-flabel" data-i18n="income_basis">Salary basis</span>' +
    '<div class="income-seg" id="incomeBasisSeg">' +
    `<button data-v="net" class="${S.basis === "net" ? "on" : ""}" data-i18n="income_net">Net (paid)</button>` +
    `<button data-v="gross" class="${S.basis === "gross" ? "on" : ""}" data-i18n="income_gross">Gross</button>` +
    "</div></div>" +
    '<div class="income-fgroup"><span class="income-flabel">&nbsp;</span><div class="income-btnrow">' +
    '<button class="income-btn" id="incomeBtnReset">↺ <span data-i18n="income_reset">Reset</span></button>' +
    '<button class="income-btn" id="incomeBtnXlsx">📊 <span data-i18n="income_export_xlsx">Excel</span></button>' +
    '<button class="income-btn income-btn-primary" id="incomeBtnPdf">📄 <span data-i18n="income_export_pdf">PDF</span></button>' +
    "</div></div>" +
    "</div>" +
    `<div class="income-frow" id="incomeMonthRow" style="${S.mode === "mom" ? "display:none" : ""}">` +
    '<div class="income-fgroup" style="flex:1"><span class="income-flabel" data-i18n="income_months">Months</span><div class="income-chips" id="incomeMonthChips">' +
    monthChips +
    "</div></div></div>" +
    '<div class="income-frow">' +
    '<div class="income-fgroup" style="flex:1"><span class="income-flabel" data-i18n="income_sources">Income sources</span><div class="income-chips" id="incomeSrcChips">' +
    srcChips +
    "</div></div></div>" +
    `<div class="income-gross-note" id="incomeGrossNote" style="${S.basis === "gross" ? "" : "display:none"}" data-i18n="income_gross_note">No gross amounts are recorded for some salary months — the net (paid) amount is used for those.</div>`;

  _incomeBindFilters();
}

function _incomeBindFilters() {
  const S = window._incomeState;
  document.querySelectorAll("#incomeModeSeg button").forEach((b) => {
    b.onclick = () => {
      S.mode = b.dataset.v;
      _incomeRefresh();
    };
  });
  document.querySelectorAll("#incomeBasisSeg button").forEach((b) => {
    b.onclick = () => {
      S.basis = b.dataset.v;
      _incomeRefresh();
    };
  });
  const bind = (id, fn) => {
    const el = document.getElementById(id);
    if (el) el.onchange = () => {
      fn(el);
      _incomeRefresh();
    };
  };
  bind("incomeFYear", (el) => (S.year = parseInt(el.value, 10)));
  bind("incomeFYa", (el) => (S.ya = parseInt(el.value, 10)));
  bind("incomeFYb", (el) => (S.yb = parseInt(el.value, 10)));
  bind("incomeFMa", (el) => (S.ma = parseInt(el.value, 10)));
  bind("incomeFMya", (el) => (S.mya = parseInt(el.value, 10)));
  bind("incomeFMb", (el) => (S.mb = parseInt(el.value, 10)));
  bind("incomeFMyb", (el) => (S.myb = parseInt(el.value, 10)));
  document.querySelectorAll("#incomeMonthChips .income-chip").forEach((b) => {
    b.onclick = () => {
      const m = parseInt(b.dataset.m, 10);
      if (!m) S.months = [];
      else if (S.months.includes(m)) S.months = S.months.filter((x) => x !== m);
      else S.months = [...S.months, m].sort((a, b2) => a - b2);
      if (S.months.length === 12) S.months = [];
      _incomeRefresh();
    };
  });
  document.querySelectorAll("#incomeSrcChips .income-chip").forEach((b) => {
    b.onclick = () => {
      const s = b.dataset.s;
      if (S.sources.includes(s)) S.sources = S.sources.filter((x) => x !== s);
      else S.sources = [...S.sources, s];
      _incomeRefresh();
    };
  });
  document.getElementById("incomeBtnReset").onclick = () => {
    window._incomeState = _incomeDefaults(window._incomeData);
    _incomeRefresh();
  };
  document.getElementById("incomeBtnXlsx").onclick = () => _incomeDownload("xlsx");
  document.getElementById("incomeBtnPdf").onclick = () => _incomeDownload("pdf");
}
