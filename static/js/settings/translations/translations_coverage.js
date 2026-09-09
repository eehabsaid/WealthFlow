"use strict";
// Translation coverage tab: per-language completeness stats and missing-key
// report modal. Split out of translations.js (200-line backlog). Bare
// globals — called via onclick attributes and settings/index.js's tab
// dispatch table.

async function renderTranslationCoverage() {
  const res = await fetch("/api/translations/");
  const data = await res.json();

  const preferred = ["ar", "en", "fr", "de"];
  const languages = [
    ...preferred.filter((l) => data[l]),
    ...Object.keys(data).filter((l) => !preferred.includes(l)),
  ];
  const allKeys = [...new Set(languages.flatMap((l) => Object.keys(data[l] || {})))];

  const stats = languages.map((lang) => {
    let translated = 0,
      missing = 0,
      empty = 0;
    allKeys.forEach((key) => {
      if (!(key in (data[lang] || {}))) {
        missing++;
        return;
      }
      const v = data[lang][key];
      if (v === null || v === undefined || v === "") empty++;
      else translated++;
    });
    const coverage = allKeys.length === 0 ? 100 : Math.round((translated / allKeys.length) * 100);
    return { lang, translated, missing, empty, coverage };
  });

  const barColor = (pct) => (pct >= 95 ? "#198754" : pct >= 80 ? "#fd7e14" : "#dc3545");

  const cards = stats
    .map(
      (s) => `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;padding:16px;min-width:220px;flex:1">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <strong>${s.lang.toUpperCase()}</strong>
                <strong>${s.coverage}%</strong>
            </div>
            <div style="height:18px;background:#e5e7eb;border-radius:20px;overflow:hidden;margin-bottom:10px">
                <div style="width:${s.coverage}%;height:100%;background:${barColor(s.coverage)};transition:width .4s"></div>
            </div>
            <div style="font-size:12px;color:var(--text-secondary)">${s.translated} / ${allKeys.length}</div>
        </div>`
    )
    .join("");

  const rows = stats
    .map(
      (s) => `
        <tr>
            <td><strong>${s.lang.toUpperCase()}</strong></td>
            <td>${allKeys.length}</td>
            <td style="color:#198754;font-weight:600">${s.translated}</td>
            <td style="color:#fd7e14;font-weight:600">${s.empty}</td>
            <td style="color:#dc3545;font-weight:600">${s.missing}</td>
            <td>
                <div style="display:flex;align-items:center;gap:10px">
                    <div style="width:180px;height:14px;background:#e5e7eb;border-radius:20px;overflow:hidden">
                        <div style="width:${s.coverage}%;height:100%;background:${barColor(s.coverage)}"></div>
                    </div>
                    <strong>${s.coverage}%</strong>
                </div>
            </td>
        </tr>`
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:14px">
            
            <button class="btn-primary-custom" onclick="showMissingTranslationsReport()" data-i18n="missing_report">Missing Report</button>
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">${cards}</div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="language">Language</th>
                    <th data-i18n="total_keys">Total Keys</th>
                    <th data-i18n="translated">Translated</th>
                    <th data-i18n="empty_values">Empty</th>
                    <th data-i18n="missing_keys">Missing</th>
                    <th data-i18n="coverage">Coverage</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
  applyTranslations();
}

async function showMissingTranslationsReport() {
  const res = await fetch("/api/translations/");
  const data = await res.json();
  const languages = Object.keys(data);
  const allKeys = [...new Set(languages.flatMap((l) => Object.keys(data[l] || {})))];

  const html = languages
    .map((lang) => {
      const missing = [],
        empty = [];
      allKeys.forEach((key) => {
        if (!(key in (data[lang] || {}))) {
          missing.push(key);
          return;
        }
        const v = data[lang][key];
        if (v === null || v === undefined || v === "") empty.push(key);
      });
      return `
            <div style="border:1px solid var(--border-color);border-radius:12px;
                        padding:12px;margin-bottom:12px;background:var(--bg-secondary)">
                <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                    <strong>${lang.toUpperCase()}</strong>
                    <span>
                        <span data-i18n="report_missing">Missing</span>: <strong style="color:#dc3545">${missing.length}</strong>
                        | <span data-i18n="report_empty">Empty</span>: <strong style="color:#fd7e14">${empty.length}</strong>
                    </span>
                </div>
                ${
                  missing.length
                    ? `<div style="margin-bottom:8px">
                    <div style="font-weight:600;color:#dc3545;margin-bottom:4px" data-i18n="report_missing_keys">Missing Keys</div>
                    <textarea class="form-control" rows="5" readonly>${missing.join("\n")}</textarea>
                </div>`
                    : ""
                }
                ${
                  empty.length
                    ? `<div>
                    <div style="font-weight:600;color:#fd7e14;margin-bottom:4px" data-i18n="report_empty_keys">Empty Keys</div>
                    <textarea class="form-control" rows="5" readonly>${empty.join("\n")}</textarea>
                </div>`
                    : ""
                }
                ${!missing.length && !empty.length ? `<div style="color:#198754;font-weight:600">✓ <span data-i18n="report_complete">Complete</span></div>` : ""}
            </div>`;
    })
    .join("");

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="report_title">Translation Coverage Report</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" style="max-height:70vh;overflow:auto">${html}</div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_close">Close</button>
        </div>`);
  applyTranslations();
}
