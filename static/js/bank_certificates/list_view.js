"use strict";
// list_view.js — Bank Certificates list page render. Split out of the
// former bank_certificates/index.js monolith. See interest_history.js for
// the interest-history modal (loaded after this file).

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
