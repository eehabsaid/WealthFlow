"use strict";
// SMTP server configuration settings
// This file is part of the settings module. Do not edit directly.

function applySmtpPreset(provider) {
  const host = document.getElementById("smtpHost");
  const port = document.getElementById("smtpPort");
  const tls = document.getElementById("smtpUseTls");
  const ssl = document.getElementById("smtpUseSsl");

  if (!host || !port || !tls || !ssl) {
    return;
  }

  if (provider === "gmail") {
    host.value = "smtp.gmail.com";
    port.value = "587";
    tls.value = "true";
    ssl.value = "false";
    return;
  }

  if (provider === "outlook") {
    host.value = "smtp-mail.outlook.com";
    port.value = "587";
    tls.value = "true";
    ssl.value = "false";
  }
}

function readSmtpForm() {
  const val = (id) => (document.getElementById(id)?.value || "").trim();
  return {
    host: val("smtpHost"),
    port: val("smtpPort"),
    username: val("smtpUsername"),
    password: val("smtpPassword"),
    senderEmail: val("smtpSenderEmail"),
    adminEmail: val("smtpAdminEmail"),
    testRecipient: val("smtpTestRecipient"),
    useTls: val("smtpUseTls") === "true" ? "true" : "false",
    useSsl: val("smtpUseSsl") === "true" ? "true" : "false",
  };
}

function validateSmtpForm(f) {
  if (!f.host || !f.port || !f.username || !f.senderEmail) {
    showToast(
      t("smtp_required_fields", "Please fill sender email, SMTP host, port, and username."),
      "error"
    );
    return false;
  }
  if (!/^\d+$/.test(f.port)) {
    showToast(t("smtp_port_invalid", "SMTP port must be a valid number."), "error");
    return false;
  }
  if (f.useTls === "true" && f.useSsl === "true") {
    showToast(
      t("smtp_tls_ssl_conflict", "Enable either TLS or SSL, not both at the same time."),
      "error"
    );
    return false;
  }
  return true;
}

// The stored password is never sent back to the browser, so an empty
// password field means "keep the saved one" and is not posted.
async function persistSmtpForm(f) {
  const payload = [
    ["sender_email", f.senderEmail],
    ["administrator_notification_email", f.adminEmail],
    ["smtp_host", f.host],
    ["smtp_port", f.port],
    ["smtp_username", f.username],
    ...(f.password ? [["smtp_password", f.password]] : []),
    ["smtp_use_tls", f.useTls],
    ["smtp_use_ssl", f.useSsl],
  ];
  for (const [key, value] of payload) {
    const res = await fetch("/api/settings/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    });
    if (!res.ok) {
      throw new Error(`save_failed_${key}`);
    }
  }
}

async function saveSmtpSettingsFromGui() {
  const form = readSmtpForm();
  if (!validateSmtpForm(form)) return;
  try {
    await persistSmtpForm(form);
    showToast(t("settings_saved", "Settings saved ✓"));
  } catch {
    showToast(t("settings_save_failed", "Save failed"), "error");
  }
}

async function testSmtpSettingsFromGui() {
  const form = readSmtpForm();
  if (!validateSmtpForm(form)) return;
  try {
    await persistSmtpForm(form);
    const testRes = await fetch("/api/settings/email-test/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_email: form.testRecipient }),
    });
    const data = await testRes.json();
    const messageKey = data.message_key || "smtp_test_error_generic";
    if (data.ok) {
      showToast(t(messageKey, "SMTP test email sent successfully."), "success");
      return;
    }
    showToast(t(messageKey, "SMTP test failed."), "error");
  } catch {
    showToast(
      t(
        "smtp_test_error_generic",
        "SMTP test failed. Please verify your settings and provider policy."
      ),
      "error"
    );
  }
}
