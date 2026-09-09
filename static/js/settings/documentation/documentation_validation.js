"use strict";
// Documentation settings tab — validation dialog and capture/generate click
// handlers (pre-flight prerequisite checks). Split out of documentation.js
// (200-line backlog). Bare globals — called by documentation_helpers.js.
// ════════════════════════════════════════════════════════════════════════════

function showValidationDialog(title, errors) {
  const errorKeys = {
    "Node.js is not installed or not in PATH.": "doc_err_node_missing",
    "npm is not installed or not in PATH.": "doc_err_npm_missing",
    "Playwright is not installed.": "doc_err_playwright_missing",
    "Screenshots directory is not writable.": "doc_err_capture_dir_not_writable",
    "Cannot create screenshots directory.": "doc_err_capture_dir_not_created",
    "Screenshot folder does not exist.": "doc_err_screenshots_folder_missing",
    "Screenshot folder contains no screenshots.": "doc_err_screenshots_empty",
    "manifest.json does not exist.": "doc_err_manifest_missing",
    "manifest.json is not valid JSON.": "doc_err_manifest_invalid",
    "capture_metadata.json does not exist.": "doc_err_metadata_missing",
    "capture_metadata.json is not valid JSON.": "doc_err_metadata_invalid",
    "page_descriptions.json does not exist.": "doc_err_descriptions_missing",
    "Output directory is not writable.": "doc_err_output_not_writable",
    "Cannot create output directory.": "doc_err_output_not_created",
    "Playwright PDF renderer (html_to_pdf.js) is missing.": "doc_err_pdf_script_missing",
    "python-docx is not installed.": "doc_err_python_docx_missing",
    "pdf2docx is not installed.": "doc_err_pdf2docx_missing",
  };

  const titleKeys = {
    "Capture Validation Failed": "doc_err_title_capture",
    "Generation Validation Failed": "doc_err_title_generation",
    Error: "doc_err_title_error",
  };

  const tFallback = (key, defaultText) =>
    typeof window.t === "function" ? window.t(key, defaultText) : defaultText;

  const translatedTitle = tFallback(titleKeys[title] || title, title);
  const translatedMissingPrereqs = tFallback(
    "doc_err_missing_prereqs",
    "The following prerequisites are missing or invalid:"
  );
  const translatedCloseBtn = tFallback("btn_close", "Close");

  const errorItems = errors
    .map((e) => {
      const translatedErr = tFallback(errorKeys[e] || e, e);
      return `<li>${translatedErr}</li>`;
    })
    .join("");

  const modalHtml = `
        <div class="modal-header" style="border-color:var(--border-color);">
            <h5 class="modal-title text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>${translatedTitle}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" style="filter: invert(var(--invert-icons, 0));"></button>
        </div>
        <div class="modal-body">
            <p style="color:var(--text-primary);">${translatedMissingPrereqs}</p>
            <ul style="color:#ff6b6b; font-weight:500;">
                ${errorItems}
            </ul>
        </div>
        <div class="modal-footer" style="border-color:var(--border-color);">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="if(typeof closeModal === 'function') closeModal();">${translatedCloseBtn}</button>
        </div>
    `;
  if (typeof showModal === "function") {
    showModal(modalHtml);
  } else {
    alert(
      `${translatedTitle}\n\n${translatedMissingPrereqs}\n${errors.map((e) => tFallback(errorKeys[e] || e, e)).join("\n")}`
    );
  }
}

async function handleCaptureClick() {
  try {
    const res = await fetch("/api/settings/documentation/validate-capture/");
    const data = await res.json();
    if (data.valid) {
      startCapture();
    } else {
      showValidationDialog("Capture Validation Failed", data.errors);
    }
  } catch (e) {
    showValidationDialog("Error", ["Failed to run capture validation. Server may be down."]);
  }
}

async function handleGenerateClick(docType) {
  try {
    const res = await fetch("/api/settings/documentation/validate-generate/");
    const data = await res.json();
    if (data.valid) {
      startGeneration(docType);
    } else {
      showValidationDialog("Generation Validation Failed", data.errors);
    }
  } catch (e) {
    showValidationDialog("Error", ["Failed to run generation validation."]);
  }
}
