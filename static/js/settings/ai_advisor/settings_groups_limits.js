"use strict";
// AI Advisor settings: the number-field groups (agent limits, documents, file generation) and diagnostics.
// Same rules as settings_groups.js: every control keeps its id, data-i18n key and value.

window.AIA = window.AIA || {};

window.AIA.buildAgentLimitsHtml = function (s) {
  const n = (id, key, min, max, fallback, label, help) =>
    window.AIA.ui.numberField({
      id,
      labelKey: `${key}_label`,
      label,
      min,
      max,
      value: s[key] ?? fallback,
      helpKey: `${key}_help`,
      help,
    });
  return `<div id="aiAgentLimits">${window.AIA.ui.grid(
    n(
      "aiAgentMaxStepsInput",
      "ai_agent_max_steps",
      2,
      40,
      15,
      "Agent max steps",
      "Tool rounds per question (2-40)."
    ) +
      n(
        "aiAgentBudgetInput",
        "ai_agent_budget_s",
        60,
        3600,
        600,
        "Agent time limit (s)",
        "Whole run, in seconds (60-3600)."
      ) +
      n(
        "aiAgentMaxReadsInput",
        "ai_agent_max_reads",
        1,
        60,
        12,
        "Agent max file reads",
        "Files read per question (1-60)."
      ),
    3
  )}</div>`;
};

window.AIA.buildDocumentsHtml = function (s) {
  const n = (id, key, min, max, fallback, label, help) =>
    window.AIA.ui.numberField({
      id,
      labelKey: `${key}_label`,
      label,
      min,
      max,
      value: s[key] ?? fallback,
      helpKey: `${key}_help`,
      help,
    });
  const grid = window.AIA.ui.grid(
    n(
      "aiDocumentBudgetInput",
      "ai_document_budget_s",
      120,
      7200,
      1200,
      "Document time limit (s)",
      "Covers the whole document, in seconds (120-7200)."
    ) +
      n(
        "aiDocumentMaxTokensInput",
        "ai_document_max_tokens",
        1024,
        32768,
        6000,
        "Document output limit (tokens)",
        "Document output limit: how many tokens the AI may write per step of a document (one screen of the guide, or one chunk of a translation). Too low and the text is cut off or left untranslated; it is also capped by Context Size minus about 3500."
      ),
    2
  );
  return (
    grid +
    window.AIA.buildInstructionsBox(s, {
      id: "aiDocumentInstructionsInput",
      resetId: "aiDocumentInstructionsResetBtn",
      rows: 7,
      onReset: "resetDocumentInstructions",
      text: s.ai_document_instructions || s.ai_document_instructions_default || "",
      labelKey: "ai_document_instructions_label",
      label: "Document writing instructions",
      helpKey: "ai_document_instructions_help",
      help: "How the AI writes Word / PDF / text documents such as the user guide (one section per screen). The time limit above covers the whole document.",
    })
  );
};

window.AIA.buildFilesHtml = function (s) {
  const n = (id, key, min, max, fallback, label, help) =>
    window.AIA.ui.numberField({
      id,
      labelKey: `${key}_label`,
      label,
      min,
      max,
      value: s[key] ?? fallback,
      helpKey: `${key}_help`,
      help,
    });
  return (
    window.AIA.ui.toggleRow({
      id: "aiFileGenerationToggle",
      checked: s.ai_file_generation !== false,
      labelKey: "ai_file_generation_label",
      label: "AI File Generation",
      helpKey: "ai_file_generation_help",
      help: "Let the AI build Excel, Word, PDF, CSV and code files from your data and give you a download link in the chat",
    }) +
    `<div id="aiFileLimits">${window.AIA.ui.grid(
      n("aiFileMaxMbInput", "ai_file_max_mb", 1, 50, 10, "Max file size (MB)", "1-50 MB.") +
        n(
          "aiFileMaxRowsInput",
          "ai_file_max_rows",
          100,
          200000,
          50000,
          "Max rows per file",
          "100-200000 rows."
        ),
      2
    )}</div>`
  );
};

window.AIA.buildDiagnosticsHtml = function (s) {
  return window.AIA.ui.toggleRow({
    id: "aiPipelineDebugToggle",
    checked: !!s.ai_pipeline_debug,
    labelKey: "ai_pipeline_debug_label",
    label: "Pipeline Debug Trace",
    helpKey: "ai_pipeline_debug_help",
    help: "Adds the processing trace to each answer, for troubleshooting.",
  });
};
