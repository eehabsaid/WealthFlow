"use strict";
// Translation editor tab: per-key per-language editing grid.
// Split out of translations.js (200-line backlog). Bare globals — called via
// onclick attributes and settings/index.js's tab dispatch table.

async function renderTranslationSettings() {
  const res = await fetch("/api/translations/");
  const data = await res.json();

  const preferred = ["ar", "en", "fr", "de"];
  const languages = [
    ...preferred.filter((l) => data[l]),
    ...Object.keys(data).filter((l) => !preferred.includes(l)),
  ];
  const masterLang = languages.includes("en") ? "en" : languages[0];
  const masterKeys = Object.keys(data[masterLang] || {});
  const allKeys = [...new Set(languages.flatMap((l) => Object.keys(data[l] || {})))];

  const keys = allKeys.sort((a, b) => {
    const ia = masterKeys.indexOf(a),
      ib = masterKeys.indexOf(b);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.localeCompare(b);
  });

  const headers = languages.map((l) => `<th>${l.toUpperCase()}</th>`).join("");
  const rows = keys
    .map((key) => {
      const cells = languages
        .map((lang) => {
          const val = data[lang]?.[key];
          return `<td><input type="text" class="form-control" id="${lang}_${key}"
                value="${typeof val === "string" ? val.replace(/"/g, "&quot;") : JSON.stringify(val || "")}"></td>`;
        })
        .join("");
      return `<tr class="translation-row" data-key="${key}"><td><code>${key}</code></td>${cells}</tr>`;
    })
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:flex-end;align-items:center;
                    margin-bottom:14px;width:100%">
            
            <div style="display:flex;gap:10px;align-items:center">
                <input type="text" id="translationSearch" class="form-control"
                    style="width:180px" placeholder="Search key..."
                    data-i18n-placeholder="search_placeholder"
                    onkeyup="filterTranslations()">
                <button class="btn-primary-custom" onclick="saveTranslations()" data-i18n="save_button">Save</button>
            </div>
        </div>
        <div class="translation-table-wrapper"
            style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px">
            <table class="data-table translation-table">
                <thead><tr>
                    <th data-i18n="translation_key">Key</th>${headers}
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
  applyTranslations();
}

async function saveTranslations() {
  const res = await fetch("/api/translations/");
  const data = await res.json();
  const languages = Object.keys(data);
  const keys = [...new Set(languages.flatMap((l) => Object.keys(data[l] || {})))];
  const result = {};
  languages.forEach((lang) => {
    result[lang] = {};
    keys.forEach((key) => {
      result[lang][key] = document.getElementById(`${lang}_${key}`)?.value || "";
    });
  });
  await fetch("/api/translations/save/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(result),
  });
  showToast("Translations saved ✓");
  renderTranslationSettings();
}

function filterTranslations() {
  const q = document.getElementById("translationSearch").value.toLowerCase();
  document.querySelectorAll(".translation-row").forEach((row) => {
    row.style.display = row.dataset.key.toLowerCase().includes(q) ? "" : "none";
  });
}
