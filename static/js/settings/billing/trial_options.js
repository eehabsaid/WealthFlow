"use strict";
// Billing settings — "trial for sysadmin-created users" option (default ON, existing users untouched).
// This file is part of the settings module. Do not edit directly.

async function renderTrialOptionsCard() {
  const mount = document.getElementById("trialOptionsMount");
  if (!mount) return;
  const res = await fetch("/api/settings/billing/trial-options/");
  if (!res.ok) return;
  const { trial_on_admin_created_users: on } = await res.json();
  mount.innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
            <div style="font-weight:600;color:var(--text-secondary);margin-bottom:6px;" data-i18n="trial_options_title">${t("trial_options_title", "Trials")}</div>
            <div class="form-check">
                <input type="checkbox" class="form-check-input" id="trialOnAdminCreated" ${on ? "checked" : ""} onchange="saveTrialOptions()">
                <label class="form-check-label" for="trialOnAdminCreated" data-i18n="trial_on_admin_created_label">${t("trial_on_admin_created_label", "Give users I create a free trial")}</label>
                <div style="color:var(--text-muted);font-size:12px;" data-i18n="trial_on_admin_created_hint">${t("trial_on_admin_created_hint", "New accounts created from Settings > Users start a trial like self-registered ones. Existing users are not changed.")}</div>
            </div>
        </div>`;
  applyTranslations();
}

async function saveTrialOptions() {
  const box = document.getElementById("trialOnAdminCreated");
  const res = await fetch("/api/settings/billing/trial-options/", {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    body: JSON.stringify({ trial_on_admin_created_users: box.checked }),
  });
  if (res.ok) {
    showToast(t("trial_options_saved", "Trial option saved ✓"), "success");
  } else {
    box.checked = !box.checked;
    showToast(t("trial_options_error", "Error saving trial option"), "error");
  }
}

window.renderTrialOptionsCard = renderTrialOptionsCard;
window.saveTrialOptions = saveTrialOptions;
