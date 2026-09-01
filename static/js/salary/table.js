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

  const rows = entries
    .map(
      (e) => `
        <tr>
            <td>
                <input type="checkbox" class="form-check-input" ${parseFloat(String(e.expected).replace(/,/g, "")) > 0 && Math.abs(parseFloat(String(e.expected).replace(/,/g, "")) - parseFloat(String(e.paid).replace(/,/g, ""))) < 0.01 ? 'checked="checked" style="background-color: var(--bs-primary) !important; border-color: var(--bs-primary) !important;"' : ""} onchange="toggleSalaryPaid(${e.id}, this.checked, ${companyId})">
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

  const emptyRow = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px">
        No entries for this year.</td></tr>`;

  area.innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
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
        
        <div class="alert alert-info py-3 px-4 mt-4" style="border: 1px solid rgba(13, 110, 253, 0.25); background: rgba(13, 110, 253, 0.05); color: var(--text-primary); border-radius: 12px;">
            <h6 style="color: var(--accent-primary); font-weight: 700; margin-bottom: 10px;">✓ How it works:</h6>
            <ul style="margin-bottom: 0; padding-left: 20px; font-size: 13px; line-height: 1.6; color: var(--text-secondary);">
                <li>Check the ✓ box to mark salary as paid</li>
                <li>Unchecking reverses the payment (removes from bank balance)</li>
                <li>Payment goes to the default bank configured for this company</li>
                <li>"Generate Current Month" creates entries for missing months</li>
                <li>Uses current_salary_amount from company payroll config</li>
            </ul>
        </div>`;

  applyTranslations();
}
