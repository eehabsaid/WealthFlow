"use strict";
// Email template settings tab: SMTP config panel + template list rendering.
// Part of the settings module (split from the former monolithic
// email_templates.js, 200-line rule). Do not edit directly.

async function renderEmailTemplateSettings() {
  const lang = currentLang ? currentLang() : localStorage.getItem("lang") || "en";
  const [templatesRes, settingsRes] = await Promise.all([
    fetch(`/api/settings/email-templates/?lang=${encodeURIComponent(lang)}`),
    fetch("/api/settings/"),
  ]);
  const data = await templatesRes.json();
  const settingsData = await settingsRes.json();
  const s = settingsData.settings || {};
  const smtpPort = s.smtp_port || "587";
  const smtpTls = s.smtp_use_tls !== "false";
  const smtpSsl = s.smtp_use_ssl === "true";
  const rows = (data.items || [])
    .map(
      (item) => `
        <tr>
            <td data-i18n="email_template_${item.key}_name">${t(`email_template_${item.key}_name`, item.key)}</td>
            <td>${item.subject || ""}</td>
            <td>${item.description || ""}</td>
            <td>${item.updated_at ? new Date(item.updated_at).toLocaleString(lang) : "—"}</td>
            <td>
                <button class="btn-icon" onclick="showEmailTemplateModal(${item.id})" data-i18n-title="edit"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon" onclick="showEmailTemplateModal(${item.id}, true)" data-i18n-title="preview"><i class="bi bi-eye"></i></button>
            </td>
        </tr>
    `
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                <div>
                    <div style="font-weight:700;color:var(--text-primary);" data-i18n="smtp_settings">${t("smtp_settings", "SMTP Settings")}</div>
                    <div style="font-size:12px;color:var(--text-muted);" data-i18n="smtp_settings_desc">${t("smtp_settings_desc", "Configure provider credentials used for verification, approval, and password reset emails.")}</div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn-secondary-custom" onclick="applySmtpPreset('gmail')" data-i18n="smtp_preset_gmail">${t("smtp_preset_gmail", "Use Gmail Preset")}</button>
                    <button class="btn-secondary-custom" onclick="applySmtpPreset('outlook')" data-i18n="smtp_preset_outlook">${t("smtp_preset_outlook", "Use Outlook Preset")}</button>
                </div>
            </div>
            <div class="row g-3">
                <div class="col-md-6">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_sender_email">${t("smtp_sender_email", "Sender Email")}</label>
                    <input id="smtpSenderEmail" class="form-control" type="email" value="${s.sender_email || ""}" placeholder="noreply@example.com">
                </div>
                <div class="col-md-6">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_admin_email">${t("smtp_admin_email", "Administrator Notification Email")}</label>
                    <input id="smtpAdminEmail" class="form-control" type="email" value="${s.administrator_notification_email || ""}" placeholder="admin@example.com">
                </div>
                <div class="col-md-4">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_host">${t("smtp_host", "SMTP Host")}</label>
                    <input id="smtpHost" class="form-control" type="text" value="${s.smtp_host || ""}" placeholder="smtp.gmail.com">
                </div>
                <div class="col-md-2">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_port">${t("smtp_port", "Port")}</label>
                    <input id="smtpPort" class="form-control" type="number" min="1" max="65535" step="1" value="${smtpPort}">
                </div>
                <div class="col-md-3">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_use_tls">${t("smtp_use_tls", "Use TLS")}</label>
                    <select id="smtpUseTls" class="form-select">
                        <option value="true" ${smtpTls ? "selected" : ""}>${t("yes", "Yes")}</option>
                        <option value="false" ${!smtpTls ? "selected" : ""}>${t("no", "No")}</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_use_ssl">${t("smtp_use_ssl", "Use SSL")}</label>
                    <select id="smtpUseSsl" class="form-select">
                        <option value="true" ${smtpSsl ? "selected" : ""}>${t("yes", "Yes")}</option>
                        <option value="false" ${!smtpSsl ? "selected" : ""}>${t("no", "No")}</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_username">${t("smtp_username", "SMTP Username")}</label>
                    <input id="smtpUsername" class="form-control" type="text" value="${s.smtp_username || ""}" placeholder="username or API key id">
                </div>
                <div class="col-md-6">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_password">${t("smtp_password", "SMTP Password")}</label>
                    <input id="smtpPassword" class="form-control" type="password" value="${s.smtp_password || ""}" placeholder="app password or API key">
                </div>
                <div class="col-md-6">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="smtp_test_recipient">${t("smtp_test_recipient", "SMTP Test Recipient")}</label>
                    <input id="smtpTestRecipient" class="form-control" type="email" value="${s.administrator_notification_email || s.sender_email || ""}" placeholder="recipient@example.com">
                </div>
            </div>
            <div style="margin-top:10px;font-size:12px;color:var(--text-muted);" data-i18n="smtp_tls_ssl_hint">${t("smtp_tls_ssl_hint", "Use either TLS or SSL based on your provider. For most providers, TLS=true and SSL=false with port 587.")}</div>
            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px;">
                <button class="btn-secondary-custom" onclick="renderEmailTemplateSettings()" data-i18n="reload">${t("reload", "Reload")}</button>
                <button class="btn-secondary-custom" onclick="testSmtpSettingsFromGui()" data-i18n="smtp_test_button">${t("smtp_test_button", "Send Test Email")}</button>
                <button class="btn-primary-custom" onclick="saveSmtpSettingsFromGui()" data-i18n="save_smtp_settings">${t("save_smtp_settings", "Save SMTP Settings")}</button>
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_email_templates">${t("settings_email_templates", "Email Templates")}</div>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="email_template_name">${t("email_template_name", "Template Name")}</th>
                            <th data-i18n="email_template_subject">${t("email_template_subject", "Subject")}</th>
                            <th data-i18n="description">${t("description", "Description")}</th>
                            <th data-i18n="last_updated">${t("last_updated", "Last Updated")}</th>
                            <th data-i18n="actions">${t("actions", "Actions")}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
    `;
  applyTranslations();
}
