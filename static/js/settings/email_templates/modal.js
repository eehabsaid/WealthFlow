"use strict";
// Email template editor/preview modal and save handler.
// Part of the settings module (split from the former monolithic
// email_templates.js, 200-line rule). Do not edit directly.

async function showEmailTemplateModal(templateId, previewOnly = false) {
  const lang = currentLang ? currentLang() : localStorage.getItem("lang") || "en";
  const res = await fetch(
    `/api/settings/email-templates/${templateId}/?lang=${encodeURIComponent(lang)}`
  );
  const item = await res.json();
  const sample = {
    UserName: "Ehab",
    Email: "ehab@example.com",
    VerificationLink: "https://wealthflow.example/verify/token",
    PasswordResetLink: "https://wealthflow.example/reset/token",
    ApprovalDate: "2026-07-05",
    AppName: "WealthFlow",
    CurrentYear: "2026",
  };
  const renderPreview = (text) =>
    Object.entries(sample).reduce(
      (out, [key, value]) => out.split(`{{${key}}}`).join(value),
      String(text || "")
    );

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="email_template_editor">${t("email_template_editor", "Email Template Editor")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div style="margin-bottom:12px;color:var(--text-secondary);font-weight:600;" data-i18n="email_template_${item.key}_name">${t(`email_template_${item.key}_name`, item.key)}</div>
            <div class="mb-3">
                <label data-i18n="email_template_subject">${t("email_template_subject", "Subject")}</label>
                <input id="emailTemplateSubject" class="form-control" value="${(item.subject || "").replace(/"/g, "&quot;")}" ${previewOnly ? "disabled" : ""}>
            </div>
            <div class="mb-3">
                <label data-i18n="email_template_body">${t("email_template_body", "Email Body")}</label>
                <textarea id="emailTemplateBody" class="form-control" rows="10" ${previewOnly ? "disabled" : ""}>${item.body || ""}</textarea>
            </div>
            <div style="margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="email_template_preview">${t("email_template_preview", "Preview")}</div>
            <div id="emailTemplatePreview" style="white-space:pre-wrap;background:var(--bg-tertiary);border:1px solid var(--border-color);border-radius:10px;padding:12px;line-height:1.7;">${renderPreview(item.body || "")}</div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            ${previewOnly ? "" : `<button class="btn-primary-custom" onclick="saveEmailTemplate(${item.id})" data-i18n="btn_save">${t("btn_save", "Save")}</button>`}
        </div>
    `);
  applyTranslations();

  const bodyEl = document.getElementById("emailTemplateBody");
  const subjectEl = document.getElementById("emailTemplateSubject");
  const previewEl = document.getElementById("emailTemplatePreview");
  const updatePreview = () => {
    previewEl.textContent =
      `${renderPreview(subjectEl.value || "")}\n\n${renderPreview(bodyEl.value || "")}`.trim();
  };
  if (bodyEl && subjectEl && !previewOnly) {
    bodyEl.addEventListener("input", updatePreview);
    subjectEl.addEventListener("input", updatePreview);
    updatePreview();
  }
}

async function saveEmailTemplate(templateId) {
  const lang = currentLang ? currentLang() : localStorage.getItem("lang") || "en";
  const subject = document.getElementById("emailTemplateSubject")?.value || "";
  const body = document.getElementById("emailTemplateBody")?.value || "";
  const res = await fetch(`/api/settings/email-templates/${templateId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lang, subject, body }),
  });
  if (!res.ok) {
    showToast(t("settings_save_failed", "Save failed"), "error");
    return;
  }
  closeModal();
  showToast(t("settings_saved", "Settings saved ✓"));
  renderEmailTemplateSettings();
}
