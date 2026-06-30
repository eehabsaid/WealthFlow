// cert_status_settings.js — Certificate Status Settings management

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// CERTIFICATE STATUS RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderCertStatusSettings() {
    const res = await fetch('/api/cert-statuses/');
    const data = await res.json();
    const statuses = data.statuses || [];

    const defaultText = t('default', 'Default');
    const terminalYesText = t('terminal_yes', '✓ Terminal');
    const terminalNoText = t('terminal_no', '—');
    const addStatusText = t('add_status', 'Add Status');
    const editText = t('edit', 'Edit');
    const deleteText = t('delete', 'Delete');

    const rows =
        statuses.length === 0
            ? `<tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text-muted)" data-i18n="no_cert_statuses">${t('no_cert_statuses', 'No statuses defined. Add one to get started.')}</td></tr>`
            : statuses
                .map(
                    (s) => `
                <tr>
                    <td>
                        <span style="display:inline-flex;align-items:center;gap:8px">
                            <span style="width:14px;height:14px;border-radius:50%;background:${s.color_hex};flex-shrink:0;display:inline-block"></span>
                            <strong>${esc(s.name)}</strong>
                            ${s.is_default ? `<span style="background:var(--accent-primary);color:#fff;font-size:10px;padding:1px 6px;border-radius:8px" data-i18n="default">${defaultText}</span>` : ''}
                        </span>
                    </td>
                    <td style="font-size:13px;color:var(--text-muted)">${s.color_hex}</td>
                    <td>
                        ${
                            s.is_terminal
                                ? `<span style="color:var(--accent-danger);font-size:12px" data-i18n="terminal_yes">${terminalYesText}</span>`
                                : `<span style="color:var(--text-muted);font-size:12px" data-i18n="terminal_no">${terminalNoText}</span>`
                        }
                    </td>
                    <td style="color:var(--text-muted);font-size:13px">${s.order}</td>
                    <td style="white-space:nowrap">
                        <button class="btn-icon" onclick="showCertStatusModal(${s.id})" title="${editText}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn-icon" onclick="deleteCertStatus(${s.id})" title="${deleteText}"
                            style="color:var(--accent-danger)">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>`,
                )
                .join('');

    const certStatusesTitle = t('cert_statuses', 'Certificate Statuses');
    const certStatusesDesc = t('cert_statuses_desc', 'Define the lifecycle statuses for bank certificates. One status must be set as default.');
    const certStatusHint = t('cert_status_hint', 'These statuses appear in the Certificate form and on the Bank Certificates page. Terminal statuses indicate the certificate lifecycle has ended.');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="cert_statuses">${certStatusesTitle}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="cert_statuses_desc">
                    ${certStatusesDesc}
                </div>
            </div>
            <button class="btn-primary-custom" onclick="showCertStatusModal(null)">
                <i class="bi bi-plus-lg"></i> <span data-i18n="add_status">${addStatusText}</span>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="status_name">${t('status_name', 'Status Name')}</th>
                            <th data-i18n="color">${t('color', 'Color')}</th>
                            <th data-i18n="terminal">${t('terminal', 'Terminal')}</th>
                            <th data-i18n="order">${t('order', 'Order')}</th>
                            <th data-i18n="actions">${t('actions', 'Actions')}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
        <div style="background:var(--bg-tertiary);border:1px solid var(--border-color);border-radius:10px;padding:12px 16px;margin-top:12px;font-size:12px;color:var(--text-muted)">
            <strong>ℹ️ </strong><span data-i18n="cert_status_hint">${certStatusHint}</span>
        </div>`;
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

async function showCertStatusModal(id) {
    let status = null;
    if (id) {
        const res = await fetch('/api/cert-statuses/');
        const data = await res.json();
        status = (data.statuses || []).find((s) => s.id === id);
    }

    const titleText = id ? t('edit_status', 'Edit Status') : t('add_status', 'Add Status');
    const statusNameLabel = t('status_name', 'Status Name');
    const colorLabel = t('color', 'Color');
    const orderLabel = t('order', 'Display Order');
    const defaultCheckbox = t('set_as_default', 'Set as default');
    const terminalCheckbox = t('is_terminal', 'Terminal status');
    const cancelText = t('cancel', 'Cancel');
    const saveText = t('save', 'Save');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title">${titleText}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-8">
                    <label class="form-label" data-i18n="status_name">${statusNameLabel}</label>
                    <input class="form-control" id="csName" value="${status ? esc(status.name) : ''}">
                </div>
                <div class="col-4">
                    <label class="form-label" data-i18n="color">${colorLabel}</label>
                    <input type="color" class="form-control form-control-color w-100" id="csColor"
                        value="${status ? status.color_hex : '#1a6ef5'}">
                </div>
                <div class="col-6">
                    <label class="form-label" data-i18n="order">${orderLabel}</label>
                    <input type="number" class="form-control" id="csOrder"
                        value="${status ? status.order : 0}" min="0">
                </div>
                <div class="col-6" style="display:flex;flex-direction:column;justify-content:flex-end;gap:8px;padding-bottom:4px">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                        <input type="checkbox" id="csDefault" ${status && status.is_default ? 'checked' : ''}>
                        <span data-i18n="set_as_default">${defaultCheckbox}</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                        <input type="checkbox" id="csTerminal" ${status && status.is_terminal ? 'checked' : ''}>
                        <span data-i18n="is_terminal">${terminalCheckbox}</span>
                    </label>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveCertStatus(${id || 'null'})" data-i18n="save">${saveText}</button>
        </div>`;
    showModal(html);
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & DELETE
// ════════════════════════════════════════════════════════════════════════════

async function saveCertStatus(id) {
    const body = {
        name: document.getElementById('csName').value.trim(),
        color_hex: document.getElementById('csColor').value,
        order: parseInt(document.getElementById('csOrder').value) || 0,
        is_default: document.getElementById('csDefault').checked,
        is_terminal: document.getElementById('csTerminal').checked,
    };
    if (!body.name) {
        showToast(t('name_required', 'Name is required'), 'error');
        return;
    }

    const url = id ? `/api/cert-statuses/${id}/` : '/api/cert-statuses/';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (res.ok) {
        closeModal();
        showToast(t('status_saved', 'Status saved ✓'), 'success');
        renderCertStatusSettings();
        // Refresh cert status dropdown in any open cert forms
        _refreshCertStatusOptions();
    } else {
        const d = await res.json().catch(() => ({}));
        showToast(d.error || t('error_saving', 'Error saving'), 'error');
    }
}

async function deleteCertStatus(id) {
    const confirmMsg = t('confirm_delete_status', 'Delete this status?');
    if (!confirm(confirmMsg)) return;
    const res = await fetch(`/api/cert-statuses/${id}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('status_deleted', 'Status deleted'), 'success');
        renderCertStatusSettings();
    }
}

// ════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════

async function _refreshCertStatusOptions() {
    // If a cert form is open, refresh its status dropdown
    const select = document.getElementById('certStatus');
    if (!select) return;
    const res = await fetch('/api/cert-statuses/');
    const data = await res.json();
    const current = select.value;
    select.innerHTML = (data.statuses || [])
        .map(
            (s) =>
                `<option value="${s.name}" ${s.name === current ? 'selected' : ''}>${s.name}</option>`,
        )
        .join('');
}

function esc(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
