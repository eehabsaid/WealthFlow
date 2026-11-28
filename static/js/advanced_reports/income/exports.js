"use strict";

// ── Income Analytics — Excel / PDF downloads (current filters + current language) ──

function _incomeExportUrl(format) {
  const p = _incomeParams();
  p.set("format", format);
  p.set("lang", localStorage.getItem("lang") || "en");
  return "/api/reports/income/export/?" + p.toString();
}

function _incomeDownload(format) {
  window.location.href = _incomeExportUrl(format);
}
