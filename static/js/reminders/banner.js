"use strict";

async function checkReminders() {
  try {
    const enabled = await _getReminderSetting();
    if (!enabled) return;
    const res = await fetch("/api/reminders/check/");
    if (!res.ok) return;
    const data = await res.json();
    if (data.count > 0) {
      _showReminderBanner(data.reminders);
    }
  } catch (e) {}
}

function _showReminderBanner(reminders) {
  const existing = document.getElementById("reminder-banner");
  if (existing) existing.remove();

  const viewText = t("view", "View");
  const remindersTitle = t("reminders_due", "Reminders");

  const items = reminders
    .slice(0, 5)
    .map(
      (r) => `
            <div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.1)">
                <span style="font-size:16px">${_reminderIcon(r.rule_type)}</span>
                <div style="flex:1">
                    <div style="font-weight:600;font-size:13px">${esc(r.rule_name)}</div>
                    <div style="font-size:12px;opacity:0.85">${esc(r.message)}</div>
                </div>
                ${r.link ? `<button onclick="navigate('${r.link}');dismissReminderBanner()" style="background:rgba(255,255,255,0.15);border:none;color:#fff;border-radius:6px;padding:3px 8px;font-size:11px;cursor:pointer" data-i18n="view">${viewText}</button>` : ""}
            </div>`
    )
    .join("");

  const more =
    reminders.length > 5
      ? `<div style="font-size:12px;opacity:0.7;padding-top:6px">+${reminders.length - 5} ${t("more_reminders", "more reminder(s)")}</div>`
      : "";

  const banner = document.createElement("div");
  banner.id = "reminder-banner";
  banner.style.cssText = `position:fixed;top:60px;right:16px;width:340px;background:var(--accent-primary);
        color:#fff;border-radius:12px;padding:14px 16px;z-index:1100;
        box-shadow:0 8px 32px rgba(0,0,0,0.4);animation:slideInRight 0.3s ease`;
  banner.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <span style="font-weight:700;font-size:14px">🔔 ${remindersTitle} (${reminders.length})</span>
            <button onclick="dismissReminderBanner()" style="background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1">×</button>
        </div>
        ${items}${more}`;
  document.body.appendChild(banner);

  // Auto-dismiss after 15 seconds
  setTimeout(dismissReminderBanner, 15000);
}

function dismissReminderBanner() {
  const b = document.getElementById("reminder-banner");
  if (b) b.remove();
}
