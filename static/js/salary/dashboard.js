"use strict";

async function renderDashboard() {
  const mc = document.getElementById("main-content");
  mc.innerHTML =
    '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  const res = await fetch("/api/salary/summary/");
  const data = await res.json();
  const g = data.grand_total;

  // Sum remaining manually to ensure footer matches company rows
  const sumRemaining = data.companies.reduce((sum, c) => sum + c.total_remaining, 0);

  const companyRows = data.companies
    .map(
      (c) => `
        <tr>
            <td>
                <span style="background:${c.color_hex};display:inline-block;
                             width:8px;height:8px;border-radius:50%;margin-right:6px"></span>
                ${c.display_name}
                ${c.group_name ? `<span class="group-badge">${c.group_name}</span>` : ""}
            </td>
            <td>${c.years.length > 0 ? `${c.years[0]} – ${c.years[c.years.length - 1]}` : "—"}</td>
            <td>${c.total_months}</td>
            <td class="text-end">${fmt(c.total_expected)}</td>
            <td class="text-end amt-positive">${fmt(c.total_paid)}</td>
            <td class="text-end ${amtClass(c.total_remaining)}">${fmt(c.total_remaining)}</td>
        </tr>`
    )
    .join("");

  try {
    mc.innerHTML = `
            <div class="page-header">
                <div><div class="page-title" data-i18n="dashboard">Dashboard</div></div>
            </div>

            <button class="btn-primary-custom" onclick="window.location.href='/api/export/excel/'">
                <i class="bi bi-file-earmark-excel"></i>
                <span data-i18n="download_excel"></span>
            </button>

            <div class="row g-3 mb-4">
                ${kpiCard("kpi_total_earned", fmt(g.total_expected), "bi-cash-stack", "var(--accent-primary)")}
                ${kpiCard("kpi_total_paid", fmt(g.total_paid), "bi-check-circle", "var(--accent-green)")}
                ${kpiCard("kpi_total_remaining", fmt(sumRemaining), "bi-hourglass-split", sumRemaining > 0 ? "var(--accent-red)" : "var(--text-muted)")}
                ${kpiCard("kpi_work_months", fmtInt(g.total_months), "bi-calendar3", "var(--accent-yellow)")}
            </div>

            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                        border-radius:12px;padding:20px;margin-bottom:24px">
                <canvas id="salaryChart" height="80"></canvas>
            </div>

            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                        border-radius:12px;overflow:visible">
                <div class="table-container">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="company">Company</th>
                        <th>Years</th>
                        <th data-i18n="work_months">Months</th>
                        <th class="text-end" data-i18n="salary_expected">Expected</th>
                        <th class="text-end" data-i18n="salary_paid">Paid</th>
                        <th class="text-end" data-i18n="salary_remaining">Remaining</th>
                    </tr></thead>
                    <tbody>${companyRows}</tbody>
                    <tfoot><tr class="total-row">
                        <td colspan="2" data-i18n="grand_total">Grand Total</td>
                        <td>${g.total_months}</td>
                        <td class="text-end">${fmt(g.total_expected)}</td>
                        <td class="text-end">${fmt(g.total_paid)}</td>
                        <td class="text-end">${fmt(sumRemaining)}</td>
                    </tr></tfoot>
                </table>
                </div>
            </div>`;

    applyTranslations();
    drawDashboardChart(data.companies);
    _renderDashboardEnhancements();
  } catch (err) {
    console.error("Dashboard Render Error:", err);
    mc.innerHTML = '<div class="alert alert-danger">Error loading dashboard. Check console.</div>';
  }
}

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

// ── KPI card helper ───────────────────────────────────────────────────────

function kpiCard(label, value, icon, color) {
  // Run the key through your global translation helper function t() so it drops the actual text inside the div
  const titleText = typeof t === "function" ? t(label, label) : label;
  return `
        <div class="col-6 col-lg-3">
            <div class="kpi-card">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <i class="bi ${icon}" style="font-size:20px;color:${color}"></i>
                    <div class="kpi-label" data-i18n="${label}">${titleText}</div>
                </div>
                <div class="kpi-value" style="color:${color}">${value}</div>
            </div>
        </div>`;
}

// ── Dashboard chart ───────────────────────────────────────────────────────

function drawDashboardChart(companies) {
  const ctx = document.getElementById("salaryChart");
  if (!ctx) return;

  // Aggregate by group_name, falling back to display_name
  const groupMap = {};
  companies.forEach((c) => {
    const key = c.group_name || c.display_name;
    if (!groupMap[key]) {
      groupMap[key] = { name: key, total_paid: 0, color: c.color_hex };
    }
    groupMap[key].total_paid += c.total_paid;
  });

  const groups = Object.values(groupMap);
  const isMobile = window.innerWidth < 768;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: groups.map((g) => g.name),
      datasets: [
        {
          label: t("salary_paid", "Total Paid"),
          data: groups.map((g) => g.total_paid),
          backgroundColor: groups.map((g) => g.color + "bb"),
          borderColor: groups.map((g) => g.color),
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: !isMobile,
      indexAxis: isMobile ? "y" : "x",
      plugins: {
        legend: { labels: { color: "#7b93c9" } },
      },
      scales: {
        x: { ticks: { color: "#7b93c9" }, grid: { color: "#1e3a6e44" } },
        y: { ticks: { color: "#7b93c9" }, grid: { color: "#1e3a6e44" } },
      },
    },
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SALARY PAGE (per company)
// ════════════════════════════════════════════════════════════════════════════
