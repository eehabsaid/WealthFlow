"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings: page composition. Tab bar + one card per group (only the active one is visible, see nav.js)
// + the sysadmin limits panel as its own section + the sticky Save bar. The groups themselves are built by
// render_settings_form.js / settings_groups.js / settings_groups_limits.js.

window.AIA.buildAISettingsFormHtml = function (ctx) {
  const ui = window.AIA.ui;
  const s = window.AIA.state.currentAISettings;
  const providerLabel =
    (window.AIA.state.currentProviderSchemas.find((p) => p.key === ctx.activeProviderKey) || {})
      .key || "";
  const bodies = {
    provider: window.AIA.buildProviderHtml(ctx),
    safety: window.AIA.buildSafetyHtml(s),
    domains: window.AIA.buildDomainsHtml(s),
    routing: window.AIA.buildRoutingHtml(s),
    agent: window.AIA.buildAgentLimitsHtml(s),
    docs: window.AIA.buildDocumentsHtml(s),
    files: window.AIA.buildFilesHtml(s),
    speech: window.AIA.buildSpeechSettingsHtml(s),
    image: window.AIA.buildImageSettingsHtml(s),
    diag: window.AIA.buildDiagnosticsHtml(s),
  };
  const cards = ui.GROUPS.map(([id, icon, key, title, desc]) =>
    ui.card({
      id,
      icon,
      titleKey: key,
      title,
      descKey: `${key}_desc`,
      desc,
      body: bodies[id],
      badge:
        id === "provider"
          ? [providerLabel, window.AIA.getProviderModelValue(ctx.activeProviderKey)]
              .filter(Boolean)
              .join(" · ")
          : "",
    })
  ).join("");
  const limits = `<section class="aia-pane" id="aiaGroup-limits" data-aia-group="limits" role="tabpanel"><div id="aiUserLimitsPanel"></div></section>`;
  return `
    <p class="aia-intro" data-i18n="ai_settings_desc">${t("ai_settings_desc", "Configure AI provider integration, API endpoints, model selection, and security parameters.")}</p>
    <div class="aia-layout">
      ${ui.chips()}
      <div class="aia-detail" id="aiaDetail">
        <div class="aia-groups">${cards}${limits}</div>
        <div class="aia-savebar">
          <button type="button" class="btn btn-primary-custom d-flex align-items-center" id="aiSaveBtn" onclick="window.AIA.saveAISettingsFromGui()">
            <i class="bi bi-check-lg me-1"></i> <span data-i18n="ai_save_settings">${t("ai_save_settings", "Save Settings")}</span>
          </button>
        </div>
      </div>
    </div>`;
};
