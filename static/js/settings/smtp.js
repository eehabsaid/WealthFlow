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

async function saveSmtpSettingsFromGui() {
  const host = (document.getElementById("smtpHost")?.value || "").trim();
  const port = (document.getElementById("smtpPort")?.value || "").trim();
  const username = (document.getElementById("smtpUsername")?.value || "").trim();
  const password = (document.getElementById("smtpPassword")?.value || "").trim();
  const senderEmail = (document.getElementById("smtpSenderEmail")?.value || "").trim();
  const adminEmail = (document.getElementById("smtpAdminEmail")?.value || "").trim();
  const useTls = document.getElementById("smtpUseTls")?.value === "true" ? "true" : "false";
  const useSsl = document.getElementById("smtpUseSsl")?.value === "true" ? "true" : "false";

  if (!host || !port || !username || !password || !senderEmail) {
    showToast(
      t(
        "smtp_required_fields",
        "Please fill sender email, SMTP host, port, username, and password."
      ),
      "error"
    );
    return;
  }

  if (!/^\d+$/.test(port)) {
    showToast(t("smtp_port_invalid", "SMTP port must be a valid number."), "error");
    return;
  }

  if (useTls === "true" && useSsl === "true") {
    showToast(
      t("smtp_tls_ssl_conflict", "Enable either TLS or SSL, not both at the same time."),
      "error"
    );
    return;
  }

  const payload = [
    ["sender_email", senderEmail],
    ["administrator_notification_email", adminEmail],
    ["smtp_host", host],
    ["smtp_port", port],
    ["smtp_username", username],
    ["smtp_password", password],
    ["smtp_use_tls", useTls],
    ["smtp_use_ssl", useSsl],
  ];

  try {
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
    showToast(t("settings_saved", "Settings saved ✓"));
  } catch {
    showToast(t("settings_save_failed", "Save failed"), "error");
  }
}

async function testSmtpSettingsFromGui() {
  const host = (document.getElementById("smtpHost")?.value || "").trim();
  const port = (document.getElementById("smtpPort")?.value || "").trim();
  const username = (document.getElementById("smtpUsername")?.value || "").trim();
  const password = (document.getElementById("smtpPassword")?.value || "").trim();
  const senderEmail = (document.getElementById("smtpSenderEmail")?.value || "").trim();
  const adminEmail = (document.getElementById("smtpAdminEmail")?.value || "").trim();
  const testRecipient = (document.getElementById("smtpTestRecipient")?.value || "").trim();
  const useTls = document.getElementById("smtpUseTls")?.value === "true" ? "true" : "false";
  const useSsl = document.getElementById("smtpUseSsl")?.value === "true" ? "true" : "false";

  if (!host || !port || !username || !password || !senderEmail) {
    showToast(
      t(
        "smtp_required_fields",
        "Please fill sender email, SMTP host, port, username, and password."
      ),
      "error"
    );
    return;
  }

  if (!/^\d+$/.test(port)) {
    showToast(t("smtp_port_invalid", "SMTP port must be a valid number."), "error");
    return;
  }

  if (useTls === "true" && useSsl === "true") {
    showToast(
      t("smtp_tls_ssl_conflict", "Enable either TLS or SSL, not both at the same time."),
      "error"
    );
    return;
  }

  const payload = [
    ["sender_email", senderEmail],
    ["administrator_notification_email", adminEmail],
    ["smtp_host", host],
    ["smtp_port", port],
    ["smtp_username", username],
    ["smtp_password", password],
    ["smtp_use_tls", useTls],
    ["smtp_use_ssl", useSsl],
  ];

  try {
    for (const [key, value] of payload) {
      const saveRes = await fetch("/api/settings/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      });
      if (!saveRes.ok) {
        throw new Error(`save_failed_${key}`);
      }
    }

    const testRes = await fetch("/api/settings/email-test/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_email: testRecipient }),
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
