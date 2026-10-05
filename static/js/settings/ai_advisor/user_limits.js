"use strict";
// AI Advisor (sysadmin): default monthly token limit + per-user override.
// Limits apply only to users on the general AI settings; users on their own settings are unlimited.

window.AIA = window.AIA || {};

async function aiLimitsPost(payload) {
  const res = await fetch("/api/settings/ai/user-limits/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showToast(t(data.error_key || "settings_save_failed", data.error || "Save failed"), "error");
    return false;
  }
  showToast(t("settings_saved", "Settings saved ✓"));
  return true;
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
  return `<tr data-user-id="${u.id}">
    <td>${escapeHtml(u.username)}</td><td>${mode}</td>
    <td>${Number(u.used).toLocaleString()}</td><td>${effective}</td>
    <td><input type="number" min="0" class="form-control form-control-sm ai-limit-input" value="${escapeHtml(u.limit_override)}"
      placeholder="${t("ai_limits_inherit", "default")}" ${u.use_general ? "" : "disabled"}></td>
    <td><button type="button" class="btn btn-sm btn-outline-primary ai-limit-save" ${u.use_general ? "" : "disabled"}>${t("ai_save_settings", "Save Settings")}</button></td></tr>`;
}

window.AIA.loadUserLimitsPanel = async function () {
  const box = document.getElementById("aiUserLimitsPanel");
  if (!box) return;
  const res = await fetch("/api/settings/ai/user-limits/");
  if (!res.ok) return;
  const d = await res.json();
  box.innerHTML = `<div class="card p-3">
    <h6 class="fw-semibold" data-i18n="ai_limits_title">${t("ai_limits_title", "Monthly AI token limit per user")}</h6>
    <div class="form-text mb-2" data-i18n="ai_limits_hint">${t("ai_limits_hint", "Applies only to users on the general app settings. Blank = use the default; 0 = unlimited.")}</div>
    <div class="input-group input-group-sm mb-3" style="max-width:360px">
      <span class="input-group-text" data-i18n="ai_limits_default">${t("ai_limits_default", "Default limit (tokens / month)")}</span>
      <input type="number" min="0" id="aiDefaultLimitInput" class="form-control" value="${escapeHtml(d.default_limit)}">
      <button type="button" class="btn btn-outline-primary" id="aiDefaultLimitSave">${t("ai_save_settings", "Save Settings")}</button>
    </div>
    <div class="table-responsive"><table class="table table-sm align-middle">
      <thead><tr><th>${t("ai_limits_th_user", "User")}</th><th>${t("ai_limits_th_mode", "AI settings")}</th>
        <th>${t("ai_limits_th_used", "Used this month")}</th><th>${t("ai_limits_th_limit", "Effective limit")}</th>
        <th>${t("ai_limits_th_override", "Override")}</th><th></th></tr></thead>
      <tbody id="aiLimitsBody">${d.users.map(aiLimitsRowHtml).join("")}</tbody></table></div></div>`;
  document.getElementById("aiDefaultLimitSave").onclick = async () => {
    if (await aiLimitsPost({ default_limit: document.getElementById("aiDefaultLimitInput").value }))
      window.AIA.loadUserLimitsPanel();
  };
  document.querySelectorAll("#aiLimitsBody .ai-limit-save").forEach((btn) => {
    btn.onclick = async () => {
      const row = btn.closest("tr");
      const ok = await aiLimitsPost({
        user_id: Number(row.dataset.userId),
        limit: row.querySelector(".ai-limit-input").value,
      });
      if (ok) window.AIA.loadUserLimitsPanel();
    };
  });
};
