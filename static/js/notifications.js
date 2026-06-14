// notifications.js — Notification center (Feature 1)

// ── Bell badge update ─────────────────────────────────────
async function updateNotificationBadge() {
    try {
        const res = await fetch('/api/notifications/?unread=true&limit=1');
        if (!res.ok) return;
        const data = await res.json();
        const count = data.unread_count || 0;
        const badge = document.getElementById('notif-badge');
        if (badge) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = count > 0 ? 'inline-flex' : 'none';
        }
    } catch (e) {}
}

// ── Generate reminders on app load ───────────────────────
async function generateReminders() {
    try {
        await fetch('/api/notifications/', { method: 'POST' });
        await updateNotificationBadge();
    } catch (e) {}
}

// ── Notification center page ──────────────────────────────
async function renderNotifications() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const res = await fetch('/api/notifications/?limit=100');
    const data = await res.json();
    const notifs = data.notifications || [];

    const rows = notifs.length === 0
        ? `<tr><td colspan="4" style="text-align:center;padding:32px;color:var(--text-muted)" data-i18n="no_notifications">No notifications</td></tr>`
        : notifs.map(n => `
            <tr style="opacity:${n.is_read ? '0.6' : '1'}">
                <td>
                    <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                        background:${n.is_read ? 'var(--text-muted)' : 'var(--accent-primary)'};
                        margin-right:8px"></span>
                    ${_notifIcon(n.notif_type)} <strong>${esc(n.title)}</strong>
                </td>
                <td style="color:var(--text-secondary)">${esc(n.message)}</td>
                <td style="white-space:nowrap;color:var(--text-muted);font-size:12px">${n.created_at}</td>
                <td>
                    ${n.link ? `<a href="${n.link}" onclick="navigate('${n.link.replace('#','')}');markNotifRead(${n.id})" style="color:var(--accent-primary);text-decoration:none;font-size:12px" data-i18n="view">View</a>` : ''}
                    ${!n.is_read ? `<button class="btn-icon" onclick="markNotifRead(${n.id})" title="Mark read"><i class="bi bi-check2"></i></button>` : ''}
                </td>
            </tr>`).join('');

    mc.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" data-i18n="nav_notifications">🔔 Notifications</div>
                <div style="color:var(--text-muted);font-size:13px" data-i18n="notif_subtitle">Your reminders and alerts</div>
            </div>
            <button class="btn-secondary-custom" onclick="markAllNotifsRead()" data-i18n="mark_all_read">
                <i class="bi bi-check2-all"></i> Mark All Read
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="notif_title">Title</th>
                    <th data-i18n="notif_message">Message</th>
                    <th data-i18n="notif_time">Time</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
    updateNotificationBadge();
}

function _notifIcon(type) {
    const icons = {
        cert_maturity:   '🏦',
        salary_reminder: '💰',
        system:          '⚙️',
        custom:          '📌',
    };
    return icons[type] || '🔔';
}

async function markNotifRead(id) {
    await fetch(`/api/notifications/${id}/read/`, { method: 'POST' });
    updateNotificationBadge();
    renderNotifications();
}

async function markAllNotifsRead() {
    await fetch('/api/notifications/mark-all-read/', { method: 'POST' });
    updateNotificationBadge();
    renderNotifications();
}

function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
