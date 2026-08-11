/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Localization & Date Utilities
   ───────────────────────────────────────────────────────────────
   Provides translation helpers, date formatting, and RTL detection
   used throughout the date-picker modules.

   Dependencies : i18n.js (t()), utils/dateFormatter.js (formatDate())
   Exposes      : window._WF_DP.loc
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  /** @returns {string} translation string via i18n.js t() if available */
  function _t(key, fallback) {
    return typeof t === "function" ? t(key, fallback) : fallback;
  }

  /** @param {string} iso  YYYY-MM-DD or empty string
   *  @returns {string}  "dd-mmm-yyyy" using existing formatDate(), or "" */
  function _displayDate(iso) {
    if (!iso) return "";
    if (typeof formatDate === "function") return formatDate(iso);
    // Minimal fallback – should never be needed since dateFormatter.js loads first.
    const [y, m, d] = iso.split("-");
    if (!y || !m || !d) return iso;
    const abbr = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return `${d}-${abbr[parseInt(m, 10) - 1] || m}-${y}`;
  }

  /** @param {Date} d @returns {string} YYYY-MM-DD */
  function _isoFromDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${dd}`;
  }

  /** Today's date at midnight local. @returns {Date} */
  function _today() {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }

  /** @returns {boolean} true when the page is RTL */
  function _isRtl() {
    return (
      document.documentElement.dir === "rtl" ||
      document.body.dir === "rtl" ||
      document.documentElement.lang === "ar" ||
      (typeof currentLang === "function" && currentLang() === "ar")
    );
  }

  window._WF_DP.loc = {
    _t,
    _displayDate,
    _isoFromDate,
    _today,
    _isRtl,
  };
})();
