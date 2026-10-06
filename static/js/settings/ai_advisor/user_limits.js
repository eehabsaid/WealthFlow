"use strict";
// AI Advisor (sysadmin): default monthly token limit + per-user override, search, bulk apply.
// Limits apply only to users on the general AI settings; users on their own settings are unlimited.
// Rows use the app's shared table + "Show all / Show less" toggle (app/utils/collapsible.js, as in Expenses).

window.AIA = window.AIA || {};
window.AIA.limits = { users: [], selected: new Set(), q: "", mode: "all" };

const AI_SAVE_BTN_CLASS = "btn btn-primary-custom d-flex align-items-center";

function aiSaveBtnHtml(extraAttrs, labelKey, fallback, extraClass = "") {
  return `<button type="button" class="${extraClass} ${AI_SAVE_BTN_CLASS}" ${extraAttrs}>
    <i class="bi bi-check-lg me-1"></i> <span data-i18n="${labelKey}">${t(labelKey, fallback)}</span></button>`;
}

function aiLimitsRowHtml(u) {
  const mode = u.use_general
    ? t("ai_limits_mode_general", "General")
    : t("ai_limits_mode_own", "Own settings (unlimited)");
  const effective = !u.use_general
    ? "—"
    : u.effective_limit
      ? u.effective_limit.toLocaleString()
      : t("myai_no_limit", "no limit");
  const off = u.use_general ? "" : "disabled";
  const checked = window.AIA.limits.selected.has(u.id) ? "checked" : "";
  return `<tr data-user-id="${u.id}">
    <td><input type="checkbox" class="form-check-input ai-limit-select" ${off} ${checked}></td>
    <td>${escapeHtml(u.username)}</td><td>${mode}</td>
    <td>${Number(u.used).toLocaleString()}</td><td>${effective}</td>
    <td><input type="number" min="0" class="form-control ai-limit-input" style="min-width:150px"
      value="${escapeHtml(u.limit_override)}" placeholder="${t("ai_limits_inherit", "default")}" ${off}></td>
    <td>${aiSaveBtnHtml(off, "ai_save_settings", "Save Settings", "ai-limit-save")}</td></tr>`;
}

function aiLimitsFiltered() {
  const { users, q, mode } = window.AIA.limits;
  const needle = q.trim().toLowerCase();
  return users.filter(
    (u) =>
      (mode === "all" || (mode === "general") === u.use_general) &&
      (!needle || `${u.username} ${u.email || ""}`.toLowerCase().includes(needle))
  );
}

window.AIA.renderUserLimitsTable = function () {
  const host = document.getElementById("aiLimitsTableHost");
  if (!host) return;
  const rows = aiLimitsFiltered();
  const th = (key, fb) => `<th data-i18n="${key}">${t(key, fb)}</th>`;
  const body = rows.length
    ? rows.map(aiLimitsRowHtml).join("")
    : `<tr><td colspan="7" class="text-muted text-center py-3" data-i18n="ai_limits_no_users">${t("ai_limits_no_users", "No users match your search.")}</td></tr>`;
  host.innerHTML = `<div class="table-container"><table class="data-table"><thead><tr><th></th>
    ${th("ai_limits_th_user", "User")}${th("ai_limits_th_mode", "AI settings")}${th("ai_limits_th_used", "Used this month")}
    ${th("ai_limits_th_limit", "Effective limit")}${th("ai_limits_th_override", "Override")}<th></th></tr></thead>
    <tbody id="aiLimitsBody">${body}</tbody></table></div>`;
  if (typeof initCollapsibleTables === "function") initCollapsibleTables();
  window.AIA.updateLimitsSelection();
};

window.AIA.updateLimitsSelection = function () {
  const n = window.AIA.limits.selected.size;
  const label = document.getElementById("aiLimitsSelectedCount");
  if (label)
    label.textContent = t("ai_limits_selected_count", "{count} selected").replace("{count}", n);
  const apply = document.getElementById("aiLimitsBulkApply");
  if (apply) apply.disabled = n === 0;
};

window.AIA.loadUserLimitsPanel = async function () {
  const box = document.getElementById("aiUserLimitsPanel");
  if (!box) return;
  const users = [];
  let defaultLimit = "0";
  for (let page = 1, pages = 1; page <= pages; page++) {
    const res = await fetch(`/api/settings/ai/user-limits/?page=${page}&page_size=200`);
    if (!res.ok) return;
    const d = await res.json();
    users.push(...d.users);
    defaultLimit = d.default_limit;
    pages = d.num_pages;
  }
  const L = window.AIA.limits;
  L.users = users;
  L.selected = new Set(
    [...L.selected].filter((id) => users.some((u) => u.id === id && u.use_general))
  );
  if (!document.getElementById("aiUserLimitsCard")) {
    box.innerHTML = window.AIA.buildUserLimitsCardHtml(defaultLimit);
    window.AIA.bindUserLimitsEvents();
  } else {
    document.getElementById("aiDefaultLimitInput").value = defaultLimit;
  }
  window.AIA.renderUserLimitsTable();
  if (typeof applyTranslations === "function") applyTranslations();
};
