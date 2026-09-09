"use strict";
// Language settings tab: list, add/edit modals, and CRUD actions.
// Split out of translations.js (200-line backlog). Bare globals — called via
// onclick attributes and settings/index.js's tab dispatch table.

async function renderLanguageSettings() {
  const res = await fetch(`/api/settings/?t=${Date.now()}`);
  const data = await res.json();
  const activeLang = data.settings.active_language || "en";

  try {
    globalLangs = JSON.parse(data.settings.available_languages || "[]").map((l) => ({
      code: l.code,
      label: l.label,
      rtl: l.rtl === true || l.rtl === "true" || l.rtl === 1,
    }));
  } catch (e) {
    globalLangs = [];
  }

  const rows = globalLangs
    .map(
      (l, i) => `
        <tr>
            <td><code>${l.code}</code></td>
            <td>${l.label}</td>
            <td>${l.rtl ? "✓" : "—"}</td>
            <td>${
              l.code === activeLang
                ? '<span style="color:var(--accent-green);font-weight:700" data-i18n="active">Active</span>'
                : `<button class="btn-icon" onclick="setActiveLang('${l.code}')" data-i18n="set_active">Set Active</button>`
            }</td>
            <td>
                <button class="btn-icon" onclick="showLanguageModal(${i})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteLang(${i})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:14px">
            
            <button class="btn-primary-custom" onclick="showAddLangModal()" data-i18n="add_language_btn">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="language_code">Code</th>
                    <th data-i18n="language_label">Label</th>
                    <th data-i18n="language_rtl">RTL</th>
                    <th data-i18n="active">Active</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
  applyTranslations();
}

function showAddLangModal() {
  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="add_language_title">Add Language</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-4">
                    <label data-i18n="language_code_placeholder">Code</label>
                    <input class="form-control" id="lCode" placeholder="fr" maxlength="5">
                </div>
                <div class="col-5">
                    <label data-i18n="language_label_placeholder">Label</label>
                    <input class="form-control" id="lLabel" placeholder="Français">
                </div>
                <div class="col-3">
                    <label data-i18n="language_rtl_label">RTL?</label>
                    <select class="form-select" id="lRTL">
                        <option value="false" data-i18n="no">No</option>
                        <option value="true"  data-i18n="yes">Yes</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveNewLang()" data-i18n="btn_add">Add</button>
        </div>`);
  applyTranslations();
}

function showLanguageModal(index) {
  const l = globalLangs[index];
  const isRtl = l.rtl === true || l.rtl === "true";
  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="edit_language_title">Edit Language</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="language_code">Code</label>
                    <input class="form-control" id="lCode" value="${l.code}">
                </div>
                <div class="col-6">
                    <label data-i18n="language_label">Label</label>
                    <input class="form-control" id="lLabel" value="${l.label}">
                </div>
                <div class="col-12">
                    <label data-i18n="language_rtl">RTL?</label>
                    <select class="form-select" id="lRTL">
                        <option value="false" ${!isRtl ? "selected" : ""} data-i18n="no">No</option>
                        <option value="true"  ${isRtl ? "selected" : ""} data-i18n="yes">Yes</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveLanguageUpdate(${index})" data-i18n="save_button">Save</button>
        </div>`);
  applyTranslations();
}

async function setActiveLang(code) {
  await loadLanguage(code);
  const el = document.getElementById("langLabel");
  if (el) el.textContent = code.toUpperCase();
  renderLanguageSettings();
}

async function saveLanguageUpdate(index) {
  globalLangs[index] = {
    code: document.getElementById("lCode").value,
    label: document.getElementById("lLabel").value,
    rtl: document.getElementById("lRTL").value === "true",
  };
  const res = await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: "available_languages", value: JSON.stringify(globalLangs) }),
  });
  if (res.ok) {
    closeModal();
    showToast(t("msg_lang_updated", "Language updated ✓"));
    renderLanguageSettings();
    if (typeof currentLang === "function" && globalLangs[index].code === currentLang()) {
      await loadLanguage(currentLang());
    }
  } else {
    showToast("Error updating language", "error");
  }
}

async function deleteLang(idx) {
  if (!confirm("Remove this language?")) return;
  const res = await fetch("/api/settings/");
  const data = await res.json();
  const langs = JSON.parse(data.settings.available_languages || "[]");
  langs.splice(idx, 1);
  await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: "available_languages", value: JSON.stringify(langs) }),
  });
  showToast("Language removed");
  renderLanguageSettings();
}

async function saveNewLang() {
  const code = document.getElementById("lCode").value.trim().toLowerCase();
  const label = document.getElementById("lLabel").value.trim();
  const rtl = document.getElementById("lRTL").value === "true";
  if (!code || !label) {
    showToast("Code and label required", "error");
    return;
  }
  const res = await fetch("/api/settings/");
  const data = await res.json();
  let langs = [];
  try {
    langs = JSON.parse(data.settings.available_languages || "[]");
  } catch (e) {}
  if (!langs.find((l) => l.code === code)) langs.push({ code, label, rtl });
  await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: "available_languages", value: JSON.stringify(langs) }),
  });
  closeModal();
  showToast(`Language "${label}" added`);
  renderLanguageSettings();
  loadLangMenu();
}
