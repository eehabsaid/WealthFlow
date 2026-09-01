"use strict";

async function _renderBalanceReport() {
  const res = await fetch("/api/reports/balance/");
  const d = await res.json();
  const banks = d.by_bank || [];
  const home = d.home_entries || [];

  const bankRows = banks
    .map(
      (b) => `
        <tr>
            <td><strong>${esc(b.bank_name)}</strong></td>
            <td class="text-end">${_fmt(b.total_egp)} <span data-i18n="EGP"></span></td>
            <td>${b.entries.map((e) => `<span style="font-size:11px;color:var(--text-muted)">${_fmt(e.amount)} ${e.currency_code || ""}</span>`).join(", ")}</td>
        </tr>`
    )
    .join("");

  const homeRows = home
    .map(
      (e) => `
        <tr>
            <td>${esc(e.title || "Home")}</td>
            <td class="text-end">${_fmt(e.amount)} ${e.currency_code || ""}</td>
            <td style="color:var(--text-muted)">—</td>
        </tr>`
    )
    .join("");

  const grandEGP = banks.reduce((s, b) => s + b.total_egp, 0) + d.cert_total;

  document.getElementById("reportContent").innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px">
            ${_kpi("🏛️", "bank_balance", _fmt(banks.reduce((s, b) => s + b.total_egp, 0)) + ' <span data-i18n="EGP"></span>', "")}
            ${_kpi("🏦", "cert_balance", _fmt(d.cert_total) + ' <span data-i18n="EGP"></span>', "")}
            ${_kpi("💹", "total_monthly_interest", _fmt(d.cert_interest) + ' <span data-i18n="EGP"></span>', '<span data-i18n="per_month">per month</span>')}
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible;margin-bottom:16px">
            <div style="padding:14px 20px;font-weight:700;color:var(--text-primary);border-bottom:1px solid var(--border-color)" data-i18n="bank_accounts">Bank Accounts</div>
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="bank">Bank</th>
                    <th class="text-end" data-i18n="egp_balance">EGP Balance</th>
                    <th data-i18n="other_currencies">Other Currencies</th>
                </tr></thead>
                <tbody>${bankRows || _noData(3)}</tbody>
            </table>
            </div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div style="padding:14px 20px;font-weight:700;color:var(--text-primary);border-bottom:1px solid var(--border-color)" data-i18n="home_cash">Home / Cash</div>
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="description">Description</th>
                    <th class="text-end" data-i18n="amount">Amount</th>
                    <th data-i18n="note">Note</th>
                </tr></thead>
                <tbody>${homeRows || _noData(3)}</tbody>
            </table>
            </div>
        </div>`;
  applyTranslations();
}

// ── Certificate Report ─────────────────────────────────────────
