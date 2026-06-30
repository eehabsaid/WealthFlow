// reminders.js — Reminder Engine management

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// REMINDER BANNER
// ════════════════════════════════════════════════════════════════════════════

// ── Check reminders on app load, show banner if any due ──────
async function checkReminders() {
    try {
        const enabled = await _getReminderSetting();
        if (!enabled) return;
        const res = await fetch('/api/reminders/check/');
        if (!res.ok) return;
        const data = await res.json();
        if (data.count > 0) {
            _showReminderBanner(data.reminders);
        }
    } catch (e) {}
}

function _showReminderBanner(reminders) {
    const existing = document.getElementById('reminder-banner');
    if (existing) existing.remove();

    const viewText = t('view', 'View');
    const remindersTitle = t('reminders_due', 'Reminders');

    const items = reminders
        .slice(0, 5)
        .map(
            (r) => `
            <div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.1)">
                <span style="font-size:16px">${_reminderIcon(r.rule_type)}</span>
                <div style="flex:1">
                    <div style="font-weight:600;font-size:13px">${esc(r.rule_name)}</div>
                    <div style="font-size:12px;opacity:0.85">${esc(r.message)}</div>
                </div>
                ${r.link ? `<button onclick="navigate('${r.link}');dismissReminderBanner()" style="background:rgba(255,255,255,0.15);border:none;color:#fff;border-radius:6px;padding:3px 8px;font-size:11px;cursor:pointer" data-i18n="view">${viewText}</button>` : ''}
            </div>`,
        )
        .join('');

    const more =
        reminders.length > 5
            ? `<div style="font-size:12px;opacity:0.7;padding-top:6px">+${reminders.length - 5} ${t('more_reminders', 'more reminder(s)')}</div>`
            : '';

    const banner = document.createElement('div');
    banner.id = 'reminder-banner';
    banner.style.cssText = `position:fixed;top:60px;right:16px;width:340px;background:var(--accent-primary);
        color:#fff;border-radius:12px;padding:14px 16px;z-index:1100;
        box-shadow:0 8px 32px rgba(0,0,0,0.4);animation:slideInRight 0.3s ease`;
    banner.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <span style="font-weight:700;font-size:14px">🔔 ${remindersTitle} (${reminders.length})</span>
            <button onclick="dismissReminderBanner()" style="background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1">×</button>
        </div>
        ${items}${more}`;
    document.body.appendChild(banner);

    // Auto-dismiss after 15 seconds
    setTimeout(dismissReminderBanner, 15000);
}

function dismissReminderBanner() {
    const b = document.getElementById('reminder-banner');
    if (b) b.remove();
}

function _reminderIcon(type) {
    return (
        {
            cert_maturity: '🏦',
            salary_unpaid: '💰',
            salary_day: '📅',
            custom: '📌',
        }[type] || '🔔'
    );
}

async function _getReminderSetting() {
    try {
        const res = await fetch('/api/settings/');
        const d = await res.json();
        return (d.settings || {}).reminder_check_enabled !== 'false';
    } catch (e) {
        return true;
    }
}

// ════════════════════════════════════════════════════════════════════════════
// REMINDER SETTINGS PAGE
// ════════════════════════════════════════════════════════════════════════════

async function renderReminderSettings() {
    const [rulesRes, settingsRes] = await Promise.all([
        fetch('/api/reminders/'),
        fetch('/api/settings/'),
    ]);
    const rulesData = await rulesRes.json();
    const settingsData = await settingsRes.json();
    const rules = rulesData.rules || [];
    const ruleTypes = rulesData.rule_types || [];
    const triggers = rulesData.salary_triggers || [];
    const s = settingsData.settings || {};

    const enabledText = t('enabled', 'Enabled');
    const editText = t('edit', 'Edit');
    const deleteText = t('delete', 'Delete');
    const activeText = t('active', 'Active');
    const inactiveText = t('inactive', 'Inactive');
    const noRulesText = t('no_reminder_rules', 'No reminder rules. Add one to get started.');

    const rows =
        rules.length === 0
            ? `<tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text-muted)" data-i18n="no_reminder_rules">${noRulesText}</td></tr>`
            : rules
                  .map(
                      (r) => `
                <tr>
                    <td>
                        <span style="font-weight:600;color:var(--text-primary)">${esc(r.name)}</span>
                    </td>
                    <td>
                        <span style="background:var(--bg-tertiary);padding:2px 8px;border-radius:8px;font-size:12px">
                            ${esc(r.rule_type_label)}
                        </span>
                    </td>
                    <td style="font-size:13px;color:var(--text-secondary)">
                        ${_ruleSummary(r)}
                    </td>
                    <td>
                        <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                            <input type="checkbox" ${r.is_active ? 'checked' : ''}
                                onchange="toggleReminderRule(${r.id}, this.checked)">
                            <span style="font-size:12px;color:${r.is_active ? 'var(--accent-green)' : 'var(--text-muted)'}"
                                data-i18n="${r.is_active ? 'active' : 'inactive'}">${r.is_active ? activeText : inactiveText}</span>
                        </label>
                    </td>
                    <td style="white-space:nowrap">
                        <button class="btn-icon" onclick="showReminderRuleModal(${r.id})" title="${editText}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn-icon" onclick="deleteReminderRule(${r.id})" title="${deleteText}"
                            style="color:var(--accent-danger)">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>`,
                  )
                  .join('');

    const remindersEnabledTitle = t('reminders_enabled', 'Enable Reminder Engine');
    const remindersEnabledDesc = t('reminders_enabled_desc', 'Show reminder banners on page load when rules are due');
    const certExpiryTitle = t('cert_expiry_window', 'Certificate Expiry Warning Window');
    const certExpiryDesc = t('cert_expiry_window_desc', 'Show expiring certificates on dashboard within this many days');
    const saveText = t('save', 'Save');
    const reminderRulesTitle = t('reminder_rules', 'Reminder Rules');
    const addRuleText = t('add_rule', 'Add Rule');
    const ruleNameHeader = t('rule_name', 'Rule Name');
    const ruleTypeHeader = t('rule_type', 'Type');
    const triggerHeader = t('trigger', 'Trigger');
    const statusHeader = t('status', 'Status');
    const actionsHeader = t('actions', 'Actions');

    document.getElementById('settingsContent').innerHTML = `
        <!-- Global toggle -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="reminders_enabled">${remindersEnabledTitle}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="reminders_enabled_desc">${remindersEnabledDesc}</div>
            </div>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                <input type="checkbox" id="reminderEnabled"
                    ${s.reminder_check_enabled !== 'false' ? 'checked' : ''}
                    onchange="saveAppSetting('reminder_check_enabled', this.checked ? 'true' : 'false')">
                <span data-i18n="enabled">${enabledText}</span>
            </label>
        </div>

        <!-- Cert expiry warning window -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="cert_expiry_window">${certExpiryTitle}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="cert_expiry_window_desc">${certExpiryDesc}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                <input type="number" id="certExpiryDays" class="form-control" style="width:90px"
                    value="${s.cert_expiry_warning_days || 30}" min="1" max="365">
                <button class="btn-secondary-custom" onclick="saveAppSetting('cert_expiry_warning_days', document.getElementById('certExpiryDays').value)" data-i18n="save">${saveText}</button>
            </div>
        </div>

        <!-- Rules table -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div style="font-weight:700;color:var(--text-primary)" data-i18n="reminder_rules">${reminderRulesTitle}</div>
            <button class="btn-primary-custom" onclick="showReminderRuleModal(null)">
                <i class="bi bi-plus-lg"></i> <span data-i18n="add_rule">${addRuleText}</span>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="rule_name">${ruleNameHeader}</th>
                            <th data-i18n="rule_type">${ruleTypeHeader}</th>
                            <th data-i18n="trigger">${triggerHeader}</th>
                            <th data-i18n="status">${statusHeader}</th>
                            <th data-i18n="actions">${actionsHeader}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// RULE UTILITIES & MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

function _ruleSummary(r) {
    if (r.rule_type === 'cert_maturity') {
        return `${r.days_before} ${t('days_before_expiry', 'days before expiry')}`;
    }
    const triggerLabel = r.salary_trigger_label || r.salary_trigger;
    return `${triggerLabel}: ${r.salary_day}`;
}

async function toggleReminderRule(id, active) {
    await fetch(`/api/reminders/${id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: active }),
    });
    showToast(
        active
            ? t('rule_enabled', 'Rule enabled')
            : t('rule_disabled', 'Rule disabled'),
        'success',
    );
    renderReminderSettings();
}

async function deleteReminderRule(id) {
    if (!confirm(t('confirm_delete_rule', 'Delete this reminder rule?'))) return;
    const res = await fetch(`/api/reminders/${id}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('rule_deleted', 'Rule deleted'), 'success');
        renderReminderSettings();
    }
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

async function showReminderRuleModal(id) {
    const rulesRes = await fetch('/api/reminders/');
    const rulesData = await rulesRes.json();
    const rule = id ? (rulesData.rules || []).find((r) => r.id === id) : null;
    const ruleTypes = rulesData.rule_types || [];
    const triggers = rulesData.salary_triggers || [];

    const typeOpts = ruleTypes
        .map(
            (rt) =>
                `<option value="${rt.value}" ${rule && rule.rule_type === rt.value ? 'selected' : ''}>${rt.label}</option>`,
        )
        .join('');

    const triggerOpts = triggers
        .map(
            (tr) =>
                `<option value="${tr.value}" ${rule && rule.salary_trigger === tr.value ? 'selected' : ''}>${tr.label}</option>`,
        )
        .join('');

    const isCert = !rule || rule.rule_type === 'cert_maturity';

    const titleText = id ? t('edit_rule', 'Edit Rule') : t('add_rule', 'Add Rule');
    const ruleNameLabel = t('rule_name', 'Rule Name');
    const ruleTypeLabel = t('rule_type', 'Rule Type');
    const daysBeforeLabel = t('days_before_expiry', 'Days Before Expiry');
    const daysBeforeHint = t('days_before_expiry_hint', 'Reminder fires this many days before the certificate expires');
    const salaryTriggerLabel = t('salary_trigger', 'Trigger Type');
    const triggerValueLabel = t('trigger_value', 'Trigger Value (day number)');
    const messageLabel = t('reminder_message', 'Reminder Message');
    const activeLabel = t('rule_active', 'Active (enabled)');
    const cancelText = t('cancel', 'Cancel');
    const saveText = t('save', 'Save');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title">${titleText}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label class="form-label" data-i18n="rule_name">${ruleNameLabel}</label>
                    <input class="form-control" id="rrName" value="${rule ? esc(rule.name) : ''}">
                </div>
                <div class="col-12">
                    <label class="form-label" data-i18n="rule_type">${ruleTypeLabel}</label>
                    <select class="form-select" id="rrType" onchange="toggleRuleFields()">
                        ${typeOpts}
                    </select>
                </div>

                <!-- Certificate fields -->
                <div id="certFields" class="col-12" ${isCert ? '' : 'style="display:none"'}>
                    <label class="form-label" data-i18n="days_before_expiry">${daysBeforeLabel}</label>
                    <input type="number" class="form-control" id="rrDaysBefore"
                        value="${rule ? rule.days_before : 30}" min="1">
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px" data-i18n="days_before_expiry_hint">${daysBeforeHint}</div>
                </div>

                <!-- Salary fields -->
                <div id="salaryFields" ${!isCert ? '' : 'style="display:none"'}>
                    <div class="row g-3">
                        <div class="col-6">
                            <label class="form-label" data-i18n="salary_trigger">${salaryTriggerLabel}</label>
                            <select class="form-select" id="rrTrigger">
                                ${triggerOpts}
                            </select>
                        </div>
                        <div class="col-6">
                            <label class="form-label" data-i18n="trigger_value">${triggerValueLabel}</label>
                            <input type="number" class="form-control" id="rrSalaryDay"
                                value="${rule ? rule.salary_day : 25}" min="1" max="31">
                        </div>
                        <div class="col-12">
                            <label class="form-label" data-i18n="reminder_message">${messageLabel}</label>
                            <input class="form-control" id="rrMessage"
                                value="${rule ? esc(rule.salary_message) : ''}">
                        </div>
                    </div>
                </div>

                <div class="col-12">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                        <input type="checkbox" id="rrActive" ${!rule || rule.is_active ? 'checked' : ''}>
                        <span data-i18n="rule_active">${activeLabel}</span>
                    </label>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveReminderRule(${id || 'null'})" data-i18n="save">${saveText}</button>
        </div>`;
    showModal(html);
    applyTranslations();
}

function toggleRuleFields() {
    const type = document.getElementById('rrType').value;
    const isCert = type === 'cert_maturity';
    document.getElementById('certFields').style.display = isCert ? '' : 'none';
    document.getElementById('salaryFields').style.display = isCert ? 'none' : '';
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & SETTINGS
// ════════════════════════════════════════════════════════════════════════════

async function saveReminderRule(id) {
    const type = document.getElementById('rrType').value;
    const body = {
        name: document.getElementById('rrName').value.trim(),
        rule_type: type,
        is_active: document.getElementById('rrActive').checked,
        days_before: parseInt(document.getElementById('rrDaysBefore')?.value) || 30,
        salary_trigger:
            document.getElementById('rrTrigger')?.value || 'day_of_month',
        salary_day: parseInt(document.getElementById('rrSalaryDay')?.value) || 25,
        salary_message: document.getElementById('rrMessage')?.value || '',
    };
    if (!body.name) {
        showToast(t('name_required', 'Name is required'), 'error');
        return;
    }

    const url = id ? `/api/reminders/${id}/` : '/api/reminders/';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (res.ok) {
        closeModal();
        showToast(t('rule_saved', 'Rule saved ✓'), 'success');
        renderReminderSettings();
    } else {
        const d = await res.json().catch(() => ({}));
        showToast(d.error || t('error_saving', 'Error saving'), 'error');
    }
}

async function saveAppSetting(key, value) {
    await fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            key: key,     // Matches backend data["key"]
            value: value  // Matches backend data["value"]
        }),
    });
    showToast(t('settings_saved', 'Settings saved ✓'), 'success');
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════

function esc(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
