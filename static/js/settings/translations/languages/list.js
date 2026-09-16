"use strict";
// Language settings tab: list rendering and set-active action.
// Split out of translations_languages.js (200-line backlog). Bare globals —
// called via onclick attributes and settings/index.js's tab dispatch table.

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

async function setActiveLang(code) {
  await loadLanguage(code);
  const el = document.getElementById("langLabel");
  if (el) el.textContent = code.toUpperCase();
  renderLanguageSettings();
}
