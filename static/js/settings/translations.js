"use strict";
// Language settings and translations/coverage manager
// This file is part of the settings module. Do not edit directly.

async function renderLanguageSettings() {
    const res  = await fetch(`/api/settings/?t=${Date.now()}`);
    const data = await res.json();
    const activeLang = data.settings.active_language || 'en';

    try {
        globalLangs = JSON.parse(data.settings.available_languages || '[]').map(l => ({
            code:  l.code,
            label: l.label,
            rtl:   l.rtl === true || l.rtl === 'true' || l.rtl === 1,
        }));
    } catch (e) { globalLangs = []; }

    const rows = globalLangs.map((l, i) => `
        <tr>
            <td><code>${l.code}</code></td>
            <td>${l.label}</td>
            <td>${l.rtl ? '✓' : '—'}</td>
            <td>${l.code === activeLang
                ? '<span style="color:var(--accent-green);font-weight:700" data-i18n="active">Active</span>'
                : `<button class="btn-icon" onclick="setActiveLang('${l.code}')" data-i18n="set_active">Set Active</button>`
            }</td>
            <td>
                <button class="btn-icon" onclick="showLanguageModal(${i})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteLang(${i})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
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
    const isRtl = l.rtl === true || l.rtl === 'true';
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
                        <option value="false" ${!isRtl ? 'selected' : ''} data-i18n="no">No</option>
                        <option value="true"  ${isRtl  ? 'selected' : ''} data-i18n="yes">Yes</option>
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
    const el = document.getElementById('langLabel');
    if (el) el.textContent = code.toUpperCase();
    renderLanguageSettings();
}

async function saveLanguageUpdate(index) {
    globalLangs[index] = {
        code:  document.getElementById('lCode').value,
        label: document.getElementById('lLabel').value,
        rtl:   document.getElementById('lRTL').value === 'true',
    };
    const res = await fetch('/api/settings/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ key: 'available_languages', value: JSON.stringify(globalLangs) }),
    });
    if (res.ok) {
        closeModal();
        showToast(t('msg_lang_updated', 'Language updated ✓'));
        renderLanguageSettings();
        if (typeof currentLang === 'function' && globalLangs[index].code === currentLang()) {
            await loadLanguage(currentLang());
        }
    } else {
        showToast('Error updating language', 'error');
    }
}

async function deleteLang(idx) {
    if (!confirm('Remove this language?')) return;
    const res  = await fetch('/api/settings/');
    const data = await res.json();
    const langs = JSON.parse(data.settings.available_languages || '[]');
    langs.splice(idx, 1);
    await fetch('/api/settings/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ key: 'available_languages', value: JSON.stringify(langs) }),
    });
    showToast('Language removed');
    renderLanguageSettings();
}

async function saveNewLang() {
    const code  = document.getElementById('lCode').value.trim().toLowerCase();
    const label = document.getElementById('lLabel').value.trim();
    const rtl   = document.getElementById('lRTL').value === 'true';
    if (!code || !label) { showToast('Code and label required', 'error'); return; }
    const res  = await fetch('/api/settings/');
    const data = await res.json();
    let langs  = [];
    try { langs = JSON.parse(data.settings.available_languages || '[]'); } catch (e) {}
    if (!langs.find(l => l.code === code)) langs.push({ code, label, rtl });
    await fetch('/api/settings/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ key: 'available_languages', value: JSON.stringify(langs) }),
    });
    closeModal();
    showToast(`Language "${label}" added`);
    renderLanguageSettings();
    loadLangMenu();
}

// ════════════════════════════════════════════════════════════════════════════
// CURRENCY SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderTranslationSettings() {
    const res  = await fetch('/api/translations/');
    const data = await res.json();

    const preferred  = ['ar', 'en', 'fr', 'de'];
    const languages  = [...preferred.filter(l => data[l]),
                        ...Object.keys(data).filter(l => !preferred.includes(l))];
    const masterLang = languages.includes('en') ? 'en' : languages[0];
    const masterKeys = Object.keys(data[masterLang] || {});
    const allKeys    = [...new Set(languages.flatMap(l => Object.keys(data[l] || {})))];

    const keys = allKeys.sort((a, b) => {
        const ia = masterKeys.indexOf(a), ib = masterKeys.indexOf(b);
        if (ia !== -1 && ib !== -1) return ia - ib;
        if (ia !== -1) return -1;
        if (ib !== -1) return 1;
        return a.localeCompare(b);
    });

    const headers = languages.map(l => `<th>${l.toUpperCase()}</th>`).join('');
    const rows    = keys.map(key => {
        const cells = languages.map(lang => {
            const val = data[lang]?.[key];
            return `<td><input type="text" class="form-control" id="${lang}_${key}"
                value="${typeof val === 'string' ? val.replace(/"/g, '&quot;') : JSON.stringify(val || '')}"></td>`;
        }).join('');
        return `<tr class="translation-row" data-key="${key}"><td><code>${key}</code></td>${cells}</tr>`;
    }).join('');

    document.getElementById('settingsContent').innerHTML = `
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
    const res  = await fetch('/api/translations/');
    const data = await res.json();
    const languages = Object.keys(data);
    const keys = [...new Set(languages.flatMap(l => Object.keys(data[l] || {})))];
    const result = {};
    languages.forEach(lang => {
        result[lang] = {};
        keys.forEach(key => { result[lang][key] = document.getElementById(`${lang}_${key}`)?.value || ''; });
    });
    await fetch('/api/translations/save/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(result),
    });
    showToast('Translations saved ✓');
    renderTranslationSettings();
}

function filterTranslations() {
    const q = document.getElementById('translationSearch').value.toLowerCase();
    document.querySelectorAll('.translation-row').forEach(row => {
        row.style.display = row.dataset.key.toLowerCase().includes(q) ? '' : 'none';
    });
}

// ════════════════════════════════════════════════════════════════════════════
// TRANSLATION COVERAGE TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderTranslationCoverage() {
    const res  = await fetch('/api/translations/');
    const data = await res.json();

    const preferred = ['ar', 'en', 'fr', 'de'];
    const languages = [...preferred.filter(l => data[l]),
                       ...Object.keys(data).filter(l => !preferred.includes(l))];
    const allKeys   = [...new Set(languages.flatMap(l => Object.keys(data[l] || {})))];

    const stats = languages.map(lang => {
        let translated = 0, missing = 0, empty = 0;
        allKeys.forEach(key => {
            if (!(key in (data[lang] || {}))) { missing++; return; }
            const v = data[lang][key];
            if (v === null || v === undefined || v === '') empty++;
            else translated++;
        });
        const coverage = allKeys.length === 0 ? 100
            : Math.round((translated / allKeys.length) * 100);
        return { lang, translated, missing, empty, coverage };
    });

    const barColor = pct => pct >= 95 ? '#198754' : pct >= 80 ? '#fd7e14' : '#dc3545';

    const cards = stats.map(s => `
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
        </div>`).join('');

    const rows = stats.map(s => `
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
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
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
    const res  = await fetch('/api/translations/');
    const data = await res.json();
    const languages = Object.keys(data);
    const allKeys   = [...new Set(languages.flatMap(l => Object.keys(data[l] || {})))];

    const html = languages.map(lang => {
        const missing = [], empty = [];
        allKeys.forEach(key => {
            if (!(key in (data[lang] || {}))) { missing.push(key); return; }
            const v = data[lang][key];
            if (v === null || v === undefined || v === '') empty.push(key);
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
                ${missing.length ? `<div style="margin-bottom:8px">
                    <div style="font-weight:600;color:#dc3545;margin-bottom:4px" data-i18n="report_missing_keys">Missing Keys</div>
                    <textarea class="form-control" rows="5" readonly>${missing.join('\n')}</textarea>
                </div>` : ''}
                ${empty.length ? `<div>
                    <div style="font-weight:600;color:#fd7e14;margin-bottom:4px" data-i18n="report_empty_keys">Empty Keys</div>
                    <textarea class="form-control" rows="5" readonly>${empty.join('\n')}</textarea>
                </div>` : ''}
                ${!missing.length && !empty.length ? `<div style="color:#198754;font-weight:600">✓ <span data-i18n="report_complete">Complete</span></div>` : ''}
            </div>`;
    }).join('');

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

