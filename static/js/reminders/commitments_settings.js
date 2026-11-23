"use strict";
// reminders/commitments_settings.js — Settings > Reminders cards for the Commitments Calendar
// (concentration window and first day of the week). Split from index.js (200-line rule).
// Values are validated on the server (INTEGER_SETTING_RANGES); invalid input shows an error toast.

// Weekday options 0 (Sunday) ... 6 (Saturday), named in the active language; 2026-11-22 is a Sunday.
function _commitmentsWeekdayOptions(selected) {
  const current =
    Number.isInteger(Number(selected)) && selected !== undefined && selected !== ""
      ? Number(selected)
      : 0;
  return Array.from({ length: 7 }, (_, day) => {
    const name = new Date(2026, 10, 22 + day).toLocaleDateString(currentLang() || "en", {
      weekday: "long",
    });
    return `<option value="${day}" ${day === current ? "selected" : ""}>${name}</option>`;
  }).join("");
}

function _commitmentsSettingsCards(s, saveText) {
  return `
        <!-- Commitments calendar concentration window -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="commitments_window_title">${t("commitments_window_title", "Commitments Calendar — Concentration Window")}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="commitments_window_desc">${t("commitments_window_desc", "Number of days used to detect periods with concentrated financial obligations on the Commitments Calendar.")}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                <input type="number" id="commitmentsWindowDays" class="form-control" style="width:90px" aria-label="${t("commitments_window_label", "Concentration window (days)")}"
                    value="${s.commitments_concentration_window_days || 30}" min="1" max="90">
                <button class="btn-secondary-custom" onclick="saveAppSetting('commitments_concentration_window_days', document.getElementById('commitmentsWindowDays').value)" data-i18n="save">${saveText}</button>
            </div>
        </div>

        <!-- Commitments calendar first day of the week -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="commitments_week_start_title">${t("commitments_week_start_title", "Commitments Calendar — First Day of the Week")}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="commitments_week_start_desc">${t("commitments_week_start_desc", "The day the Month and Week views of the Commitments Calendar start on.")}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                <select id="commitmentsWeekStart" class="form-select" style="width:auto" aria-label="${t("commitments_week_start_title", "First Day of the Week")}">${_commitmentsWeekdayOptions(s.commitments_week_start_day)}</select>
                <button class="btn-secondary-custom" onclick="saveAppSetting('commitments_week_start_day', document.getElementById('commitmentsWeekStart').value)" data-i18n="save">${saveText}</button>
            </div>
        </div>
  `;
}
