"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings: chat-pipeline controls (answer validation mode + pipeline debug toggle).

window.AIA.VALIDATE_MODES = ["off", "flag", "regenerate"];

window.AIA.buildPipelineControlsHtml = function () {
  const s = window.AIA.state.currentAISettings || {};
  const mode = window.AIA.VALIDATE_MODES.includes(s.ai_validate_mode)
    ? s.ai_validate_mode
    : "flag";
  const debugChecked = s.ai_pipeline_debug ? "checked" : "";
  const options = window.AIA.VALIDATE_MODES.map(
    (m) =>
      `<option value="${m}" ${m === mode ? "selected" : ""} data-i18n="ai_validate_mode_${m}">${t(`ai_validate_mode_${m}`, m)}</option>`,
  ).join("");
  return `
                    <div class="d-flex align-items-center gap-2 mb-0" title="${t("ai_validate_mode_hint", "Checks figures in the answer against your data")}">
                        <label class="fs-6 fw-semibold mb-0" for="aiValidateModeSelect" data-i18n="ai_validate_mode_label">${t("ai_validate_mode_label", "Answer Validation")}</label>
                        <select class="form-select form-select-sm w-auto" id="aiValidateModeSelect">${options}</select>
                    </div>
                    <div class="form-check form-switch fs-5 mb-0">
                        <input class="form-check-input" type="checkbox" id="aiPipelineDebugToggle" ${debugChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiPipelineDebugToggle" data-i18n="ai_pipeline_debug_label">${t("ai_pipeline_debug_label", "Pipeline Debug Trace")}</label>
                    </div>`;
};
