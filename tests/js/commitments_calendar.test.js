"use strict";
// Node tests for the Commitments Calendar date/navigation helpers (nav.js, script-global JS
// loaded into a vm sandbox like a browser page). Run: node --test tests/js/*.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const FILE = path.join(
  __dirname,
  "..",
  "..",
  "static",
  "js",
  "financial_advisor",
  "commitments_calendar",
  "nav.js"
);

function load(state = {}) {
  const sandbox = {
    Date,
    Number,
    String,
    formatDate: (v) => `fmt:${v}`,
    currentLang: () => "en",
    _commitmentsData: { settings: { week_start_day: 0 } },
    _commitmentsView: "month",
    _commitmentsAnchor: new Date(2026, 10, 22),
    ...state,
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(FILE, "utf8"), sandbox, { filename: "nav.js" });
  return sandbox;
}

const iso = (c, d) => c._commitmentsLocalISO(d);

test("local ISO keeps the calendar day (no UTC shift)", () => {
  const c = load();
  assert.strictEqual(iso(c, new Date(2026, 11, 2, 0, 30)), "2026-12-02");
  assert.strictEqual(iso(c, c._commitmentsDateFromISO("2026-03-31")), "2026-03-31");
  assert.strictEqual(c._commitmentsLocalMonth(new Date(2026, 0, 9)), "2026-01");
});

test("week starts on Sunday by default and on the configured day", () => {
  let c = load();
  assert.strictEqual(iso(c, c._commitmentsWeekStartOf(new Date(2026, 10, 25))), "2026-11-22"); // Wed -> Sun
  c = load({ _commitmentsData: { settings: { week_start_day: 1 } } });
  assert.strictEqual(iso(c, c._commitmentsWeekStartOf(new Date(2026, 10, 22))), "2026-11-16"); // Sun -> Mon
  assert.strictEqual(iso(c, c._commitmentsWeekStartOf(new Date(2026, 10, 23))), "2026-11-23");
  c = load({ _commitmentsData: { settings: { week_start_day: 6 } } });
  assert.strictEqual(iso(c, c._commitmentsWeekStartOf(new Date(2026, 10, 27))), "2026-11-21"); // Fri -> Sat
});

test("a missing or invalid week_start_day falls back to Sunday", () => {
  for (const data of [null, {}, { settings: {} }, { settings: { week_start_day: "x" } }]) {
    assert.strictEqual(load({ _commitmentsData: data })._commitmentsWeekStartDay(), 0);
  }
});

test("week period spans exactly 7 days; month period spans the whole month", () => {
  let c = load({ _commitmentsView: "week", _commitmentsAnchor: new Date(2026, 11, 30) });
  let p = c._commitmentsPeriod(c._commitmentsAnchor);
  assert.strictEqual(iso(c, p.start), "2026-12-27");
  assert.strictEqual(iso(c, p.end), "2027-01-02"); // crosses the year boundary
  c = load({ _commitmentsView: "month" });
  p = c._commitmentsPeriod(new Date(2026, 1, 10));
  assert.strictEqual(iso(c, p.start), "2026-02-01");
  assert.strictEqual(iso(c, p.end), "2026-02-28");
});

test("shifting moves by week in week view and by month in month view", () => {
  let c = load({ _commitmentsView: "week", _commitmentsAnchor: new Date(2026, 11, 28) });
  assert.strictEqual(iso(c, c._commitmentsShifted(1)), "2027-01-04");
  assert.strictEqual(iso(c, c._commitmentsShifted(-1)), "2026-12-21");
  c = load({ _commitmentsView: "month", _commitmentsAnchor: new Date(2026, 11, 15) });
  assert.strictEqual(iso(c, c._commitmentsShifted(1)), "2027-01-01");
  assert.strictEqual(iso(c, c._commitmentsShifted(-1)), "2026-11-01");
});

test("loaded range starts this month and is 12 months (within the 366-day API maximum)", () => {
  const c = load();
  const r = c._commitmentsRange();
  const days = Math.round((r.end - r.start) / 86400000) + 1;
  assert.ok(days >= 365 && days <= 366, `${days} days`);
  assert.strictEqual(r.start.getDate(), 1);
  const now = new Date();
  assert.strictEqual(r.start.getMonth(), now.getMonth());
});

test("navigation stays inside the loaded range", () => {
  const now = new Date();
  const thisMonth = new Date(now.getFullYear(), now.getMonth(), 15);
  let c = load({ _commitmentsView: "month", _commitmentsAnchor: thisMonth });
  assert.strictEqual(c._commitmentsCanShift(-1), false);
  assert.strictEqual(c._commitmentsCanShift(1), true);
  const last = new Date(now.getFullYear(), now.getMonth() + 11, 15);
  c = load({ _commitmentsView: "month", _commitmentsAnchor: last });
  assert.strictEqual(c._commitmentsCanShift(1), false);
  assert.strictEqual(c._commitmentsCanShift(-1), true);
});

test("displayed dates go through the central formatter", () => {
  assert.strictEqual(load()._commitmentsShowDate("2026-11-22"), "fmt:2026-11-22");
});
