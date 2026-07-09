'use strict';

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