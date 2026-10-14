"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings: chat-pipeline controls (instant answers, AI investigator mode + code access, answer validation mode, pipeline debug).

window.AIA.VALIDATE_MODES = ["off", "flag", "regenerate"];
window.AIA.INVESTIGATOR_MODES = ["auto", "always", "off"];

window.AIA.buildPipelineControlsHtml = function () {
  const s = window.AIA.state.currentAISettings || {};
  const mode = window.AIA.VALIDATE_MODES.includes(s.ai_validate_mode) ? s.ai_validate_mode : "flag";
  const debugChecked = s.ai_pipeline_debug ? "checked" : "";
  const directChecked = s.ai_direct_answers === false ? "" : "checked";
  const invMode = window.AIA.INVESTIGATOR_MODES.includes(s.ai_investigator_mode)
    ? s.ai_investigator_mode
    : "auto";
  const codeChecked = s.ai_code_access === false ? "" : "checked";
  const invOptions = window.AIA.INVESTIGATOR_MODES.map(
    (m) =>
      `<option value="${m}" ${m === invMode ? "selected" : ""} data-i18n="ai_investigator_mode_${m}">${t(`ai_investigator_mode_${m}`, m)}</option>`
  ).join("");
  const fileOn = s.ai_file_generation === false ? "" : "checked";
  const fileNum = (id, key, min, max, fallback) =>
    `<div class="d-flex align-items-center gap-2 mb-0"><label class="fs-6 mb-0" for="${id}" data-i18n="${key}_label">${t(`${key}_label`, key)}</label><input type="number" class="form-control form-control-sm w-auto" style="max-width:7.5rem" id="${id}" min="${min}" max="${max}" value="${s[key] ?? fallback}"></div>`;
  const options = window.AIA.VALIDATE_MODES.map(
    (m) =>
      `<option value="${m}" ${m === mode ? "selected" : ""} data-i18n="ai_validate_mode_${m}">${t(`ai_validate_mode_${m}`, m)}</option>`
  ).join("");
  return `
                    <div class="form-check form-switch fs-5 mb-0" title="${t("ai_direct_answers_help", "Answer simple data questions instantly from your data without the AI model")}">
                        <input class="form-check-input" type="checkbox" id="aiDirectAnswersToggle" ${directChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiDirectAnswersToggle" data-i18n="ai_direct_answers_label">${t("ai_direct_answers_label", "Instant Data Answers")}</label>
                        <div class="form-text fs-6 fw-normal" data-i18n="ai_direct_answers_help">${t("ai_direct_answers_help", "Answer simple data questions instantly from your data without the AI model")}</div>
                    </div>
                    <div class="d-flex align-items-center gap-2 mb-0" title="${t("ai_investigator_mode_hint", "Lets the AI explore the whole app with read-only tools when a normal answer is not enough")}">
                        <label class="fs-6 fw-semibold mb-0" for="aiInvestigatorModeSelect" data-i18n="ai_investigator_mode_label">${t("ai_investigator_mode_label", "AI Investigator")}</label>
                        <select class="form-select form-select-sm w-auto" id="aiInvestigatorModeSelect">${invOptions}</select>
                    </div>
                    <div class="form-check form-switch fs-5 mb-0" title="${t("ai_code_access_help", "Read-only; secrets and databases are never exposed. Customers never get code access")}">
                        <input class="form-check-input" type="checkbox" id="aiCodeAccessToggle" ${codeChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiCodeAccessToggle" data-i18n="ai_code_access_label">${t("ai_code_access_label", "Let the AI read the source code (admin only)")}</label>
                        <div class="form-text fs-6 fw-normal" data-i18n="ai_code_access_help">${t("ai_code_access_help", "Read-only; secrets and databases are never exposed. Customers never get code access")}</div>
                    </div>
                    <div class="form-check form-switch fs-5 mb-0" title="${t("ai_file_generation_help", "Let the AI build Excel, Word, PDF, CSV and code files from your data and give you a download link in the chat")}">
                        <input class="form-check-input" type="checkbox" id="aiFileGenerationToggle" ${fileOn}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiFileGenerationToggle" data-i18n="ai_file_generation_label">${t("ai_file_generation_label", "AI File Generation")}</label>
                        <div class="form-text fs-6 fw-normal" data-i18n="ai_file_generation_help">${t("ai_file_generation_help", "Let the AI build Excel, Word, PDF, CSV and code files from your data and give you a download link in the chat")}</div>
                    </div>
                    <div class="d-flex flex-wrap gap-3 mb-0" id="aiFileLimits">
                        ${fileNum("aiFileMaxMbInput", "ai_file_max_mb", 1, 50, 10)}
                        ${fileNum("aiFileMaxRowsInput", "ai_file_max_rows", 100, 200000, 50000)}
                    </div>
                    <div class="d-flex align-items-center gap-2 mb-0" title="${t("ai_validate_mode_hint", "Checks figures in the answer against your data")}">
                        <label class="fs-6 fw-semibold mb-0" for="aiValidateModeSelect" data-i18n="ai_validate_mode_label">${t("ai_validate_mode_label", "Answer Validation")}</label>
                        <select class="form-select form-select-sm w-auto" id="aiValidateModeSelect">${options}</select>
                    </div>
                    <div class="form-check form-switch fs-5 mb-0">
                        <input class="form-check-input" type="checkbox" id="aiPipelineDebugToggle" ${debugChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiPipelineDebugToggle" data-i18n="ai_pipeline_debug_label">${t("ai_pipeline_debug_label", "Pipeline Debug Trace")}</label>
                    </div>`;
};
