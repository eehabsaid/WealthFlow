"use strict";
// Dashboard settings rendering
// This file is part of the settings module. Do not edit directly.

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

