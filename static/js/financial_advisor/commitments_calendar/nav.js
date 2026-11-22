"use strict";
// commitments_calendar/nav.js — date helpers, localized names and the
// month/week navigation rules shared by every view.

// The backend sends date-only "YYYY-MM-DD" values. Keys must always be built
// from LOCAL calendar components, never from Date.toISOString() (UTC), which
// shifts the day in any non-UTC timezone and puts events one cell ahead.
function _commitmentsLocalISO(d) {
  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}

function _commitmentsLocalMonth(d) {
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
}

function _commitmentsDateFromISO(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

// Displayed dates always go through the central formatter (dd-mmm-yyyy).
function _commitmentsShowDate(value) {
  return formatDate(value);
}

// Weekday and month NAMES (not date values) come from Intl in the active language.
function _commitmentsName(date, options) {
  return date.toLocaleDateString(currentLang() || "en", options);
}

function _commitmentsMonthYear(date) {
  return _commitmentsName(date, { month: "long", year: "numeric" });
}

function _commitmentsWeekday(date) {
  return _commitmentsName(date, { weekday: "short" });
}

function _commitmentsMondayOf(d) {
  const monday = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  return monday;
}

// The loaded window: first day of the current month through 12 months (API max is 366 days).
function _commitmentsRange() {
  const now = new Date();
  return {
    start: new Date(now.getFullYear(), now.getMonth(), 1),
    end: new Date(now.getFullYear(), now.getMonth() + 12, 0),
  };
}

function _commitmentsPeriod(anchor) {
  if (_commitmentsView === "week") {
    const start = _commitmentsMondayOf(anchor);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return { start, end };
  }
  return {
    start: new Date(anchor.getFullYear(), anchor.getMonth(), 1),
    end: new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0),
  };
}

function _commitmentsShifted(delta) {
  if (_commitmentsView === "week") {
    const moved = new Date(_commitmentsAnchor);
    moved.setDate(moved.getDate() + 7 * delta);
    return moved;
  }
  return new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth() + delta, 1);
}

// Navigation stays inside the loaded window so a grid is never silently empty.
function _commitmentsCanShift(delta) {
  const range = _commitmentsRange();
  const period = _commitmentsPeriod(_commitmentsShifted(delta));
  return period.end >= range.start && period.start <= range.end;
}
