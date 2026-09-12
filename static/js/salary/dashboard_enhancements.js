"use strict";
// dashboard_enhancements.js — Dashboard widgets: expiring bank
// certificates and active reminders, appended after the main dashboard
// renders. Split out of the former salary/dashboard.js monolith. See
// dashboard_render.js for the main dashboard page render.

// ── Dashboard enhancements — expiring certs + active reminders ────────────

async function _renderDashboardEnhancements() {
  try {
    const [summRes, settRes] = await Promise.all([
      fetch("/api/dashboard/summary/"),
      fetch("/api/settings/"),
    ]);
    if (!summRes.ok) return;

    const d = await summRes.json();
    const sett = settRes.ok ? (await settRes.json()).settings || {} : {};
    const mc = document.getElementById("main-content");
    if (!mc) return;

    let html = "";

    // Expiring certificates widget
    if (sett.dashboard_show_certs !== "false" && d.expiring_soon?.length > 0) {
      const rows = d.expiring_soon
        .map(
          (c) => `
                <tr>
                    <td>${c["bank__name"] || "—"}</td>
                    <td style="white-space:nowrap">${c.expiry_date}</td>
                    <td class="text-end">
                        ${(parseFloat(c.amount) || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td>
                        <span style="color:${c.days_left <= 7 ? "var(--accent-danger)" : c.days_left <= 30 ? "#f59e0b" : "var(--accent-green)"};font-weight:700">
                            ${c.days_left}d
                        </span>
                    </td>
                    <td>
                        <span style="background:var(--bg-tertiary);padding:2px 8px;border-radius:8px;font-size:11px">
                            ${c.status || "—"}
                        </span>
                    </td>
                </tr>`
        )
        .join("");

      html += `
                <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                            border-radius:12px;margin-top:20px;overflow:visible">
                    <div style="padding:14px 20px;display:flex;justify-content:space-between;
                                align-items:center;border-bottom:1px solid var(--border-color)">
                        <div style="font-weight:700;color:var(--text-primary)">
                            ⚠️ <span data-i18n="expiring_certs_title">Certificates Expiring Soon</span>
                            <span style="background:var(--accent-danger);color:#fff;border-radius:10px;
                                         padding:1px 7px;font-size:11px;margin-left:6px">
                                ${d.expiring_soon.length}
                            </span>
                        </div>
                        <button class="btn-secondary-custom"
                            onclick="navigate('bank-certificates')"
                            data-i18n="view_all">View All</button>
                    </div>
                    <div class="table-container">
                    <table class="data-table">
                        <thead><tr>
                            <th data-i18n="bank">Bank</th>
                            <th data-i18n="expiry_date">Expiry</th>
                            <th class="text-end" data-i18n="amount">Amount (EGP)</th>
                            <th data-i18n="days_left">Days Left</th>
                            <th data-i18n="status">Status</th>
                        </tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                    </div>
                </div>`;
    }

    // Active reminders widget
    if (sett.dashboard_show_reminders !== "false" && d.active_reminders?.length > 0) {
      const rems = d.active_reminders
        .map(
          (r) => `
                <div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--border-color)">
                    <span style="font-size:16px">🔔</span>
                    <div>
                        <div style="font-size:12px;font-weight:700;color:var(--text-primary)">${r.rule}</div>
                        <div style="font-size:12px;color:var(--text-secondary)">${r.message}</div>
                    </div>
                </div>`
        )
        .join("");

      html += `
                <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                            border-radius:12px;margin-top:16px;padding:16px 20px">
                    <div style="font-weight:700;color:var(--text-primary);margin-bottom:10px">
                        🔔 <span data-i18n="active_reminders">Active Reminders Today</span>
                    </div>
                    ${rems}
                </div>`;
    }

    if (html) {
      mc.insertAdjacentHTML("beforeend", html);
      applyTranslations();
    }
  } catch (e) {}
}
