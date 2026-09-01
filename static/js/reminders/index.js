"use strict";

// reminders.js — Reminder Engine management

"use strict";

// ════════════════════════════════════════════════════════════════════════════
// REMINDER BANNER
// ════════════════════════════════════════════════════════════════════════════

// ── Check reminders on app load, show banner if any due ──────

async function renderReminderSettings() {
  const [rulesRes, settingsRes] = await Promise.all([
    fetch("/api/reminders/"),
    fetch("/api/settings/"),
  ]);
  const rulesData = await rulesRes.json();
  const settingsData = await settingsRes.json();
  const rules = rulesData.rules || [];
  const ruleTypes = rulesData.rule_types || [];
  const triggers = rulesData.salary_triggers || [];
  const s = settingsData.settings || {};

  const enabledText = t("enabled", "Enabled");
  const editText = t("edit", "Edit");
  const deleteText = t("delete", "Delete");
  const activeText = t("active", "Active");
  const inactiveText = t("inactive", "Inactive");
  const noRulesText = t("no_reminder_rules", "No reminder rules. Add one to get started.");

  const rows =
    rules.length === 0
      ? `<tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text-muted)" data-i18n="no_reminder_rules">${noRulesText}</td></tr>`
      : rules
          .map(
            (r) => `
                <tr>
                    <td>
                        <span style="font-weight:600;color:var(--text-primary)">${esc(r.name)}</span>
                    </td>
                    <td>
                        <span style="background:var(--bg-tertiary);padding:2px 8px;border-radius:8px;font-size:12px">
                            ${esc(r.rule_type_label)}
                        </span>
                    </td>
                    <td style="font-size:13px;color:var(--text-secondary)">
                        ${_ruleSummary(r)}
                    </td>
                    <td>
                        <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                            <input type="checkbox" ${r.is_active ? "checked" : ""}
                                onchange="toggleReminderRule(${r.id}, this.checked)">
                            <span style="font-size:12px;color:${r.is_active ? "var(--accent-green)" : "var(--text-muted)"}"
                                data-i18n="${r.is_active ? "active" : "inactive"}">${r.is_active ? activeText : inactiveText}</span>
                        </label>
                    </td>
                    <td style="white-space:nowrap">
                        <button class="btn-icon" onclick="showReminderRuleModal(${r.id})" title="${editText}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn-icon" onclick="deleteReminderRule(${r.id})" title="${deleteText}"
                            style="color:var(--accent-danger)">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>`
          )
          .join("");

  const remindersEnabledTitle = t("reminders_enabled", "Enable Reminder Engine");
  const remindersEnabledDesc = t(
    "reminders_enabled_desc",
    "Show reminder banners on page load when rules are due"
  );
  const certExpiryTitle = t("cert_expiry_window", "Certificate Expiry Warning Window");
  const certExpiryDesc = t(
    "cert_expiry_window_desc",
    "Show expiring certificates on dashboard within this many days"
  );
  const saveText = t("save", "Save");
  const reminderRulesTitle = t("reminder_rules", "Reminder Rules");
  const addRuleText = t("add_rule", "Add Rule");
  const ruleNameHeader = t("rule_name", "Rule Name");
  const ruleTypeHeader = t("rule_type", "Type");
  const triggerHeader = t("trigger", "Trigger");
  const statusHeader = t("status", "Status");
  const actionsHeader = t("actions", "Actions");

  document.getElementById("settingsContent").innerHTML = `
        <!-- Global toggle -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="reminders_enabled">${remindersEnabledTitle}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="reminders_enabled_desc">${remindersEnabledDesc}</div>
            </div>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                <input type="checkbox" id="reminderEnabled"
                    ${s.reminder_check_enabled !== "false" ? "checked" : ""}
                    onchange="saveAppSetting('reminder_check_enabled', this.checked ? 'true' : 'false')">
                <span data-i18n="enabled">${enabledText}</span>
            </label>
        </div>

        <!-- Cert expiry warning window -->
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
            <div>
                <div style="font-weight:700;color:var(--text-primary)" data-i18n="cert_expiry_window">${certExpiryTitle}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px" data-i18n="cert_expiry_window_desc">${certExpiryDesc}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                <input type="number" id="certExpiryDays" class="form-control" style="width:90px"
                    value="${s.cert_expiry_warning_days || 30}" min="1" max="365">
                <button class="btn-secondary-custom" onclick="saveAppSetting('cert_expiry_warning_days', document.getElementById('certExpiryDays').value)" data-i18n="save">${saveText}</button>
            </div>
        </div>

        <!-- Rules table -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div style="font-weight:700;color:var(--text-primary)" data-i18n="reminder_rules">${reminderRulesTitle}</div>
            <button class="btn-primary-custom" onclick="showReminderRuleModal(null)">
                <i class="bi bi-plus-lg"></i> <span data-i18n="add_rule">${addRuleText}</span>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="rule_name">${ruleNameHeader}</th>
                            <th data-i18n="rule_type">${ruleTypeHeader}</th>
                            <th data-i18n="trigger">${triggerHeader}</th>
                            <th data-i18n="status">${statusHeader}</th>
                            <th data-i18n="actions">${actionsHeader}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
  applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// RULE UTILITIES & MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

function _reminderIcon(type) {
  return (
    {
      cert_maturity: "🏦",
      salary_unpaid: "💰",
      salary_day: "📅",
      custom: "📌",
    }[type] || "🔔"
  );
}

async function _getReminderSetting() {
  try {
    const res = await fetch("/api/settings/");
    const d = await res.json();
    return (d.settings || {}).reminder_check_enabled !== "false";
  } catch (e) {
    return true;
  }
}

// ════════════════════════════════════════════════════════════════════════════
// REMINDER SETTINGS PAGE
// ════════════════════════════════════════════════════════════════════════════

function esc(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
