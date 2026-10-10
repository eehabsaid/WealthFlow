"use strict";
// Legal Text settings tab (sysadmin-only): account-deletion grace period card.
// How long a deleted account stays restorable before the scheduled purge removes it.
// This file is part of the settings module. Do not edit directly.

async function renderRetentionCard() {
  const box = document.getElementById("retentionCard");
  if (!box) return;
  const res = await fetch("/api/settings/account-retention/");
  if (!res.ok) {
    box.innerHTML = "";
    return;
  }
  const cfg = await res.json();
  box.innerHTML = `
    <div class="legal-publish-box">
      <label class="form-label" for="retentionDays" data-i18n="retention_grace_days">
        Account deletion grace period (days)
      </label>
      <p class="text-muted mb-1" data-i18n="retention_grace_help">
        A deleted account is disabled at once and can be restored during this period; after it ends the data is permanently removed.
        Keep the retention wording in the Privacy Policy below in line with this number.
      </p>
      <div class="legal-edit-row">
        <input id="retentionDays" type="number" class="form-control" min="${cfg.min}" max="${cfg.max}" step="1"
               value="${cfg.grace_days}" />
        <button id="retentionSaveBtn" type="button" class="btn-primary-custom" onclick="saveRetentionDays()">
          <i class="bi bi-check-lg"></i> <span data-i18n="retention_save">Save</span>
        </button>
      </div>
    </div>`;
  applyTranslations();
}

async function saveRetentionDays() {
  const input = document.getElementById("retentionDays");
  const btn = document.getElementById("retentionSaveBtn");
  btn.disabled = true;
  const res = await fetch("/api/settings/account-retention/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grace_days: input.value }),
  });
  btn.disabled = false;
  if (!res.ok) {
    showToast(t("retention_invalid", "Enter a whole number of days between 1 and 365."), "error");
    return;
  }
  const cfg = await res.json();
  input.value = cfg.grace_days;
  showToast(t("retention_saved", "Grace period saved."));
}
