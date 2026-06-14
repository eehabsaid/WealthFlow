// audit_log.js — Audit Log page (Feature 3)

let _auditPage = 1;
let _auditFilters = {};

async function renderAuditLog() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';
    await _loadAuditLog(1, {});
}

async function _loadAuditLog(page, filters) {
    _auditPage = page;
    _auditFilters = filters;

    const params = new URLSearchParams({ page, per_page: 50, ...filters });
    const res = await fetch('/api/audit-log/?' + params);
    if (!res.ok) {
        document.getElementById('main-content').innerHTML =
            `<div style="color:var(--accent-danger);padding:32px" data-i18n="access_denied">Access denied.</div>`;
        return;
    }
    const data = await res.json();
    const logs = data.logs || [];

    const actionColors = {
        create: 'var(--accent-green)', update: 'var(--accent-yellow)',
        delete: 'var(--accent-danger)', login: 'var(--accent-primary)',
        logout: 'var(--text-muted)', export: 'var(--accent-purple)',
        other:  'var(--text-secondary)',
    };

    const rows = logs.length === 0
        ? `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)" data-i18n="no_records">No records found</td></tr>`
        : logs.map(l => `
            <tr>
                <td style="color:var(--text-muted);font-size:11px;white-space:nowrap">${l.timestamp}</td>
                <td><strong>${esc(l.username)}</strong></td>
                <td><span style="color:${actionColors[l.action]||'var(--text-primary)'};font-weight:600;text-transform:uppercase;font-size:11px">${l.action}</span></td>
                <td style="color:var(--text-secondary)">${esc(l.model_name)}</td>
                <td>${l.object_id || '—'}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--text-secondary)" title="${esc(l.object_repr)}">${esc(l.object_repr)}</td>
                <td style="color:var(--text-muted);font-size:11px">${esc(l.ip_address)}</td>
            </tr>`).join('');

    // Pagination
    const pages = data.total_pages || 1;
    const pager = pages <= 1 ? '' : `
        <div style="display:flex;align-items:center;gap:8px;padding:12px 16px;border-top:1px solid var(--border-color)">
            <button class="btn-secondary-custom" ${page <= 1 ? 'disabled' : ''} onclick="_loadAuditLog(${page-1},_auditFilters)">‹ Prev</button>
            <span style="color:var(--text-muted);font-size:13px">Page ${page} / ${pages} &nbsp;(${data.total} records)</span>
            <button class="btn-secondary-custom" ${page >= pages ? 'disabled' : ''} onclick="_loadAuditLog(${page+1},_auditFilters)">Next ›</button>
        </div>`;

    const mc = document.getElementById('main-content');
    mc.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" data-i18n="nav_audit_log">📋 Audit Log</div>
                <div style="color:var(--text-muted);font-size:13px" data-i18n="audit_subtitle">System activity history</div>
            </div>
            <button class="btn-secondary-custom" onclick="showAuditPurgeModal()" data-i18n="audit_purge">
                <i class="bi bi-trash"></i> Purge Old Logs
            </button>
        </div>

        <!-- Filters -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px 16px;margin-bottom:16px;display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
            <div>
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px" data-i18n="audit_filter_action">Action</label>
                <select id="auditFilterAction" class="form-select" style="width:130px" onchange="_applyAuditFilters()">
                    <option value="">All</option>
                    <option value="create">Create</option>
                    <option value="update">Update</option>
                    <option value="delete">Delete</option>
                    <option value="login">Login</option>
                    <option value="logout">Logout</option>
                    <option value="export">Export</option>
                </select>
            </div>
            <div>
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px" data-i18n="audit_filter_model">Model</label>
                <input id="auditFilterModel" class="form-control" placeholder="e.g. BankCertificate" style="width:160px" onchange="_applyAuditFilters()">
            </div>
            <div>
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px" data-i18n="audit_filter_user">User</label>
                <input id="auditFilterUser" class="form-control" placeholder="Username" style="width:140px" onchange="_applyAuditFilters()">
            </div>
            <div>
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px" data-i18n="audit_filter_from">From</label>
                <input type="date" id="auditFilterFrom" class="form-control" style="width:145px" onchange="_applyAuditFilters()">
            </div>
            <div>
                <label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:4px" data-i18n="audit_filter_to">To</label>
                <input type="date" id="auditFilterTo" class="form-control" style="width:145px" onchange="_applyAuditFilters()">
            </div>
            <button class="btn-secondary-custom" onclick="_clearAuditFilters()" data-i18n="clear_filters">Clear</button>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="audit_timestamp">Timestamp</th>
                    <th data-i18n="audit_user">User</th>
                    <th data-i18n="audit_action">Action</th>
                    <th data-i18n="audit_model">Model</th>
                    <th data-i18n="audit_object_id">ID</th>
                    <th data-i18n="audit_object">Object</th>
                    <th data-i18n="audit_ip">IP</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
            ${pager}
        </div>`;

    // Re-apply filter values
    if (filters.action) document.getElementById('auditFilterAction').value = filters.action;
    if (filters.model)  document.getElementById('auditFilterModel').value  = filters.model;
    if (filters.user)   document.getElementById('auditFilterUser').value   = filters.user;
    if (filters.date_from) document.getElementById('auditFilterFrom').value = filters.date_from;
    if (filters.date_to)   document.getElementById('auditFilterTo').value   = filters.date_to;
    applyTranslations();
}

function _applyAuditFilters() {
    const filters = {};
    const a = document.getElementById('auditFilterAction');
    const m = document.getElementById('auditFilterModel');
    const u = document.getElementById('auditFilterUser');
    const f = document.getElementById('auditFilterFrom');
    const t = document.getElementById('auditFilterTo');
    if (a && a.value) filters.action    = a.value;
    if (m && m.value) filters.model     = m.value;
    if (u && u.value) filters.user      = u.value;
    if (f && f.value) filters.date_from = f.value;
    if (t && t.value) filters.date_to   = t.value;
    _loadAuditLog(1, filters);
}

function _clearAuditFilters() {
    _loadAuditLog(1, {});
}

function showAuditPurgeModal() {
    const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="audit_purge">Purge Old Logs</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <p style="color:var(--text-secondary)" data-i18n="audit_purge_desc">Delete audit log entries older than the specified number of days.</p>
            <label data-i18n="audit_purge_days">Retain logs for last N days</label>
            <input type="number" id="purgeDays" class="form-control" value="90" min="1" style="width:120px;margin-top:8px">
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
            <button class="btn-danger-custom" onclick="confirmAuditPurge()" data-i18n="audit_purge_confirm">Purge</button>
        </div>`;
    showModal(html);
}

async function confirmAuditPurge() {
    const days = parseInt(document.getElementById('purgeDays').value) || 90;
    const res = await fetch('/api/audit-log/purge/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days }),
    });
    if (res.ok) {
        const data = await res.json();
        closeModal();
        showToast(t('audit_purge_success', `Deleted ${data.deleted} old log entries`));
        renderAuditLog();
    } else {
        showToast(t('error_generic', 'Error purging logs'), 'error');
    }
}

function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
