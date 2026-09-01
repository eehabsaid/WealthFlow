"use strict";

function _ruleSummary(r) {
  if (r.rule_type === "cert_maturity") {
    return `${r.days_before} ${t("days_before_expiry", "days before expiry")}`;
  }
  const triggerLabel = r.salary_trigger_label || r.salary_trigger;
  return `${triggerLabel}: ${r.salary_day}`;
}

async function showReminderRuleModal(id) {
  const rulesRes = await fetch("/api/reminders/");
  const rulesData = await rulesRes.json();
  const rule = id ? (rulesData.rules || []).find((r) => r.id === id) : null;
  const ruleTypes = rulesData.rule_types || [];
  const triggers = rulesData.salary_triggers || [];

  const typeOpts = ruleTypes
    .map(
      (rt) =>
        `<option value="${rt.value}" ${rule && rule.rule_type === rt.value ? "selected" : ""}>${rt.label}</option>`
    )
    .join("");

  const triggerOpts = triggers
    .map(
      (tr) =>
        `<option value="${tr.value}" ${rule && rule.salary_trigger === tr.value ? "selected" : ""}>${tr.label}</option>`
    )
    .join("");

  const isCert = !rule || rule.rule_type === "cert_maturity";

  const titleText = id ? t("edit_rule", "Edit Rule") : t("add_rule", "Add Rule");
  const ruleNameLabel = t("rule_name", "Rule Name");
  const ruleTypeLabel = t("rule_type", "Rule Type");
  const daysBeforeLabel = t("days_before_expiry", "Days Before Expiry");
  const daysBeforeHint = t(
    "days_before_expiry_hint",
    "Reminder fires this many days before the certificate expires"
  );
  const salaryTriggerLabel = t("salary_trigger", "Trigger Type");
  const triggerValueLabel = t("trigger_value", "Trigger Value (day number)");
  const messageLabel = t("reminder_message", "Reminder Message");
  const activeLabel = t("rule_active", "Active (enabled)");
  const cancelText = t("cancel", "Cancel");
  const saveText = t("save", "Save");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title">${titleText}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label class="form-label" data-i18n="rule_name">${ruleNameLabel}</label>
                    <input class="form-control" id="rrName" value="${rule ? esc(rule.name) : ""}">
                </div>
                <div class="col-12">
                    <label class="form-label" data-i18n="rule_type">${ruleTypeLabel}</label>
                    <select class="form-select" id="rrType" onchange="toggleRuleFields()">
                        ${typeOpts}
                    </select>
                </div>

                <!-- Certificate fields -->
                <div id="certFields" class="col-12" ${isCert ? "" : 'style="display:none"'}>
                    <label class="form-label" data-i18n="days_before_expiry">${daysBeforeLabel}</label>
                    <input type="number" class="form-control" id="rrDaysBefore"
                        value="${rule ? rule.days_before : 30}" min="1">
                    <div style="font-size:12px;color:var(--text-muted);margin-top:4px" data-i18n="days_before_expiry_hint">${daysBeforeHint}</div>
                </div>

                <!-- Salary fields -->
                <div id="salaryFields" ${!isCert ? "" : 'style="display:none"'}>
                    <div class="row g-3">
                        <div class="col-6">
                            <label class="form-label" data-i18n="salary_trigger">${salaryTriggerLabel}</label>
                            <select class="form-select" id="rrTrigger">
                                ${triggerOpts}
                            </select>
                        </div>
                        <div class="col-6">
                            <label class="form-label" data-i18n="trigger_value">${triggerValueLabel}</label>
                            <input type="number" class="form-control" id="rrSalaryDay"
                                value="${rule ? rule.salary_day : 25}" min="1" max="31">
                        </div>
                        <div class="col-12">
                            <label class="form-label" data-i18n="reminder_message">${messageLabel}</label>
                            <input class="form-control" id="rrMessage"
                                value="${rule ? esc(rule.salary_message) : ""}">
                        </div>
                    </div>
                </div>

                <div class="col-12">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                        <input type="checkbox" id="rrActive" ${!rule || rule.is_active ? "checked" : ""}>
                        <span data-i18n="rule_active">${activeLabel}</span>
                    </label>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveReminderRule(${id || "null"})" data-i18n="save">${saveText}</button>
        </div>`;
  showModal(html);
  applyTranslations();
}

function toggleRuleFields() {
  const type = document.getElementById("rrType").value;
  const isCert = type === "cert_maturity";
  document.getElementById("certFields").style.display = isCert ? "" : "none";
  document.getElementById("salaryFields").style.display = isCert ? "none" : "";
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & SETTINGS
// ════════════════════════════════════════════════════════════════════════════
