"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings: the allowed modes and the instructions helpers (restore default / save default as ""). The controls themselves
// are built by settings_groups.js.

window.AIA.VALIDATE_MODES = ["off", "flag", "regenerate"];
window.AIA.INVESTIGATOR_MODES = ["auto", "always", "off"];

window.AIA.resetDocumentInstructions = function () {
  const box = document.getElementById("aiDocumentInstructionsInput");
  if (box)
    box.value = (window.AIA.state.currentAISettings || {}).ai_document_instructions_default || "";
};

window.AIA.documentInstructionsForSave = function () {
  const text = (document.getElementById("aiDocumentInstructionsInput")?.value || "").trim();
  const dflt = (
    (window.AIA.state.currentAISettings || {}).ai_document_instructions_default || ""
  ).trim();
  return text === dflt ? "" : text;
};

window.AIA.resetAgentInstructions = function () {
  const box = document.getElementById("aiAgentInstructionsInput");
  if (box)
    box.value = (window.AIA.state.currentAISettings || {}).ai_agent_instructions_default || "";
};

window.AIA.agentInstructionsForSave = function () {
  const text = (document.getElementById("aiAgentInstructionsInput")?.value || "").trim();
  const dflt = (
    (window.AIA.state.currentAISettings || {}).ai_agent_instructions_default || ""
  ).trim();
  return text === dflt ? "" : text;
};
