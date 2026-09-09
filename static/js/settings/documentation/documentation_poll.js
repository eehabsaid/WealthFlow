"use strict";
// Documentation settings tab — status polling loop + window exports.
// Split out of documentation.js (200-line backlog). Bare global.
// ════════════════════════════════════════════════════════════════════════════

// (History table rendering functions loadDocHistory, sortDocHistory, renderDocHistory are loaded from documentation_helpers.js)
async function pollDocStatus() {
  const btnCap = document.getElementById("btnCaptureScreenshots");
  if (!btnCap) return;

  try {
    const res = await fetch("/api/settings/documentation/status/?t=" + Date.now());
    const statusData = await res.json();
    const rawStatus = (statusData.status || "").toUpperCase();
    const isRunning = rawStatus === "RUNNING";

    const capProgress = document.getElementById("captureProgressSection");
    const genProgress = document.getElementById("generationProgressSection");
    const btnCancelCap = document.getElementById("btnCancelCapture");
    const btnCancelGen = document.getElementById("btnCancelGeneration");

    const btnGenAll = document.getElementById("btnGenerateAll");
    const btnGenUser = document.getElementById("btnGenerateUser");
    const btnGenAdmin = document.getElementById("btnGenerateAdmin");
    const btnGenTech = document.getElementById("btnGenerateTech");

    if (isRunning) {
      if (!docIntervalId) {
        docIntervalId = setInterval(pollDocStatus, 1000);
      }
      activeProcessType = statusData.device === "N/A" ? "GENERATION" : "CAPTURE";

      if (activeProcessType === "CAPTURE") {
        btnCap.disabled = true;
        btnCap.innerHTML =
          '<i class="bi bi-camera me-2"></i><span data-i18n="doc_btn_running_capture">Running Capture...</span>';
        if (typeof applyTranslations === "function") applyTranslations(btnCap);
        if (!isCancelling) btnCancelCap.disabled = false;
        capProgress.style.display = "block";

        document.getElementById("capStatus").textContent = statusData.page || "Capturing...";
        document.getElementById("capPage").textContent = statusData.page || "-";
        document.getElementById("capTab").textContent = statusData.tab || "-";
        document.getElementById("capNested").textContent = statusData.nested_tab || "-";
        document.getElementById("capModal").textContent = statusData.modal || "-";
        document.getElementById("capLang").textContent = statusData.language || "-";
        document.getElementById("capTheme").textContent = statusData.theme || "-";
        document.getElementById("capDevice").textContent = statusData.device || "-";
        document.getElementById("capCount").textContent =
          `${statusData.screenshots_count || 0} / ${statusData.total || "?"}`;
        const mm = String(Math.floor((statusData.elapsed_seconds || 0) / 60)).padStart(2, "0");
        const ss = String((statusData.elapsed_seconds || 0) % 60).padStart(2, "0");
        document.getElementById("capElapsed").textContent = `${mm}:${ss}`;

        btnGenAll.disabled = true;
        btnGenUser.disabled = true;
        btnGenAdmin.disabled = true;
        btnGenTech.disabled = true;
      } else {
        btnGenAll.disabled = true;
        btnGenUser.disabled = true;
        btnGenAdmin.disabled = true;
        btnGenTech.disabled = true;

        let activeBtn = btnGenAll;
        let activeText = "doc_btn_generating";
        let defaultText = "Generating...";
        if (statusData.current_doc === "User") {
          activeBtn = btnGenUser;
        } else if (statusData.current_doc === "Admin") {
          activeBtn = btnGenAdmin;
        } else if (statusData.current_doc === "Technical") {
          activeBtn = btnGenTech;
        }

        activeBtn.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><span data-i18n="' +
          activeText +
          '">' +
          defaultText +
          "</span>";
        if (typeof applyTranslations === "function") applyTranslations(activeBtn);
        if (!isCancelling) btnCancelGen.disabled = false;
        genProgress.style.display = "block";

        document.getElementById("genStatus").textContent = statusData.page || "Building...";
        document.getElementById("genDoc").textContent = statusData.current_doc || "-";
        document.getElementById("genFormat").textContent = statusData.current_format || "-";
        document.getElementById("genPage").textContent = statusData.page || "-";
        document.getElementById("genScreenshot").textContent = statusData.screenshots_count || "-";
        document.getElementById("genPercent").textContent = `${statusData.progress || 0}%`;
        const mm = String(Math.floor((statusData.elapsed_seconds || 0) / 60)).padStart(2, "0");
        const ss = String((statusData.elapsed_seconds || 0) % 60).padStart(2, "0");
        document.getElementById("genElapsed").textContent = `${mm}:${ss}`;

        btnCap.disabled = true;
      }
    } else {
      btnCap.disabled = false;
      btnCap.innerHTML =
        '<i class="bi bi-camera me-2"></i><span data-i18n="doc_btn_capture">Capture Screenshots</span>';
      if (typeof applyTranslations === "function") applyTranslations(btnCap);
      btnCancelCap.disabled = true;

      btnGenAll.disabled = false;
      btnGenUser.disabled = false;
      btnGenAdmin.disabled = false;
      btnGenTech.disabled = false;
      btnGenAll.innerHTML =
        '<i class="bi bi-file-earmark-check me-2"></i><span data-i18n="doc_btn_gen_all">Generate All Documents</span>';
      btnGenUser.innerHTML =
        '<i class="bi bi-person-badge me-2"></i><span data-i18n="doc_btn_gen_user">User Guide</span>';
      btnGenAdmin.innerHTML =
        '<i class="bi bi-shield-lock me-2"></i><span data-i18n="doc_btn_gen_admin">Admin Guide</span>';
      btnGenTech.innerHTML =
        '<i class="bi bi-code-slash me-2"></i><span data-i18n="doc_btn_gen_tech">Technical Guide</span>';
      if (typeof applyTranslations === "function") {
        applyTranslations(btnGenAll);
        applyTranslations(btnGenUser);
        applyTranslations(btnGenAdmin);
        applyTranslations(btnGenTech);
      }
      btnCancelGen.disabled = true;

      if (["COMPLETED", "CANCELLED", "FAILED"].includes(rawStatus)) {
        if (activeProcessType === "CAPTURE") {
          document.getElementById("capStatus").textContent = rawStatus;
          document.getElementById("capStatus").style.color =
            rawStatus === "COMPLETED" ? "var(--accent-primary)" : "#ff6b6b";
        } else if (activeProcessType === "GENERATION") {
          document.getElementById("genStatus").textContent = rawStatus;
          document.getElementById("genStatus").style.color =
            rawStatus === "COMPLETED" ? "var(--accent-primary)" : "#ff6b6b";
        }
      }

      if (!isRunning) {
        isCancelling = false;
        activeProcessType = null;
        if (docIntervalId) {
          clearInterval(docIntervalId);
          docIntervalId = null;
        }
        if (["COMPLETED", "CANCELLED", "FAILED"].includes(rawStatus)) {
          loadDocHistory();
        }
      }
    }
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
}

window.renderDocumentationSettings = renderDocumentationSettings;
window.updateDocDeviceType = updateDocDeviceType;
window.handleCaptureClick = handleCaptureClick;
window.handleGenerateClick = handleGenerateClick;
window.cancelDocumentationProcess = cancelDocumentationProcess;
window.openDocFolder = openDocFolder;
window.loadDocHistory = loadDocHistory;
