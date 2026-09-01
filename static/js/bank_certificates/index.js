"use strict";

// bank_certificates.js — Bank Certificates management page

"use strict";

// ════════════════════════════════════════════════════════════════════════════
// MODULE STATE
// ════════════════════════════════════════════════════════════════════════════

let _currencies = [];

// ════════════════════════════════════════════════════════════════════════════
// BANK CERTIFICATES RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderBankCertificates() {
  const mc = document.getElementById("main-content");
  mc.innerHTML =
    '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  await refreshBanks();
  const [cRes, certRes] = await Promise.all([
    fetch("/api/currencies/"),
    fetch("/api/bank-certificates/"),
  ]);

  const currData = await cRes.json();
  const certData = await certRes.json();
  const certificates = certData.certificates || [];
  _currencies = currData.currencies || [];

  const editTitle = t("edit", "Edit");
  const deleteTitle = t("delete", "Delete");
  const historyTitle = t("interest_history", "Interest History");

  const rows = certificates
    .map((c) => {
      const isClosed =
        String(c.status || "")
          .trim()
          .toLowerCase() === "closed";

      // Apply the background tint, explicit red text color, and semi-bold font to every cell if closed
      const tdStyle = isClosed
        ? 'style="background-color: rgba(255, 77, 109, 0.05) !important; color: var(--accent-red) !important; font-weight: 700 !important;"'
        : "";

      return `
                <tr>
                    <td ${tdStyle}>${c.bank_name || "—"}</td>
                    <td ${tdStyle}><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${c.currency_flag} ${c.currency_code || "—"}</span></td>
                    <td ${tdStyle}>${formatDate(c.issue_date) || "—"}</td>
                    <td ${tdStyle}>${formatDate(c.expiry_date) || "—"}</td>
                    <td ${tdStyle} class="text-end">${fmt(c.amount)}</td>
                    <td ${tdStyle}>${c.interest_rate ? c.interest_rate : "—"}</td>
                    <td ${tdStyle}>${c.interest_value ? fmt(c.interest_value) : "—"}</td>
                    <td ${tdStyle} class="local-freq-field" data-freq="${c.frequency || ""}">
                    ${c.frequency ? c.frequency.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase()) : "—"}
                    </td>
                    <td ${tdStyle}>
                        ${c.status || "—"}
                    </td>
                    <td ${tdStyle}>
                        <button class="btn-icon" onclick="showBankCertificateModal(${c.id})" title="${editTitle}"><i class="bi bi-pencil"></i></button>
                        <button class="btn-icon" onclick="showBankCertificateInterestHistory(${c.id})" title="${historyTitle}"><i class="bi bi-clock-history"></i></button>
                        <button class="btn-icon del" onclick="deleteBankCertificate(${c.id})" title="${deleteTitle}"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>`;
    })
    .join("");

  const bankCertificatesTitle = t("bank_certificates", "Bank Certificates");
  const bankHeader = t("bank", "Bank");
  const currencyHeader = t("currency", "Currency");
  const issueDateHeader = t("issue_date", "Issue Date");
  const expiryDateHeader = t("expiry_date", "Expiry Date");
  const amountHeader = t("balance_amount", "Amount");
  const rateHeader = t("interest_rate", "Interest Rate");
  const valueHeader = t("interest_value", "Interest Value");
  const frequencyHeader = t("frequency", "Frequency");
  const statusHeader = t("status", "Status");
  const actionsHeader = t("actions", "Actions");

  mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="bank_certificates">${bankCertificatesTitle}</div></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="bank">${bankHeader}</th>
                            <th data-i18n="currency">${currencyHeader}</th>
                            <th data-i18n="issue_date">${issueDateHeader}</th>
                            <th data-i18n="expiry_date">${expiryDateHeader}</th>
                            <th class="text-end" data-i18n="balance_amount">${amountHeader}</th>
                            <th data-i18n="interest_rate">${rateHeader}</th>
                            <th data-i18n="interest_value">${valueHeader}</th>
                            <th data-i18n="frequency">${frequencyHeader}</th>
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
// MODAL MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

async function showBankCertificateInterestHistory(certificateId) {
  const res = await fetch(`/api/bank-certificates/${certificateId}/interest-history/`);
  if (!res.ok) {
    showToast(t("error_loading_interest_history", "Error loading interest history"), "error");
    return;
  }

  const data = await res.json();
  const certificate = data.certificate || {};
  const items = data.items || [];
  const totalRecords = items.length;
  const totalInterestPaid = items.reduce(
    (sum, item) => sum + (parseFloat(item.interest_amount) || 0),
    0
  );

  const prettyIssueDate = formatCertificateHistoryDate(certificate.issue_date);
  const prettyNextPosting = getCertificateNextPostingDate(certificate, items);
  const prettyFrequency = formatCertificateFrequencyLabel(certificate.frequency || "");

  const rows = items.length
    ? items
        .map(
          (item) => `
            <tr data-posting-date="${item.posting_date || ""}">
                <td>${formatDate(item.posting_date) || "—"}</td>
                <td>${item.posting_period || "—"}</td>
                <td class="text-end">${fmt(item.interest_amount || 0)}</td>
                <td>${item.bank_name || "—"}</td>
                <td>${item.currency_code || "—"}</td>
                <td>${item.created_at ? formatDate(item.created_at) : "—"}</td>
            </tr>
        `
        )
        .join("")
    : `<tr><td colspan="6" style="text-align:center;padding:22px;color:var(--text-muted)" data-i18n="no_interest_history">No interest history yet.</td></tr>`;

  const certTitle = certificate.bank_name
    ? `${certificate.bank_name} - ${certificate.currency_code || ""}`
    : certificate.id
      ? `#${certificate.id}`
      : "";

  const summaryRows = `
        <div class="row g-2" style="margin-bottom:12px;">
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="certificate">Certificate</div>
                    <div style="font-weight:700;color:var(--text-primary);">${certificate.bank_name || certTitle || "—"}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="issue_date">Issue Date</div>
                    <div style="font-weight:700;color:var(--text-primary);">${prettyIssueDate}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="frequency">Frequency</div>
                    <div style="font-weight:700;color:var(--text-primary);">${prettyFrequency}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="monthly_interest">Monthly Interest</div>
                    <div style="font-weight:700;color:var(--text-primary);">${fmt(parseFloat(certificate.interest_value) || 0)}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="total_posted">Total Posted</div>
                    <div style="font-weight:700;color:var(--text-primary);">${fmt(totalInterestPaid)}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="next_posting">Next Posting</div>
                    <div style="font-weight:700;color:var(--text-primary);">${prettyNextPosting}</div>
                </div>
            </div>
        </div>
    `;

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="interest_history">Interest History</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
        </div>
        <div class="modal-body">
            <div style="margin-bottom:10px;color:var(--text-secondary);font-size:13px;">
                <span data-i18n="certificate">Certificate</span>: ${certTitle || "—"}
            </div>
            ${summaryRows}
            <div class="row g-2" style="margin-bottom:10px;">
                <div class="col-sm-6">
                    <label class="form-label" data-i18n="start_date">Start Date</label>
                    <input type="date" class="form-control" id="interestHistoryStart" oninput="filterBankCertificateInterestHistoryRows()">
                </div>
                <div class="col-sm-6">
                    <label class="form-label" data-i18n="end_date">End Date</label>
                    <input type="date" class="form-control" id="interestHistoryEnd" oninput="filterBankCertificateInterestHistoryRows()">
                </div>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="posting_date">Posting Date</th>
                            <th data-i18n="posting_period">Posting Period</th>
                            <th class="text-end" data-i18n="interest_amount">Interest Amount</th>
                            <th data-i18n="bank">Bank</th>
                            <th data-i18n="currency">Currency</th>
                            <th data-i18n="created_at">Created At</th>
                        </tr>
                    </thead>
                    <tbody id="interestHistoryRows">${rows}</tbody>
                </table>
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:12px;padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                <div><span data-i18n="total_records">Total Records</span> : <strong>${totalRecords}</strong></div>
                <div><span data-i18n="total_interest_paid">Total Interest Paid</span> : <strong>${fmt(totalInterestPaid)}</strong></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()" data-i18n="btn_close">Close</button>
        </div>
    `);
  applyTranslations();
}

function filterBankCertificateInterestHistoryRows() {
  const start = document.getElementById("interestHistoryStart")?.value || "";
  const end = document.getElementById("interestHistoryEnd")?.value || "";
  const rows = document.querySelectorAll("#interestHistoryRows tr[data-posting-date]");

  rows.forEach((row) => {
    const postingDate = row.getAttribute("data-posting-date") || "";
    const inStart = !start || postingDate >= start;
    const inEnd = !end || postingDate <= end;
    row.style.display = inStart && inEnd ? "" : "none";
  });
}

window.showBankCertificateInterestHistory = showBankCertificateInterestHistory;
window.filterBankCertificateInterestHistoryRows = filterBankCertificateInterestHistoryRows;
