// settings_extensions.js — Settings tabs for Features 1,2,3,4,7

// ── Notifications Settings Tab ───────────────────────────────
async function renderNotificationSettings() {
    const [rulesRes, appRes] = await Promise.all([
        fetch('/api/reminder-rules/'),
        fetch('/api/settings/'),
    ]);
    const rulesData = await rulesRes.json();
    const appData   = await appRes.json();
    const rules     = rulesData.rules || [];
    const settings  = appData.settings || {};

    const notifsEnabled = settings.notifications_enabled !== 'false';

    const ruleRows = rules.length === 0
        ? `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted)" data-i18n="no_rules">No reminder rules configured</td></tr>`
        : rules.map(r => `
            <tr>
                <td>${escS(r.name)}</td>
                <td>${r.rule_type}</td>
                <td>${r.days_before} days</td>
                <td><span style="color:${r.is_active?'var(--accent-green)':'var(--text-muted)'};font-weight:600">${r.is_active ? t('active','Active') : t('inactive','Inactive')}</span></td>
                <td>
                    <button class="btn-icon" onclick="showReminderRuleModal(${r.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon del" onclick="deleteReminderRule(${r.id})"><i class="bi bi-trash"></i></button>
                </td>
            </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <!-- Global toggle -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;margin-bottom:20px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-weight:700;color:var(--text-primary)" data-i18n="notif_global_enable">Enable Notifications</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="notif_global_enable_desc">Master switch for all notifications and reminders</div>
                </div>
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                    <input type="checkbox" id="notifsEnabled" ${notifsEnabled ? 'checked' : ''}
                        onchange="saveNotifSetting('notifications_enabled', this.checked ? 'true' : 'false')">
                    <span data-i18n="enabled">Enabled</span>
                </label>
            </div>
        </div>

        <!-- Reminder Rules -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-weight:700;color:var(--text-primary)" data-i18n="reminder_rules">Reminder Rules</div>
            <button class="btn-primary-custom" onclick="showReminderRuleModal(null)">
                <i class="bi bi-plus-lg"></i> <span data-i18n="add_rule">Add Rule</span>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="rule_name">Name</th>
                    <th data-i18n="rule_type">Type</th>
                    <th data-i18n="days_before">Days Before</th>
                    <th data-i18n="status">Status</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${ruleRows}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
}

async function saveNotifSetting(key, value) {
    await fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: value }),
    });
    showToast(t('settings_saved', 'Settings saved ✓'));
}

function showReminderRuleModal(id) {
    let rule = null;
    const fetchRule = id
        ? fetch('/api/reminder-rules/').then(r=>r.json()).then(d=>{ rule = (d.rules||[]).find(r=>r.id===id); })
        : Promise.resolve();

    fetchRule.then(() => {
        const html = `
            <div class="modal-header">
                <h5 class="modal-title" data-i18n="reminder_rule">${id ? t('edit_rule','Edit Rule') : t('add_rule','Add Rule')}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-12">
                        <label data-i18n="rule_name">Rule Name</label>
                        <input class="form-control" id="rrName" value="${rule ? escS(rule.name) : ''}">
                    </div>
                    <div class="col-6">
                        <label data-i18n="rule_type">Type</label>
                        <select class="form-select" id="rrType">
                            <option value="cert_maturity" ${(!rule||rule.rule_type==='cert_maturity')?'selected':''}>Certificate Maturity</option>
                            <option value="salary_reminder" ${(rule&&rule.rule_type==='salary_reminder')?'selected':''}>Salary Reminder</option>
                            <option value="custom" ${(rule&&rule.rule_type==='custom')?'selected':''}>Custom</option>
                        </select>
                    </div>
                    <div class="col-6">
                        <label data-i18n="days_before">Days Before Event</label>
                        <input type="number" class="form-control" id="rrDays" value="${rule ? rule.days_before : 30}" min="1">
                    </div>
                    <div class="col-12">
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                            <input type="checkbox" id="rrActive" ${!rule||rule.is_active?'checked':''}>
                            <span data-i18n="rule_active">Active</span>
                        </label>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
                <button class="btn-primary-custom" onclick="saveReminderRule(${id||'null'})" data-i18n="save">Save</button>
            </div>`;
        showModal(html);
    });
}

async function saveReminderRule(id) {
    const body = {
        name:        document.getElementById('rrName').value.trim(),
        rule_type:   document.getElementById('rrType').value,
        days_before: parseInt(document.getElementById('rrDays').value) || 30,
        is_active:   document.getElementById('rrActive').checked,
    };
    const url    = id ? `/api/reminder-rules/${id}/` : '/api/reminder-rules/';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if (res.ok) {
        closeModal();
        showToast(t('rule_saved','Rule saved ✓'));
        renderNotificationSettings();
    } else {
        const d = await res.json();
        showToast(d.error || t('error_generic','Error'), 'error');
    }
}

async function deleteReminderRule(id) {
    if (!confirm(t('confirm_delete','Delete this rule?'))) return;
    const res = await fetch(`/api/reminder-rules/${id}/`, { method: 'DELETE' });
    if (res.ok) { showToast(t('deleted','Deleted')); renderNotificationSettings(); }
    else showToast(t('error_generic','Error'), 'error');
}


// ── Certificate Status Settings Tab ──────────────────────────
async function renderCertificateSettings() {
    const res = await fetch('/api/certificate-statuses/');
    const data = await res.json();
    const statuses = data.statuses || [];

    const rows = statuses.length === 0
        ? `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted)" data-i18n="no_statuses">No statuses configured</td></tr>`
        : statuses.map(s => `
            <tr>
                <td><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${s.color_hex};margin-right:8px"></span>${escS(s.name)}</td>
                <td>${s.is_terminal ? '✓ Terminal' : '—'}</td>
                <td>${s.order}</td>
                <td>
                    <button class="btn-icon" onclick="showCertStatusModal(${s.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon del" onclick="deleteCertStatus(${s.id})"><i class="bi bi-trash"></i></button>
                </td>
            </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="cert_statuses">Certificate Statuses</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="cert_statuses_desc">Define lifecycle statuses for bank certificates</div>
            </div>
            <button class="btn-primary-custom" onclick="showCertStatusModal(null)">
                <i class="bi bi-plus-lg"></i> <span data-i18n="add_status">Add Status</span>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="status_name">Status Name</th>
                    <th data-i18n="terminal">Terminal</th>
                    <th data-i18n="order">Order</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
}

function showCertStatusModal(id) {
    const fetchData = id
        ? fetch('/api/certificate-statuses/').then(r=>r.json()).then(d=>d.statuses||[])
        : Promise.resolve([]);

    fetchData.then(statuses => {
        const s = id ? statuses.find(x => x.id === id) : null;
        const html = `
            <div class="modal-header">
                <h5 class="modal-title">${id ? t('edit_status','Edit Status') : t('add_status','Add Status')}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-8">
                        <label data-i18n="status_name">Status Name</label>
                        <input class="form-control" id="csName" value="${s ? escS(s.name) : ''}">
                    </div>
                    <div class="col-4">
                        <label data-i18n="color">Color</label>
                        <input type="color" class="form-control" id="csColor" value="${s ? s.color_hex : '#0d6efd'}">
                    </div>
                    <div class="col-6">
                        <label data-i18n="order">Order</label>
                        <input type="number" class="form-control" id="csOrder" value="${s ? s.order : 0}" min="0">
                    </div>
                    <div class="col-6" style="display:flex;align-items:flex-end">
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding-bottom:8px">
                            <input type="checkbox" id="csTerminal" ${s && s.is_terminal ? 'checked' : ''}>
                            <span data-i18n="is_terminal">Terminal (end-of-life)</span>
                        </label>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
                <button class="btn-primary-custom" onclick="saveCertStatus(${id||'null'})" data-i18n="save">Save</button>
            </div>`;
        showModal(html);
    });
}

async function saveCertStatus(id) {
    const body = {
        name:        document.getElementById('csName').value.trim(),
        color_hex:   document.getElementById('csColor').value,
        order:       parseInt(document.getElementById('csOrder').value) || 0,
        is_terminal: document.getElementById('csTerminal').checked,
    };
    const url = id ? `/api/certificate-statuses/${id}/` : '/api/certificate-statuses/';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if (res.ok) {
        closeModal();
        showToast(t('status_saved','Status saved ✓'));
        renderCertificateSettings();
    } else {
        const d = await res.json();
        showToast(d.error || t('error_generic','Error'), 'error');
    }
}

async function deleteCertStatus(id) {
    if (!confirm(t('confirm_delete','Delete this status?'))) return;
    const res = await fetch(`/api/certificate-statuses/${id}/`, { method: 'DELETE' });
    if (res.ok) { showToast(t('deleted','Deleted')); renderCertificateSettings(); }
    else showToast(t('error_generic','Error'), 'error');
}


// ── Audit Settings Tab ────────────────────────────────────────
async function renderAuditSettings() {
    const res = await fetch('/api/settings/');
    const data = await res.json();
    const s = data.settings || {};

    document.getElementById('settingsContent').innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:24px;display:flex;flex-direction:column;gap:20px">
            <div>
                <div style="font-weight:700;color:var(--text-primary);margin-bottom:16px" data-i18n="audit_settings">Audit Log Settings</div>

                <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border-color)">
                    <div>
                        <div style="font-weight:600;color:var(--text-primary)" data-i18n="audit_enabled">Enable Audit Logging</div>
                        <div style="font-size:12px;color:var(--text-muted)" data-i18n="audit_enabled_desc">Track create/update/delete/login actions</div>
                    </div>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                        <input type="checkbox" id="auditEnabled" ${s.audit_enabled !== 'false' ? 'checked' : ''}
                            onchange="saveNotifSetting('audit_enabled', this.checked ? 'true' : 'false')">
                        <span data-i18n="enabled">Enabled</span>
                    </label>
                </div>

                <div style="padding:12px 0;border-bottom:1px solid var(--border-color)">
                    <div style="font-weight:600;color:var(--text-primary);margin-bottom:6px" data-i18n="audit_retention">Log Retention (days)</div>
                    <div style="display:flex;gap:10px;align-items:center">
                        <input type="number" id="auditRetention" class="form-control" style="width:120px"
                            value="${s.audit_retention_days || 90}" min="7">
                        <button class="btn-secondary-custom" onclick="saveNotifSetting('audit_retention_days', document.getElementById('auditRetention').value)" data-i18n="save">Save</button>
                    </div>
                </div>

                <div style="padding:12px 0">
                    <div style="font-weight:600;color:var(--text-primary);margin-bottom:6px" data-i18n="audit_disabled_models">Exclude Models from Logging</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px" data-i18n="audit_disabled_models_desc">Comma-separated model names to exclude (e.g. ExchangeRate,GoldPrice)</div>
                    <div style="display:flex;gap:10px;align-items:center">
                        <input class="form-control" id="auditDisabled" value="${s.audit_disabled_models || ''}" style="max-width:340px" placeholder="ExchangeRate,GoldPrice">
                        <button class="btn-secondary-custom" onclick="saveNotifSetting('audit_disabled_models', document.getElementById('auditDisabled').value)" data-i18n="save">Save</button>
                    </div>
                </div>
            </div>
        </div>`;
    applyTranslations();
}


// ── Security Settings Tab ─────────────────────────────────────
async function renderSecuritySettings() {
    const res = await fetch('/api/settings/');
    const data = await res.json();
    const s = data.settings || {};

    document.getElementById('settingsContent').innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:24px;display:flex;flex-direction:column;gap:0">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:20px" data-i18n="security_settings">Security Settings</div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
                <div>
                    <div style="font-weight:600;color:var(--text-primary);margin-bottom:14px" data-i18n="password_policy">Password Policy</div>
                    <div style="display:flex;flex-direction:column;gap:12px">
                        <div>
                            <label style="font-size:12px;color:var(--text-muted)" data-i18n="pwd_min_length">Minimum Length</label>
                            <div style="display:flex;gap:8px;margin-top:4px">
                                <input type="number" id="pwdMinLen" class="form-control" value="${s.password_min_length || 8}" min="6" style="width:90px">
                                <button class="btn-secondary-custom" onclick="saveNotifSetting('password_min_length', document.getElementById('pwdMinLen').value)" data-i18n="save">Save</button>
                            </div>
                        </div>
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                            <input type="checkbox" ${s.password_require_upper==='true'?'checked':''}
                                onchange="saveNotifSetting('password_require_upper', this.checked?'true':'false')">
                            <span data-i18n="pwd_require_upper">Require uppercase letter</span>
                        </label>
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                            <input type="checkbox" ${s.password_require_digit==='true'?'checked':''}
                                onchange="saveNotifSetting('password_require_digit', this.checked?'true':'false')">
                            <span data-i18n="pwd_require_digit">Require digit</span>
                        </label>
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                            <input type="checkbox" ${s.password_require_special==='true'?'checked':''}
                                onchange="saveNotifSetting('password_require_special', this.checked?'true':'false')">
                            <span data-i18n="pwd_require_special">Require special character</span>
                        </label>
                    </div>
                </div>
                <div>
                    <div style="font-weight:600;color:var(--text-primary);margin-bottom:14px" data-i18n="login_security">Login Security</div>
                    <div style="display:flex;flex-direction:column;gap:12px">
                        <div>
                            <label style="font-size:12px;color:var(--text-muted)" data-i18n="session_timeout">Session Timeout (minutes, 0=never)</label>
                            <div style="display:flex;gap:8px;margin-top:4px">
                                <input type="number" id="sessionTimeout" class="form-control" value="${s.session_timeout_minutes || 0}" min="0" style="width:100px">
                                <button class="btn-secondary-custom" onclick="saveNotifSetting('session_timeout_minutes', document.getElementById('sessionTimeout').value)" data-i18n="save">Save</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    applyTranslations();
}


// ── Dashboard Settings Tab ────────────────────────────────────
async function renderDashboardSettings() {
    const res = await fetch('/api/dashboard-preferences/');
    const data = await res.json();
    const available = data.available_widgets || [];
    const config    = data.config  || {};
    const saved     = config.widgets || [];

    // Merge available with saved order/visibility
    const widgets = available.map(w => {
        const saved_w = saved.find(s => s.id === w.id);
        return saved_w ? { ...w, ...saved_w } : w;
    }).sort((a, b) => (a.order || 0) - (b.order || 0));

    const rows = widgets.map((w, i) => `
        <tr id="dw_${w.id}">
            <td style="cursor:grab;color:var(--text-muted)">⠿</td>
            <td>${w.icon || '📊'} ${w.label}</td>
            <td>
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                    <input type="checkbox" onchange="toggleWidget('${w.id}', this.checked)" ${w.visible !== false ? 'checked' : ''}>
                    <span data-i18n="visible">Visible</span>
                </label>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="margin-bottom:14px">
            <div style="font-weight:700;color:var(--text-primary)" data-i18n="dashboard_widgets">Dashboard Widgets</div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:4px" data-i18n="dashboard_widgets_desc">Show or hide widgets on your dashboard</div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th style="width:40px"></th>
                    <th data-i18n="widget">Widget</th>
                    <th data-i18n="visibility">Visibility</th>
                </tr></thead>
                <tbody id="dashWidgetsBody">${rows}</tbody>
            </table>
            </div>
        </div>
        <div style="margin-top:12px;display:flex;justify-content:flex-end">
            <button class="btn-secondary-custom" onclick="resetDashboardWidgets()" data-i18n="reset_defaults">Reset to Defaults</button>
        </div>`;
    applyTranslations();
    window._dashWidgets = widgets;
}

async function toggleWidget(id, visible) {
    if (!window._dashWidgets) return;
    const w = window._dashWidgets.find(w => w.id === id);
    if (w) w.visible = visible;
    await _saveDashWidgets();
    showToast(t('widget_updated','Widget updated ✓'));
}

async function _saveDashWidgets() {
    await fetch('/api/dashboard-preferences/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: { widgets: window._dashWidgets || [] } }),
    });
}

async function resetDashboardWidgets() {
    await fetch('/api/dashboard-preferences/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: {} }),
    });
    showToast(t('reset_done','Dashboard reset to defaults ✓'));
    renderDashboardSettings();
}

function escS(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
