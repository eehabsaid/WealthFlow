"use strict";
// Node tests: Cash Flow chart/status panel and Expenses payment pills (script-global JS in a vm sandbox).
// Run: node --test tests/js/*.test.js
process.env.TZ = "America/New_York";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const JS = path.join(__dirname, "..", "..", "static", "js");

function load(file, extra = {}) {
  const sandbox = { Date, Number, String, Intl, Math, console, ...extra };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(JS, file), "utf8"), sandbox, { filename: file });
  return sandbox;
}

test("cash flow chart month labels do not shift a month west of UTC", () => {
  let config = null;
  const canvas = {};
  const sb = load("financial_advisor/cash_flow_forecast/cash_flow_chart.js", {
    window: {
      Chart: function Chart(_c, cfg) {
        config = cfg;
      },
    },
    Chart: function Chart(_c, cfg) {
      config = cfg;
    },
    document: { getElementById: () => canvas, documentElement: { lang: "en" } },
    currentLang: () => "en",
    t: (k) => k,
    _money: (v) => String(v),
    _themeColor: (_n, fb) => fb,
    _destroyChart: () => {},
  });
  sb._renderCashFlowChart(
    [
      { month: "2026-12", ending_cash: 10 },
      { month: "2027-01", ending_cash: 20 },
    ],
    5
  );
  assert.deepStrictEqual(Array.from(config.data.labels), ["Dec", "Jan"]);
});

test("cash flow status 'see summary' link never changes the hash route", () => {
  const sb = load("financial_advisor/cash_flow_forecast/cash_flow_status.js");
  const html = sb._buildCashFlowStatusPanelHtml({
    warnings: [{ key: "cash_flow_warning_healthy" }],
    summary: { largest_cash_event: { amount: 5 } },
  });
  const link = html.match(/<a [^>]*cash_flow_summary_section[^>]*>/)[0];
  assert.ok(link.includes("event.preventDefault()"));
  assert.ok(link.includes("scrollIntoView"));
});

test("expense payment pill label is translated, falls back to the raw value", () => {
  const sb = load("expenses/table.js", {
    t: (k, fb) => (k === "payment_cash" ? "نقداً" : fb),
    fmt: (v) => String(v),
    formatDate: (v) => String(v),
    baseCurrencyCode: () => "EGP",
  });
  const row = (pm) => ({
    id: 1,
    date: "2026-11-01",
    category_color: "#fff",
    category_icon: "",
    category_name: "c",
    subcategory_name: "",
    description: "d",
    payment_method: pm,
    amount: 1,
    amount_base: 1,
    currency_code: "EGP",
    is_readonly: false,
  });
  const cash = sb.renderExpenseTableHTML([row("Cash")]);
  assert.ok(cash.includes("exp-method-cash"));
  assert.ok(cash.includes("نقداً"));
  assert.ok(sb.renderExpenseTableHTML([row("Wire")]).includes("Wire"));
});

test("expense table escapes user-entered text", () => {
  const sb = load("expenses/table.js", {
    t: (_k, fb) => fb,
    fmt: (v) => String(v),
    formatDate: (v) => String(v),
  });
  const html = sb.renderExpenseTableHTML([
    {
      id: 1,
      date: "2026-11-01",
      category_color: '#fff"><img src=x>',
      category_icon: "",
      category_name: "<script>alert(1)</script>",
      subcategory_name: "<b>s</b>",
      description: '<img src=x onerror="alert(1)">',
      payment_method: "Cash",
      amount: 1,
      amount_base: 1,
      currency_code: "EGP",
      is_readonly: false,
    },
  ]);
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes("<img src=x"));
  assert.ok(!html.includes("<b>s</b>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("shared wfEsc / _escapeRegExp helpers", () => {
  const sb = load("app/formatting.js", {
    document: {},
    window: {},
    localStorage: { getItem: () => null },
  });
  assert.strictEqual(sb.wfEsc(`<a href="x">'&`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;");
  assert.strictEqual(sb.wfEsc(null), "");
  assert.ok(new RegExp(sb._escapeRegExp("Bank (Egypt) A+B [x")).test("Bank (Egypt) A+B [x"));
});
