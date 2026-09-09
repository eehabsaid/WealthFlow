"use strict";
// Documentation settings tab — capture/generation start actions, cancel,
// and folder-open action. Split out of documentation.js (200-line
// backlog). Bare globals — called by documentation_helpers.js.
// ════════════════════════════════════════════════════════════════════════════

async function startCapture() {
  let lang = document.getElementById("docLang").value;
  if (lang === "current") lang = localStorage.getItem("language") || "en";
  let theme = document.getElementById("docTheme").value;
  if (theme === "current") theme = localStorage.getItem("theme") || "dark";
  const category = document.getElementById("docDeviceCat").value;
  const deviceType = document.getElementById("docDeviceType").value;

  localStorage.setItem("docEngineLang", document.getElementById("docLang").value);
  localStorage.setItem("docEngineTheme", document.getElementById("docTheme").value);
  localStorage.setItem("docEngineCat", category);
  localStorage.setItem("docEngineType", deviceType);

  try {
    const btn = document.getElementById("btnCaptureScreenshots");
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Starting...';

    const res = await fetch("/api/settings/documentation/capture/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        language: lang,
        theme: theme,
        device_category: category,
        device_type: deviceType,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      alert("Error: " + (data.error || "Failed to start capture."));
    } else {
      if (!docIntervalId) docIntervalId = setInterval(pollDocStatus, 1000);
    }
  } catch (e) {
    alert("Failed to start capture.");
  }
}

async function startGeneration(docType) {
  try {
    const res = await fetch("/api/settings/documentation/generate-docs/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ docs: docType }),
    });
    const data = await res.json();
    if (!res.ok) {
      alert("Error: " + (data.error || "Failed to start generation."));
    } else {
      if (!docIntervalId) docIntervalId = setInterval(pollDocStatus, 1000);
    }
  } catch (e) {
    alert("Failed to start generation.");
  }
}

async function cancelDocumentationProcess() {
  try {
    isCancelling = true;
    await fetch("/api/settings/documentation/cancel/", { method: "POST" });
    setTimeout(pollDocStatus, 500);
  } catch (e) {
    isCancelling = false;
  }
}

async function openDocFolder(target) {
  try {
    await fetch("/api/settings/documentation/open/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: target }),
    });
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
}
