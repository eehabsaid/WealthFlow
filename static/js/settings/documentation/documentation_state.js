"use strict";
// Documentation settings tab — shared state, tab render entry point, and
// device-type dropdown sync. Split out of documentation.js (200-line
// backlog). Bare globals — called by settings/index.js and
// documentation_helpers.js.
// ════════════════════════════════════════════════════════════════════════════

let docIntervalId = null;
let docHistoryData = [];
let deviceInventory = { desktop: [], tablet: [], mobile: [] };
let isCancelling = false;
let activeProcessType = null; // 'CAPTURE', 'GENERATION', or null

async function renderDocumentationSettings() {
  const contentDiv = document.getElementById("settingsContent");
  if (!contentDiv) return;

  if (typeof buildDocumentationSettingsLayoutHtml === "function") {
    contentDiv.innerHTML = buildDocumentationSettingsLayoutHtml();
  }

  applyTranslations();
  updateDocDeviceType();

  try {
    const res = await fetch("/api/settings/?t=" + Date.now());
    const data = await res.json();
    const langs = JSON.parse(data.settings.available_languages || "[]");
    const langSelect = document.getElementById("docLang");
    if (langSelect && langs.length > 0) {
      let optionsHtml =
        '<option value="current" data-i18n="doc_lang_current">Current Language</option><option value="ALL" data-i18n="doc_lang_all">All Supported Languages</option>';
      for (const l of langs) {
        optionsHtml += `<option value="${l.code}">${l.label || l.code}</option>`;
      }
      langSelect.innerHTML = optionsHtml;
      applyTranslations(langSelect);
    }
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }

  try {
    const res = await fetch("/api/settings/documentation/devices/?t=" + Date.now());
    if (res.ok) deviceInventory = await res.json();
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }

  const savedLang = localStorage.getItem("docEngineLang");
  const savedTheme = localStorage.getItem("docEngineTheme");
  const savedCat = localStorage.getItem("docEngineCat");
  const savedType = localStorage.getItem("docEngineType");

  if (savedLang) document.getElementById("docLang").value = savedLang;
  if (savedTheme) document.getElementById("docTheme").value = savedTheme;
  if (savedCat) {
    document.getElementById("docDeviceCat").value = savedCat;
    updateDocDeviceType();
    if (savedType) document.getElementById("docDeviceType").value = savedType;
  }

  if (docIntervalId) clearInterval(docIntervalId);
  pollDocStatus(); // check once on load
  loadDocHistory();
}

function updateDocDeviceType() {
  const cat = document.getElementById("docDeviceCat").value;
  const typeSelect = document.getElementById("docDeviceType");
  if (cat === "ALL") {
    typeSelect.innerHTML = '<option value="ALL">Automatic</option>';
    typeSelect.disabled = true;
    return;
  }
  typeSelect.disabled = false;
  let optionsList = [];
  if (deviceInventory.categories && deviceInventory.categories[cat.toLowerCase()]) {
    optionsList = deviceInventory.categories[cat.toLowerCase()].filter(
      (item) => item.enabled !== false
    );
  }
  let optionsHtml = "";
  let defaultId = null;
  let firstEnabledId = null;
  for (const item of optionsList) {
    let i18nAttr =
      item.display_name === "Current Resolution" ? ' data-i18n="doc_engine_current_res"' : "";
    optionsHtml += `<option value="${item.id}"${i18nAttr}>${item.display_name}</option>`;
    if (!firstEnabledId) firstEnabledId = item.id;
    if (item.default) defaultId = item.id;
  }
  typeSelect.innerHTML = optionsHtml;
  if (optionsList.length > 0) {
    typeSelect.value = defaultId || firstEnabledId;
  }
  if (typeof applyTranslations === "function") applyTranslations(typeSelect);
}
