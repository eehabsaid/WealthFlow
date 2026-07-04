// settings.js — Settings page (languages, companies, banks, currencies, users, translations)

'use strict';

// ── Module state ──────────────────────────────────────────────────────────
let globalLangs = [];

// ════════════════════════════════════════════════════════════════════════════
// MAIN ROUTER
// ════════════════════════════════════════════════════════════════════════════

async function renderSettings(route) {
    const mc = document.getElementById('main-content');

    const TAB_MAP = {
        companies:         'companies',
        banks:             'banks',
        currency:          'currency',
        users:             'users',
        translationcoverage: 'translationcoverage',
        translations:      'translations',
        reminders:         'reminders',
        certstatus:        'certstatus',
        goldsettings:      'goldsettings',
        'settings-dashboard': 'dashboard',
        languages:         'languages',
    };

    let activeTab = 'languages';
    for (const [key, val] of Object.entries(TAB_MAP)) {
        if (route.includes(key)) { activeTab = val; break; }
    }

    const tabs = [
        { id: 'languages',          i18n: 'settings_languages',         fallback: 'Languages',         route: 'settings-languages'          },
        { id: 'companies',          i18n: 'settings_companies',         fallback: 'Companies',         route: 'settings-companies'          },
        { id: 'banks',              i18n: 'settings_banks',             fallback: 'Banks',             route: 'settings-banks'              },
        { id: 'currency',           i18n: 'settings_currency',          fallback: 'Currency',          route: 'settings-currency'           },
        { id: 'users',              i18n: 'settings_users',             fallback: 'Users',             route: 'settings-users'              },
        { id: 'translations',       i18n: 'settings_translations',      fallback: 'Translations',      route: 'settings-translations'       },
        { id: 'translationcoverage',i18n: 'settings_translation_coverage', fallback: 'Translation Coverage', route: 'settings-translationcoverage' },
        { id: 'reminders',          i18n: 'tab_reminders',              fallback: 'Reminders',         route: 'settings-reminders'          },
        { id: 'certstatus',         i18n: 'tab_cert_status',            fallback: 'Certificate Status', route: 'settings-certstatus'         },
        { id: 'goldsettings',       i18n: 'tab_gold_settings',          fallback: 'Gold Settings',    route: 'settings-goldsettings'       },
        { id: 'dashboard',          i18n: 'tab_dashboard_sett',         fallback: 'Dashboard',         route: 'settings-dashboard'          },
    ];

    const tabBar = tabs.map(tab => {
        const label = t(tab.i18n, tab.fallback || tab.id);
        return `
        <button class="settings-tab ${activeTab === tab.id ? 'active' : ''}"
            onclick="navigate('${tab.route}')"
            data-i18n="${tab.i18n}">
            ${label}
        </button>`;
    }).join('');

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_settings">Settings</div></div>
        </div>
        <div style="border-bottom:1px solid var(--border-color);margin-bottom:20px;
                    display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap">
            ${tabBar}
        </div>
        <div id="settingsContent"></div>`;

    applyTranslations();

    const renderers = {
        languages:          renderLanguageSettings,
        companies:          renderCompanySettings,
        currency:           renderCurrencySettings,
        users:              renderUserSettings,
        translations:       renderTranslationSettings,
        translationcoverage:renderTranslationCoverage,
        reminders:          renderReminderSettings,
        certstatus:         renderCertStatusSettings,
        goldsettings:       renderGoldSettings,
        dashboard:          renderDashboardSettings,
        banks:              renderBankSettings,
    };

    await (renderers[activeTab] || renderers.banks)();
}

// ════════════════════════════════════════════════════════════════════════════
// DASHBOARD SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderDashboardSettings() {
    const res = await fetch('/api/settings/');
    const s   = (await res.json()).settings || {};

    const toggle = (key, i18nLabel, i18nDesc, checked) => `
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:12px 0;border-bottom:1px solid var(--border-color)">
            <div>
                <div style="font-weight:600;color:var(--text-primary)" data-i18n="${i18nLabel}"></div>
                <div style="font-size:12px;color:var(--text-muted)" data-i18n="${i18nDesc}"></div>
            </div>
            <input type="checkbox" ${checked ? 'checked' : ''}
                onchange="saveAppSetting('${key}', this.checked ? 'true' : 'false')">
        </div>`;

    document.getElementById('settingsContent').innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;padding:20px">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:16px"
                data-i18n="dashboard_settings"></div>
            ${toggle('dashboard_show_certs',     'dashboard_show_certs',     'dashboard_show_certs_desc',     s.dashboard_show_certs     !== 'false')}
            ${toggle('dashboard_show_reminders', 'dashboard_show_reminders', 'dashboard_show_reminders_desc', s.dashboard_show_reminders !== 'false')}
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0">
                <div>
                    <div style="font-weight:600;color:var(--text-primary)" data-i18n="dashboard_show_salary"></div>
                    <div style="font-size:12px;color:var(--text-muted)" data-i18n="dashboard_show_salary_desc"></div>
                </div>
                <input type="checkbox" ${s.dashboard_show_salary !== 'false' ? 'checked' : ''}
                    onchange="saveAppSetting('dashboard_show_salary', this.checked ? 'true' : 'false')">
            </div>
        </div>`;
    applyTranslations();
}

function saveAppSetting(key, value) {
    fetch('/api/settings/', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ [key]: value }),
    }).then(() => showToast(t('settings_saved', 'Settings saved ✓')));
}

// ════════════════════════════════════════════════════════════════════════════
// GOLD SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderGoldSettings() {
    const [typesRes, puritiesRes] = await Promise.all([
        fetch('/api/settings/gold-types/'),
        fetch('/api/settings/gold-purities/'),
    ]);

    const typeData = await typesRes.json();
    const purityData = await puritiesRes.json();

    const types = typeData.items || [];
    const purities = purityData.items || [];

    const typeRows = types.map(item => `
        <tr>
            <td>${item.name}</td>
            <td>${item.order ?? 0}</td>
            <td><span style="color:${item.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}" data-i18n="${item.is_active ? 'active' : 'inactive'}">${item.is_active ? t('active', 'Active') : t('inactive', 'Inactive')}</span></td>
            <td>
                <button class="btn-icon" onclick="showGoldTypeModal(${item.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="disableGoldType(${item.id})"><i class="bi bi-slash-circle"></i></button>
            </td>
        </tr>
    `).join('');

    const purityRows = purities.map(item => `
        <tr>
            <td>${item.key}</td>
            <td>${item.label}</td>
            <td class="num-fmt" data-value="${item.cashback_per_gram || 0}">${fmt(item.cashback_per_gram || 0)}</td>
            <td>${item.order ?? 0}</td>
            <td><span style="color:${item.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}" data-i18n="${item.is_active ? 'active' : 'inactive'}">${item.is_active ? t('active', 'Active') : t('inactive', 'Inactive')}</span></td>
            <td>
                <button class="btn-icon" onclick="showGoldPurityModal(${item.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="disableGoldPurity(${item.id})"><i class="bi bi-slash-circle"></i></button>
            </td>
        </tr>
    `).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:700;color:var(--text-primary)" data-i18n="tab_gold_settings">${t('tab_gold_settings', 'Gold Settings')}</div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="gold_types">${t('gold_types', 'Gold Types')}</div>
                <button class="btn-primary-custom" onclick="showGoldTypeModal(null)" data-i18n="add_gold_type">${t('add_gold_type', 'Add Gold Type')}</button>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="gold_type">${t('gold_type', 'Gold Type')}</th>
                            <th data-i18n="order">${t('order', 'Order')}</th>
                            <th data-i18n="active">${t('active', 'Active')}</th>
                            <th data-i18n="actions">${t('actions', 'Actions')}</th>
                        </tr>
                    </thead>
                    <tbody>${typeRows}</tbody>
                </table>
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="gold_purities">${t('gold_purities', 'Gold Purities')}</div>
                <button class="btn-primary-custom" onclick="showGoldPurityModal(null)" data-i18n="add_gold_purity">${t('add_gold_purity', 'Add Gold Purity')}</button>
            </div>
            <div style="margin-bottom:8px;color:var(--text-muted);font-size:12px;" data-i18n="gold_purities_cashback_hint">${t('gold_purities_cashback_hint', 'Cashback per gram here is used in all gold valuation calculations across the app.')}</div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="gold_purity_key">${t('gold_purity_key', 'Purity Key')}</th>
                            <th data-i18n="gold_purity_label">${t('gold_purity_label', 'Purity Label')}</th>
                            <th data-i18n="cashback_per_gram">${t('cashback_per_gram', 'Cashback per Gram')}</th>
                            <th data-i18n="order">${t('order', 'Order')}</th>
                            <th data-i18n="active">${t('active', 'Active')}</th>
                            <th data-i18n="actions">${t('actions', 'Actions')}</th>
                        </tr>
                    </thead>
                    <tbody>${purityRows}</tbody>
                </table>
            </div>
        </div>
    `;

    applyTranslations();
}

async function showGoldTypeModal(itemId) {
    let item = null;
    if (itemId) {
        const res = await fetch('/api/settings/gold-types/');
        const data = await res.json();
        item = (data.items || []).find(x => x.id === itemId) || null;
    }

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${item ? 'edit_gold_type' : 'add_gold_type'}">${item ? t('edit_gold_type', 'Edit Gold Type') : t('add_gold_type', 'Add Gold Type')}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-7"><label data-i18n="gold_type">${t('gold_type', 'Gold Type')}</label><input type="text" class="form-control" id="gstName" value="${item?.name || ''}"></div>
                <div class="col-3"><label data-i18n="order">${t('order', 'Order')}</label><input type="number" class="form-control" id="gstOrder" value="${item?.order ?? 0}"></div>
                <div class="col-2"><label data-i18n="active">${t('active', 'Active')}</label><select class="form-select" id="gstActive"><option value="true" ${item == null || item.is_active ? 'selected' : ''}>${t('yes', 'Yes')}</option><option value="false" ${item && !item.is_active ? 'selected' : ''}>${t('no', 'No')}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t('btn_cancel', 'Cancel')}</button>
            <button class="btn-primary-custom" onclick="saveGoldType(${itemId || 'null'})" data-i18n="btn_save">${t('btn_save', 'Save')}</button>
        </div>
    `);
    applyTranslations();

    if (window.DocumentManager) {
        window.DocumentManager.init({
            containerId: 'bankDocumentManagerContainer',
            parentType: 'bank',
            parentId: bankId,
            disabledMessage: t('documents_save_first', 'Save this record first to manage documents.'),
        });
    }
}

async function saveGoldType(itemId) {
    const body = {
        name: document.getElementById('gstName').value.trim(),
        order: parseInt(document.getElementById('gstOrder').value) || 0,
        is_active: document.getElementById('gstActive').value === 'true',
    };

    if (!body.name) {
        showToast(t('gold_type_required', 'Gold type name is required'), 'error');
        return;
    }

    const url = itemId ? `/api/settings/gold-types/${itemId}/` : '/api/settings/gold-types/';
    const method = itemId ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (res.ok) {
        closeModal();
        showToast(t('gold_type_saved', 'Gold type saved ✓'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_saving_gold_type', 'Error saving gold type'), 'error');
    }
}

async function disableGoldType(itemId) {
    if (!confirm(t('confirm_disable_gold_type', 'Disable this gold type?'))) return;
    const res = await fetch(`/api/settings/gold-types/${itemId}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('gold_type_disabled', 'Gold type disabled'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_disabling_gold_type', 'Error disabling gold type'), 'error');
    }
}

async function showGoldPurityModal(itemId) {
    let item = null;
    if (itemId) {
        const res = await fetch('/api/settings/gold-purities/');
        const data = await res.json();
        item = (data.items || []).find(x => x.id === itemId) || null;
    }

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${item ? 'edit_gold_purity' : 'add_gold_purity'}">${item ? t('edit_gold_purity', 'Edit Gold Purity') : t('add_gold_purity', 'Add Gold Purity')}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-3"><label data-i18n="gold_purity_key">${t('gold_purity_key', 'Purity Key')}</label><input type="text" class="form-control" id="gspKey" value="${item?.key || ''}" placeholder="24k"></div>
                <div class="col-3"><label data-i18n="gold_purity_label">${t('gold_purity_label', 'Purity Label')}</label><input type="text" class="form-control" id="gspLabel" value="${item?.label || ''}" placeholder="24K"></div>
                <div class="col-3"><label data-i18n="cashback_per_gram">${t('cashback_per_gram', 'Cashback per Gram')}</label><input type="number" step="0.0001" class="form-control" id="gspCashback" value="${item?.cashback_per_gram ?? 0}"></div>
                <div class="col-2"><label data-i18n="order">${t('order', 'Order')}</label><input type="number" class="form-control" id="gspOrder" value="${item?.order ?? 0}"></div>
                <div class="col-1"><label data-i18n="active">${t('active', 'Active')}</label><select class="form-select" id="gspActive"><option value="true" ${item == null || item.is_active ? 'selected' : ''}>${t('yes', 'Yes')}</option><option value="false" ${item && !item.is_active ? 'selected' : ''}>${t('no', 'No')}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t('btn_cancel', 'Cancel')}</button>
            <button class="btn-primary-custom" onclick="saveGoldPurity(${itemId || 'null'})" data-i18n="btn_save">${t('btn_save', 'Save')}</button>
        </div>
    `);
    applyTranslations();
}

async function saveGoldPurity(itemId) {
    const body = {
        key: document.getElementById('gspKey').value.trim().toLowerCase(),
        label: document.getElementById('gspLabel').value.trim(),
        cashback_per_gram: parseFloat(document.getElementById('gspCashback').value) || 0,
        order: parseInt(document.getElementById('gspOrder').value) || 0,
        is_active: document.getElementById('gspActive').value === 'true',
    };

    if (!body.key) {
        showToast(t('gold_purity_key_required', 'Purity key is required'), 'error');
        return;
    }

    if (!body.label) {
        body.label = body.key.toUpperCase();
    }

    const url = itemId ? `/api/settings/gold-purities/${itemId}/` : '/api/settings/gold-purities/';
    const method = itemId ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (res.ok) {
        closeModal();
        showToast(t('gold_purity_saved', 'Gold purity saved ✓'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_saving_gold_purity', 'Error saving gold purity'), 'error');
    }
}

async function disableGoldPurity(itemId) {
    if (!confirm(t('confirm_disable_gold_purity', 'Disable this gold purity?'))) return;
    const res = await fetch(`/api/settings/gold-purities/${itemId}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('gold_purity_disabled', 'Gold purity disabled'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_disabling_gold_purity', 'Error disabling gold purity'), 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// LANGUAGE SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

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
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_languages"></div>
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

async function renderCurrencySettings() {
    const res        = await fetch('/api/currencies/');
    const { currencies = [] } = await res.json();

    const rows = currencies.map(c => `
        <tr>
            <td style="font-size:20px">${c.flag}</td>
            <td><code style="color:var(--accent-primary);font-weight:700">${c.code}</code></td>
            <td>${c.symbol || '—'}</td>
            <td>${c.name}</td>
            <td>
                <button class="btn-icon" onclick="showCurrencyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCurrency(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_currency"></div>
            <button class="btn-primary-custom" onclick="showCurrencyModal(null)" data-i18n="add_currency">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="currency_flag">Flag</th>
                    <th data-i18n="currency_code">Code</th>
                    <th data-i18n="currency_symbol">Symbol</th>
                    <th data-i18n="currency_name">Name</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>
        <div style="margin-top:14px;font-size:13px;color:var(--text-secondary)"
            data-i18n="currency_settings_desc"></div>`;
    applyTranslations();
}

async function showCurrencyModal(currencyId) {
    let c = null;
    if (currencyId) {
        const res = await fetch(`/api/currencies/${currencyId}/`);
        c = await res.json();
    }
    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${c ? 'edit_currency' : 'add_currency'}"></h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-4">
                    <label data-i18n="currency_code">Code</label>
                    <input class="form-control" id="curCode" value="${c?.code || ''}" placeholder="USD">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_symbol">Symbol</label>
                    <input class="form-control" id="curSymbol" value="${c?.symbol || ''}" placeholder="$">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_flag">Flag</label>
                    <input class="form-control" id="curFlag" value="${c?.flag || '💱'}" placeholder="🇺🇸" maxlength="5">
                </div>
                <div class="col-12">
                    <label data-i18n="currency_name">Name</label>
                    <input class="form-control" id="curName" value="${c?.name || ''}" placeholder="US Dollar">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_order">Order</label>
                    <input type="number" class="form-control" id="curOrder" value="${c?.order ?? 0}">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCurrency(${currencyId})" data-i18n="save_button">Save</button>
        </div>`);
    applyTranslations();
}

async function saveCurrency(currencyId) {
    const body = {
        code:   document.getElementById('curCode').value.toUpperCase(),
        symbol: document.getElementById('curSymbol').value,
        flag:   document.getElementById('curFlag').value,
        name:   document.getElementById('curName').value,
        order:  parseInt(document.getElementById('curOrder').value) || 0,
    };
    if (!body.code || !body.name) { showToast('Code and Name are required', 'error'); return; }
    const res = await fetch(currencyId ? `/api/currencies/${currencyId}/` : '/api/currencies/', {
        method:  currencyId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });
    if (res.ok) { closeModal(); showToast('Currency saved ✓'); renderCurrencySettings(); }
    else showToast('Error', 'error');
}

async function deleteCurrency(currencyId) {
    if (!confirm('Delete this currency?')) return;
    const res = await fetch(`/api/currencies/${currencyId}/`, { method: 'DELETE' });
    if (res.ok) { showToast('Deleted'); renderCurrencySettings(); }
    else showToast('Error deleting currency', 'error');
}

// ════════════════════════════════════════════════════════════════════════════
// COMPANY SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderCompanySettings() {
    const res        = await fetch('/api/companies/');
    const { companies = [] } = await res.json();

    const rows = companies.map(c => `
        <tr>
            <td>
                <span style="background:${c.color_hex};width:12px;height:12px;border-radius:3px;
                             display:inline-block;margin-right:8px"></span>${c.name}
            </td>
            <td>${c.display_name}</td>
            <td><span class="group-badge">${c.group_name || '—'}</span></td>
            <td>
                <input type="color" value="${c.color_hex}"
                    onchange="updateCompanyColor(${c.id}, this.value)"
                    style="background:none;border:none;width:32px;height:32px;cursor:pointer">
            </td>
            <td>${c.order}</td>
            <td>
                <span style="color:${c.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}"
                    data-i18n="${c.is_active ? 'active' : 'inactive'}">
                </span>
            </td>
            <td>
                <button class="btn-icon" onclick="showCompanyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCompany(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_companies"></div>
            <button class="btn-primary-custom" onclick="showCompanyModal(null)" data-i18n="btn_add">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="company_name">Name</th>
                    <th data-i18n="company_display_name">Display Name</th>
                    <th data-i18n="group_name">Group</th>
                    <th data-i18n="color">Color</th>
                    <th data-i18n="order">Order</th>
                    <th data-i18n="active">Active</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
}

async function showCompanyModal(companyId) {
    let c = null;
    if (companyId) {
        const res = await fetch(`/api/companies/${companyId}/`);
        c = await res.json();
    }
    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${c ? 'edit_company' : 'add_company'}"></h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="company_name">Name</label>
                    <input class="form-control" id="cName" value="${c?.name || ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="company_display_name">Display Name</label>
                    <input class="form-control" id="cDisplay" value="${c?.display_name || ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="group_name">Group Name</label>
                    <input class="form-control" id="cGroup" value="${c?.group_name || ''}">
                </div>
                <div class="col-3">
                    <label data-i18n="color">Color</label>
                    <input type="color" class="form-control" id="cColor" value="${c?.color_hex || '#0d6efd'}">
                </div>
                <div class="col-3">
                    <label data-i18n="order">Order</label>
                    <input type="number" class="form-control" id="cOrder" value="${c?.order ?? 0}">
                </div>
                <div class="col-12">
                    <label data-i18n="active">Active</label>
                    <select class="form-select" id="cActive">
                        <option value="true"  ${!c || c.is_active  ? 'selected' : ''} data-i18n="active">Active</option>
                        <option value="false" ${c  && !c.is_active ? 'selected' : ''} data-i18n="inactive">Inactive</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCompany(${companyId})" data-i18n="save_button">Save</button>
        </div>`);
    applyTranslations();
}

async function updateCompanyColor(id, color) {
    await fetch(`/api/companies/${id}/`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ color_hex: color }),
    });
    window._companies = (window._companies || []).map(c =>
        c.id === id ? { ...c, color_hex: color } : c);
    renderSidebar();
}

async function saveCompany(companyId) {
    const body = {
        name:         document.getElementById('cName').value,
        display_name: document.getElementById('cDisplay').value,
        group_name:   document.getElementById('cGroup').value,
        color_hex:    document.getElementById('cColor').value,
        order:        parseInt(document.getElementById('cOrder').value) || 0,
        is_active:    document.getElementById('cActive').value === 'true',
    };
    const res = await fetch(companyId ? `/api/companies/${companyId}/` : '/api/companies/', {
        method:  companyId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });
    if (res.ok) {
        closeModal();
        showToast('Company saved ✓');
        const cRes = await fetch('/api/companies/');
        window._companies = (await cRes.json()).companies;
        renderSidebar();
        renderCompanySettings();
    } else showToast('Error', 'error');
}

async function deleteCompany(id) {
    if (!confirm('Delete company? This will also delete all salary entries!')) return;
    await fetch(`/api/companies/${id}/`, { method: 'DELETE' });
    showToast('Deleted');
    const cRes = await fetch('/api/companies/');
    window._companies = (await cRes.json()).companies;
    renderSidebar();
    renderCompanySettings();
}

// ════════════════════════════════════════════════════════════════════════════
// BANK SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderBankSettings() {
    const res   = await fetch('/api/banks/');
    const data  = await res.json();
    window._banks = data.banks;

    const rows = data.banks.map(b => `
        <tr>
            <td>${b.name}</td>
            <td><code style="color:var(--text-muted);font-size:11px">${b.account_number || '—'}</code></td>
            <td><code style="color:var(--text-muted);font-size:11px">${b.swift_code    || '—'}</code></td>
            <td style="color:${b.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}">
                ${b.is_active ? 'Active' : 'Inactive'}
            </td>
            <td>
                <button class="btn-icon" onclick="showBankModal(${b.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBank(${b.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_banks"></div>
            <button class="btn-primary-custom" onclick="showBankModal(null)" data-i18n="btn_add">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="bank_name">Name</th>
                    <th data-i18n="account_number">Account</th>
                    <th data-i18n="swift_code">Swift</th>
                    <th data-i18n="status">Active</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
}

async function showBankModal(bankId) {
    let b = null;
    if (bankId) {
        const res  = await fetch('/api/banks/');
        const data = await res.json();
        b = data.banks.find(x => x.id === bankId);
    }
    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${b ? 'edit_bank' : 'add_bank'}"></h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label data-i18n="bank_name">Bank Name</label>
                    <input class="form-control" id="bnName" value="${b?.name || ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="account_number">Account Number</label>
                    <input class="form-control" id="bnAcct" value="${b?.account_number || ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="card_id">Card ID</label>
                    <input class="form-control" id="bnCard" value="${b?.card_id || ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="swift_code">Swift Code</label>
                    <input class="form-control" id="bnSwift" value="${b?.swift_code || ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="customer_id">Customer ID</label>
                    <input class="form-control" id="bnCustId" value="${b?.customer_id || ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="customer_name">Customer Name</label>
                    <input class="form-control" id="bnCustName" value="${b?.customer_name || ''}">
                </div>
            </div>
            <div class="mt-3" id="bankDocumentManagerContainer"></div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveBank(${bankId})" data-i18n="save_button">Save</button>
        </div>`);
    applyTranslations();

    if (window.DocumentManager) {
        window.DocumentManager.init({
            containerId: 'bankDocumentManagerContainer',
            parentType: 'bank',
            parentId: bankId,
            disabledMessage: t('documents_save_first', 'Save this record first to manage documents.'),
        });
    }
}

async function saveBank(bankId) {
    const body = {
        name:          document.getElementById('bnName').value,
        account_number:document.getElementById('bnAcct').value,
        card_id:       document.getElementById('bnCard').value,
        swift_code:    document.getElementById('bnSwift').value,
        customer_id:   document.getElementById('bnCustId').value,
        customer_name: document.getElementById('bnCustName').value,
    };
    const res = await fetch(bankId ? `/api/banks/${bankId}/` : '/api/banks/', {
        method:  bankId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });
    if (res.ok) { closeModal(); showToast('Bank saved ✓'); renderBankSettings(); }
    else showToast('Error', 'error');
}

async function deleteBank(id) {
    if (!confirm('Delete this bank?')) return;
    await fetch(`/api/banks/${id}/`, { method: 'DELETE' });
    showToast('Deleted');
    renderBankSettings();
}

// ════════════════════════════════════════════════════════════════════════════
// USER MANAGEMENT TAB
// ════════════════════════════════════════════════════════════════════════════

async function renderUserSettings() {
    const mc = document.getElementById('settingsContent');
    const meRes = await fetch('/api/auth/me/');
    const me    = await meRes.json();
    const canManage = me.user?.is_staff || (me.allowed_pages || []).includes('user_management');

    if (!canManage) {
        mc.innerHTML = `<div class="p-4" data-i18n="no_permission">You do not have permission to manage users.</div>`;
        applyTranslations();
        return;
    }
    await loadUsers({ page: 1, pageSize: 10, q: '' });
}

async function loadUsers({ page = 1, pageSize = 10, q = '' } = {}) {
    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_users">Users</div>
            <div style="display:flex;gap:8px">
                <input id="userSearch" class="form-control"
                    data-i18n-placeholder="search_placeholder" value="${q}"
                    style="width:260px" placeholder="Search...">
                <button class="btn-primary-custom" onclick="handleUserSearch()" data-i18n="btn_search">Search</button>
                <button class="btn-primary-custom" onclick="showUserModal(null)" data-i18n="btn_add_user">
                    <i class="bi bi-plus-lg"></i>
                </button>
            </div>
        </div>
        <div style="margin-bottom:8px;display:flex;gap:8px;align-items:center">
            <button class="btn-secondary-custom" onclick="toggleSelectAll()" data-i18n="btn_toggle_select">Toggle Select</button>
            <select id="bulkActionSelect" class="form-select" style="width:220px">
                <option value=""             data-i18n="bulk_actions">Bulk actions</option>
                <option value="activate"     data-i18n="activate_selected">Activate selected</option>
                <option value="deactivate"   data-i18n="deactivate_selected">Deactivate selected</option>
                <option value="delete"       data-i18n="delete_selected">Delete selected</option>
                <option value="set_staff_true"  data-i18n="set_staff">Set staff</option>
                <option value="set_staff_false" data-i18n="unset_staff">Unset staff</option>
            </select>
            <button class="btn-primary-custom" onclick="applyBulkAction()" data-i18n="btn_apply">Apply</button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th></th>
                    <th data-i18n="user_username">Username</th>
                    <th data-i18n="user_email">Email</th>
                    <th data-i18n="user_is_active">Active</th>
                    <th data-i18n="user_roles">Roles</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody id="usersTableBody"></tbody>
            </table>
            </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
            <div id="usersPager"></div>
            <select id="usersPageSize" class="form-select" style="width:80px">
                <option>5</option><option selected>10</option><option>25</option><option>50</option>
            </select>
        </div>`;

    document.getElementById('usersPageSize').value = pageSize;

    const resp = await fetch(`/api/users/?page=${page}&page_size=${pageSize}&q=${encodeURIComponent(q)}`);
    const data = await resp.json();

    document.getElementById('usersTableBody').innerHTML = (data.users || []).map(u => `
        <tr>
            <td><input type="checkbox" class="user-select" data-id="${u.id}"></td>
            <td>${u.username}</td>
            <td>${u.email || '—'}</td>
            <td data-i18n="${u.is_active ? 'user_is_active' : 'user_is_inactive'}"></td>
            <td>
                ${u.is_staff     ? '<span data-i18n="user_is_staff">Staff</span> ' : ''}
                ${u.is_superuser ? '<span data-i18n="user_is_superuser">Superuser</span>' : ''}
            </td>
            <td>
                <button class="btn-icon" onclick="showUserModal(${u.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon" onclick="showPermissionsModal(${u.id})"><i class="bi bi-shield-lock"></i></button>
                <button class="btn-icon del" onclick="deleteUser(${u.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    applyTranslations();
}

async function showUserModal(userId) {
    let u = null;
    if (userId) {
        const res = await fetch(`/api/users/${userId}/`);
        u = (await res.json()).user;
    }
    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${userId ? 'edit_user' : 'add_user'}"></h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label data-i18n="user_username">Username</label>
                    <input class="form-control" id="uName" value="${u?.username || ''}" ${u ? 'disabled' : ''}>
                </div>
                <div class="col-12">
                    <label data-i18n="user_email">Email</label>
                    <input class="form-control" id="uEmail" value="${u?.email || ''}">
                </div>
                <div class="col-12">
                    <label data-i18n="user_password">Password</label>
                    <input type="password" class="form-control" id="uPassword">
                </div>
                <div class="col-6">
                    <label data-i18n="user_is_active">Active</label>
                    <select class="form-select" id="uActive">
                        <option value="true"  ${!u || u.is_active  ? 'selected' : ''} data-i18n="yes">Yes</option>
                        <option value="false" ${u  && !u.is_active ? 'selected' : ''} data-i18n="no">No</option>
                    </select>
                </div>
                <div class="col-6">
                    <label data-i18n="user_is_staff">Staff</label>
                    <select class="form-select" id="uStaff">
                        <option value="false" ${!u?.is_staff ? 'selected' : ''} data-i18n="no">No</option>
                        <option value="true"  ${ u?.is_staff ? 'selected' : ''} data-i18n="yes">Yes</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveUser(${userId})" data-i18n="save_button">Save</button>
        </div>`);
    applyTranslations();
}

async function showPermissionsModal(userId) {
    const res = await fetch(`/api/users/${userId}/permissions/`);
    if (!res.ok) { showToast('Unable to load permissions', 'error'); return; }
    const d = await res.json();

    const rows = (d.permissions || []).map(p => `
        <tr>
            <td>${p.username}</td>
            <td>${p.page}</td>
            <td><button class="btn-icon del" onclick="deletePermission(${p.id})"><i class="bi bi-trash"></i></button></td>
        </tr>`).join('');

    const optHtml = (d.available_pages || []).map(p =>
        `<option value="${p[0]}">${p[1]}</option>`).join('');

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="manage_permissions">Manage Permissions</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <strong data-i18n="existing_permissions">Existing Permissions</strong>
            <div style="max-height:240px;overflow:auto;margin:10px 0">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="user_username">User</th>
                        <th data-i18n="page">Page</th>
                        <th data-i18n="actions">Actions</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
            <hr>
            <div class="row g-3">
                <div class="col-8"><select id="permPage" class="form-select">${optHtml}</select></div>
                <div class="col-4">
                    <button class="btn-primary-custom" onclick="addPermission(${userId})" data-i18n="btn_add">Add</button>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="close_button">Close</button>
        </div>`);
    applyTranslations();
}

function handleUserSearch() {
    loadUsers({
        page:     1,
        pageSize: document.getElementById('usersPageSize').value,
        q:        document.getElementById('userSearch').value,
    });
}

function toggleSelectAll() {
    const boxes = Array.from(document.querySelectorAll('.user-select'));
    const some  = boxes.some(b => !b.checked);
    boxes.forEach(b => b.checked = some);
}

function getSelectedUserIds() {
    return Array.from(document.querySelectorAll('.user-select:checked'))
        .map(cb => parseInt(cb.dataset.id));
}

async function applyBulkAction() {
    const action = document.getElementById('bulkActionSelect').value;
    const ids    = getSelectedUserIds();
    if (!action) { showToast('Choose an action', 'error'); return; }
    if (!ids.length) { showToast('No users selected', 'error'); return; }
    if (action === 'delete' && !confirm(`Delete ${ids.length} selected users?`)) return;

    const payload = { action, ids };
    if (action.startsWith('set_staff')) payload.value = action.endsWith('true');

    try {
        const res = await fetch('/api/users/bulk/', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const d = await res.json();
        if (res.ok) {
            showToast(`${d.changed || 0} users updated`);
            loadUsers({ page: 1, pageSize: document.getElementById('usersPageSize').value,
                        q: document.getElementById('userSearch').value });
        } else showToast(d.error || 'Bulk action failed', 'error');
    } catch (e) { showToast('Network error', 'error'); }
}

async function saveUser(userId) {
    const username = document.getElementById('uName')?.value.trim() || '';
    const email    = document.getElementById('uEmail').value.trim();
    const password = document.getElementById('uPassword').value;

    if (!userId && !username) { showToast('Username required', 'error'); return; }
    if (!email) { showToast('Email required', 'error'); return; }

    const body = {
        username,
        email,
        is_active: document.getElementById('uActive').value === 'true',
        is_staff:  document.getElementById('uStaff').value  === 'true',
    };
    if (password) body.password = password;

    const res = await fetch(userId ? `/api/users/${userId}/` : '/api/users/', {
        method:  userId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });
    if (res.ok) { closeModal(); showToast('User saved ✓'); renderUserSettings(); }
    else { const e = await res.json().catch(() => ({})); showToast(e.error || 'Error saving user', 'error'); }
}

async function deleteUser(id) {
    if (!confirm('Delete user? This cannot be undone.')) return;
    const res = await fetch(`/api/users/${id}/`, { method: 'DELETE' });
    if (res.ok) { showToast('Deleted'); renderUserSettings(); }
    else showToast('Error deleting user', 'error');
}

async function addPermission(userId) {
    const page = document.getElementById('permPage').value;
    const res  = await fetch(`/api/users/${userId}/permissions/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ page }),
    });
    if (res.ok) { showToast('Permission added'); showPermissionsModal(userId); }
    else showToast('Error adding permission', 'error');
}

async function deletePermission(permId) {
    if (!confirm('Remove this permission?')) return;
    const res = await fetch(`/api/users/permissions/${permId}/`, { method: 'DELETE' });
    if (res.ok) { showToast('Removed'); closeModal(); }
    else showToast('Error removing permission', 'error');
}

// ════════════════════════════════════════════════════════════════════════════
// TRANSLATION SETTINGS TAB
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
        <div style="display:flex;justify-content:space-between;align-items:center;
                    margin-bottom:14px;width:100%">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_translations"></div>
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
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_translation_coverage"></div>
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
