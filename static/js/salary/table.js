"use strict";

function renderSalaryTable(allEntries, year, companyId) {
  const area = document.getElementById("salaryTableArea");
  if (!area) return;

  const entries = allEntries.filter((e) => e.year === year);

  let totExp = 0,
    totPaid = 0,
    totBonus = 0,
    totRemaining = 0;
  entries.forEach((e) => {
    totExp += e.expected;
    totPaid += e.paid;
    totBonus += e.bonus;
    totRemaining += e.remaining;
  });

  const isEntryPaid = (e) => {
    const exp = parseFloat(String(e.expected).replace(/,/g, ""));
    const paid = parseFloat(String(e.paid).replace(/,/g, ""));
    return exp > 0 && Math.abs(exp - paid) < 0.01;
  };

  const rows = entries
    .map(
      (e) => `
        <tr${isEntryPaid(e) ? ' class="salary-row-paid"' : ""}>
            <td>
                <input type="checkbox" class="form-check-input" ${isEntryPaid(e) ? 'checked="checked" style="background-color: var(--bs-primary) !important; border-color: var(--bs-primary) !important;"' : ""} onchange="toggleSalaryPaid(${e.id}, this.checked, ${companyId})">
            </td>
            <td>${e.month}</td>
            <td class="text-end">${fmt(e.expected)}</td>
            <td class="text-end amt-positive">${fmt(e.paid)}</td>
            <td class="text-end amt-positive">
                ${e.bonus > 0 ? fmt(e.bonus) : '<span class="amt-zero">—</span>'}
            </td>
            <td class="text-end ${amtClass(e.remaining)}">${fmt(e.remaining)}</td>
            <td>
                <button class="btn-icon" onclick="showSalaryModal(${e.id}, ${companyId})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn-icon del" onclick="deleteSalaryEntry(${e.id}, ${companyId})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>`
    )
    .join("");

  const emptyRow = `<tr class="salary-empty-row"><td colspan="7" data-i18n="salary_no_entries">No entries for this year.</td></tr>`;

  area.innerHTML = `
        <div class="salary-summary-grid">
            ${salarySummaryCard("salary_expected", fmt(totExp), "var(--accent-primary)")}
            ${salarySummaryCard("salary_paid", fmt(totPaid), "var(--accent-green)")}
            ${salarySummaryCard("salary_bonus", fmt(totBonus), "var(--accent-yellow)")}
            ${salarySummaryCard("salary_remaining", fmt(totRemaining), totRemaining > 0 ? "var(--accent-red)" : "var(--text-muted)")}
        </div>
        <div class="surface-panel surface-panel--flush salary-table-card">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th style="width: 40px;" data-i18n="mark_paid">✓</th>
                    <th data-i18n="salary_month">Month</th>
                    <th class="text-end" data-i18n="salary_expected">Expected</th>
                    <th class="text-end" data-i18n="salary_paid">Paid</th>
                    <th class="text-end" data-i18n="salary_bonus">Bonus</th>
                    <th class="text-end" data-i18n="salary_remaining">Remaining</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows || emptyRow}</tbody>
                <tfoot><tr class="total-row">
                    <td colspan="2" data-i18n="total">Total</td>
                    <td class="text-end">${fmt(totExp)}</td>
                    <td class="text-end">${fmt(totPaid)}</td>
                    <td class="text-end">${fmt(totBonus)}</td>
                    <td class="text-end ${amtClass(totRemaining)}">${fmt(totRemaining)}</td>
                    <td></td>
                </tr></tfoot>
            </table>
            </div>
        </div>
        
        <details class="salary-help">
            <summary data-i18n="salary_how_it_works">How it works</summary>
            <ul>
                <li data-i18n="salary_how_1">Check the ✓ box to mark a month as paid</li>
                <li data-i18n="salary_how_2">Unchecking reverses the payment and removes it from the bank balance</li>
                <li data-i18n="salary_how_3">Payment is credited to the default bank set for this company</li>
                <li data-i18n="salary_how_4">"Generate Current Month" creates entries for missing months</li>
                <li data-i18n="salary_how_5">Uses the current salary amount from the company's payroll settings</li>
            </ul>
        </details>`;

  applyTranslations();
}

// ── KPI summary card (selected year) ──────────────────────────────────────
function salarySummaryCard(labelKey, value, color) {
  const label = typeof t === "function" ? t(labelKey, labelKey) : labelKey;
  return `
        <div class="salary-summary-card">
            <div class="salary-summary-label" data-i18n="${labelKey}">${label}</div>
            <div class="salary-summary-value" style="color:${color}">${value}</div>
        </div>`;
}
