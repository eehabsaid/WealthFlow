"use strict";
// Markup of the "Monthly AI token limit per user" frame (logic: user_limits.js / user_limits_actions.js).

window.AIA = window.AIA || {};

window.AIA.buildUserLimitsCardHtml = function (defaultLimit) {
  const lbl = (key, fb, id) =>
    `<label class="form-label fw-semibold" for="${id}" data-i18n="${key}">${t(key, fb)}</label>`;
  return `<div class="si-modern-card p-4 mb-4" id="aiUserLimitsCard">
    <h5 class="fw-bold mb-1" style="color:var(--text-primary);"><i class="bi bi-speedometer2 text-primary me-2"></i>
      <span data-i18n="ai_limits_title">${t("ai_limits_title", "Monthly AI token limit per user")}</span></h5>
    <div class="form-text mb-3" data-i18n="ai_limits_hint">${t("ai_limits_hint", "Applies only to users on the general app settings. Blank = use the default; 0 = unlimited.")}</div>
    <div class="mb-4">
      ${lbl("ai_limits_default", "Default limit (tokens / month)", "aiDefaultLimitInput")}
      <div class="d-flex gap-2 align-items-center flex-wrap">
        <input type="number" min="0" id="aiDefaultLimitInput" class="form-control" style="max-width:240px" value="${escapeHtml(defaultLimit)}">
        ${aiSaveBtnHtml('id="aiDefaultLimitSave"', "ai_save_settings", "Save Settings")}
      </div>
    </div>
    <div class="row g-3 mb-3">
      <div class="col-md-5">${lbl("ai_limits_search_label", "Search user", "aiLimitsSearch")}
        <input type="search" id="aiLimitsSearch" class="form-control" placeholder="${t("ai_limits_search_ph", "Username or email…")}"></div>
      <div class="col-md-3">${lbl("ai_limits_filter_label", "AI settings", "aiLimitsModeFilter")}
        <select id="aiLimitsModeFilter" class="form-select">
          <option value="all">${t("ai_limits_filter_all", "All")}</option>
          <option value="general">${t("ai_limits_mode_general", "General")}</option>
          <option value="own">${t("ai_limits_mode_own", "Own settings (unlimited)")}</option></select></div>
    </div>
    <div class="d-flex flex-wrap gap-2 align-items-center mb-3">
      <button type="button" class="btn btn-outline-secondary d-flex align-items-center" id="aiLimitsToggleAll">
        <i class="bi bi-check2-square me-1"></i> <span data-i18n="ai_limits_toggle_all">${t("ai_limits_toggle_all", "Toggle Select All")}</span></button>
      <input type="number" min="0" id="aiLimitsBulkValue" class="form-control" style="max-width:200px" placeholder="${t("ai_limits_inherit", "default")}"
        aria-label="${t("ai_limits_bulk_label", "Limit for selected users")}">
      ${aiSaveBtnHtml('id="aiLimitsBulkApply" disabled', "ai_limits_apply_selected", "Apply to selected")}
      <small class="text-muted" id="aiLimitsSelectedCount"></small>
    </div>
    <div id="aiLimitsTableHost"></div></div>`;
};
