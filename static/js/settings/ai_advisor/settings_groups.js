"use strict";
// AI Advisor settings: the body of every group except "Provider and model" (see render_settings_form.js).
// Every control keeps its original id, data-i18n key and value, so saving and the other scripts are unaffected.

window.AIA = window.AIA || {};

const aiaEsc = (text) =>
  String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const aiaModeOptions = (modes, current, prefix) =>
  modes
    .map(
      (m) =>
        `<option value="${m}" ${m === current ? "selected" : ""} data-i18n="${prefix}_${m}">${t(`${prefix}_${m}`, m)}</option>`
    )
    .join("");

window.AIA.buildSafetyHtml = function (s) {
  const ui = window.AIA.ui;
  const tier = s.ai_permission_tier || "read";
  const tierOption = (value, key, fallback) =>
    `<option value="${value}" ${tier === value ? "selected" : ""}>${t(key, fallback)}</option>`;
  const mode = window.AIA.VALIDATE_MODES.includes(s.ai_validate_mode) ? s.ai_validate_mode : "flag";
  return (
    ui.selectRow({
      id: "aiPermissionTierSelect",
      labelKey: "ai_permission_tier_label",
      label: "AI Tool Permissions",
      helpKey: "ai_permission_tier_help",
      help: "Read only, read + execute, or read + execute + modify.",
      options:
        tierOption("read", "ai_permission_tier_read", "Read Only") +
        tierOption("execute", "ai_permission_tier_execute", "Read + Execute") +
        tierOption("modify", "ai_permission_tier_modify", "Read + Execute + Modify"),
    }) +
    ui.toggleRow({
      id: "aiCodeAccessToggle",
      checked: s.ai_code_access !== false,
      labelKey: "ai_code_access_label",
      label: "Let the AI read the source code (admin only)",
      helpKey: "ai_code_access_help",
      help: "Read-only; secrets and databases are never exposed. Customers never get code access",
    }) +
    ui.selectRow({
      id: "aiValidateModeSelect",
      labelKey: "ai_validate_mode_label",
      label: "Answer Validation",
      helpKey: "ai_validate_mode_hint",
      help: "Checks figures in the answer against your data",
      options: aiaModeOptions(window.AIA.VALIDATE_MODES, mode, "ai_validate_mode"),
    })
  );
};

window.AIA.buildRoutingHtml = function (s) {
  const ui = window.AIA.ui;
  const inv = window.AIA.INVESTIGATOR_MODES.includes(s.ai_investigator_mode)
    ? s.ai_investigator_mode
    : "auto";
  return (
    ui.toggleRow({
      id: "aiDirectAnswersToggle",
      checked: s.ai_direct_answers !== false,
      labelKey: "ai_direct_answers_label",
      label: "Instant Data Answers",
      helpKey: "ai_direct_answers_help",
      help: "Answer simple data questions instantly from your data without the AI model",
    }) +
    ui.toggleRow({
      id: "aiMultiAgentToggle",
      checked: !!s.ai_multi_agent_enabled,
      labelKey: "ai_multi_agent_label",
      label: "Multi-Agent Orchestration",
      helpKey: "ai_multi_agent_help",
      help: "Lets several specialised agents work on one question.",
    }) +
    ui.selectRow({
      id: "aiInvestigatorModeSelect",
      labelKey: "ai_investigator_mode_label",
      label: "AI Investigator",
      helpKey: "ai_investigator_mode_hint",
      help: "Lets the AI explore the whole app with read-only tools when a normal answer is not enough",
      options: aiaModeOptions(window.AIA.INVESTIGATOR_MODES, inv, "ai_investigator_mode"),
    }) +
    ui.toggleRow({
      id: "aiAgentEnabledToggle",
      checked: s.ai_agent_enabled !== false,
      labelKey: "ai_agent_enabled_label",
      label: "Agent mode",
      helpKey: "ai_agent_enabled_help",
      help: "Lets users switch the chat to Agent: the AI investigates the app and your data with read-only tools and answers from what it read. Source-code tools stay admin-only.",
    }) +
    window.AIA.buildInstructionsBox(s, {
      id: "aiAgentInstructionsInput",
      resetId: "aiAgentInstructionsResetBtn",
      rows: 8,
      onReset: "resetAgentInstructions",
      text: s.ai_agent_instructions || s.ai_agent_instructions_default || "",
      labelKey: "ai_agent_instructions_label",
      label: "Agent investigation instructions",
      helpKey: "ai_agent_instructions_help",
      help: "How the agent should investigate (like Continue's rules). Applies to every user's Agent chats.",
    })
  );
};

window.AIA.buildInstructionsBox = function (s, o) {
  return `
    <div class="aia-row aia-row-wide">
      <div class="aia-row-text">
        <label class="aia-label" for="${o.id}" data-i18n="${o.labelKey}">${t(o.labelKey, o.label)}</label>
        <div class="aia-help" data-i18n="${o.helpKey}">${t(o.helpKey, o.help)}</div>
      </div>
      <div class="aia-row-control aia-stack">
        <textarea class="form-control" id="${o.id}" rows="${o.rows}" maxlength="6000">${aiaEsc(o.text)}</textarea>
        <button type="button" class="btn btn-sm btn-outline-secondary" id="${o.resetId}" onclick="window.AIA.${o.onReset}()" data-i18n="ai_agent_instructions_reset">${t("ai_agent_instructions_reset", "Restore default")}</button>
      </div>
    </div>`;
};

// Chat domains: two checkboxes. One of them always stays checked (the server refuses none, too).
window.AIA.keepOneDomain = function (box) {
  const other = document.getElementById(
    box.id === "aiDomainBusinessToggle" ? "aiDomainAppToggle" : "aiDomainBusinessToggle"
  );
  if (!box.checked && other && !other.checked) box.checked = true;
};

window.AIA.buildDomainsHtml = function (s) {
  const row = (id, checked, labelKey, label, helpKey, help) =>
    window.AIA.ui.row({
      id,
      labelKey,
      label,
      helpKey,
      help,
      toggle: true,
      control: `<div class="form-check m-0"><input class="form-check-input" type="checkbox" id="${id}" ${checked ? "checked" : ""} onchange="window.AIA.keepOneDomain(this)"></div>`,
    });
  return (
    row(
      "aiDomainBusinessToggle",
      s.ai_domain_business !== false,
      "ai_domain_business_data",
      "Business / Data Analysis",
      "ai_domain_business_help",
      "Questions about the user's own financial data. No access to the application's technical information."
    ) +
    row(
      "aiDomainAppToggle",
      s.ai_domain_app !== false,
      "ai_domain_app_features",
      "Application Features & Architecture",
      "ai_domain_app_help",
      "Questions about how the application is built and works. No access to the user's financial data."
    ) +
    `<div class="aia-row aia-row-wide"><div class="aia-help" data-i18n="ai_domain_rule_help">${t("ai_domain_rule_help", "With both checked, users choose a domain in the AI workspace. With one checked, there is no choice and that domain is always used.")}</div></div>`
  );
};
