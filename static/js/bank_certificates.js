// bank_certificates.js — Bank Certificates page
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

  const rows = certificates
    .map(
      (c) => `
        <tr>
            <td>${c.bank_name || "—"}</td>
            <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${c.currency_flag} ${c.currency_code || "—"}</span></td>
            <td>${c.issue_date || "—"}</td>
            <td>${c.expiry_date || "—"}</td>
            <td>${fmt(c.amount)}</td>
            <td>${c.interest_rate ? c.interest_rate : "—"}</td>
            <td>${c.interest_value ? fmt(c.interest_value) : "—"}</td>
            <td class="local-freq-field" data-freq="${c.frequency || ""}">
              ${c.frequency ? c.frequency.replace(/_/g, " ").replace(/\b\w/g, ch => ch.toUpperCase()) : "—"}
            </td>
            <td>${c.status || "—"}</td>
            <td>
                <button class="btn-icon" onclick="showBankCertificateModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBankCertificate(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`,
    )
    .join("");

  mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="bank_certificates">Bank Certificates</div></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="bank">Bank</th>
                    <th data-i18n="currency">Currency</th>
                    <th data-i18n="issue_date">Issue Date</th>
                    <th data-i18n="expiry_date">Expiry Date</th>
                    <th class="text-end" data-i18n="balance_amount">Amount</th>
                    <th data-i18n="interest_rate">Interest Rate</th>
                    <th data-i18n="interest_value">Interest Value</th>
                    <th data-i18n="frequency">Frequency</th>
                    <th data-i18n="status">Status</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        </div>`;
  applyTranslations();
}

async function showBankCertificateModal(certificateId) {
  let certificate = null;
  if (certificateId) {
    const res = await fetch(`/api/bank-certificates/${certificateId}/`);
    certificate = await res.json();
  }
  const bankOpts = _banks
    .map(
      (b) =>
        `<option value="${b.id}" ${certificate && certificate.bank_id === b.id ? "selected" : ""}>${b.name}</option>`,
    )
    .join("");
  const curOpts = _currencies
    .map(
      (c) =>
        `<option value="${c.id}" ${certificate && certificate.currency_id === c.id ? "selected" : ""}>${c.flag} ${c.code}</option>`,
    )
    .join("");

  // Fetch status options cleanly BEFORE generating the HTML template to eliminate race conditions
  const statusOpts = await _getCertStatusOptions(certificate ? certificate.status : null);

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${certificate ? "edit_bank_certificate" : "add_bank_certificate"}">${certificate ? "Edit" : "Add"} Bank Certificate</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="status">Status</label>
                    <select class="form-select" id="bcStatus">
                        ${statusOpts}
                    </select>
                </div>
                <div class="col-6"><label data-i18n="bank">Bank</label><select class="form-select" id="bcBank"><option value="">— None —</option>${bankOpts}</select></div>
                <div class="col-6"><label data-i18n="currency">Currency</label>
                <select class="form-select" id="bcCurrency"><option value="">— Select currency —</option>${curOpts}</select></div>
                <div class="col-6"><label data-i18n="issue_date">Issue Date</label>
                <input type="date" class="form-control" id="bcIssue" value="${certificate ? certificate.issue_date : ""}"></div>
                <div class="col-6"><label data-i18n="expiry_date">Expiry Date</label>
                <input type="date" class="form-control" id="bcExpiry" value="${certificate ? certificate.expiry_date : ""}"></div>
                <div class="col-4"><label data-i18n="balance_amount">Amount</label>
                <input type="number" step="0.01" class="form-control" id="bcAmount" value="${certificate ? certificate.amount : ""}"></div>
                <div class="col-4"><label data-i18n="interest_rate">Interest Rate</label>
                <input type="number" step="0.0001" class="form-control" id="bcInterestRate" value="${certificate ? certificate.interest_rate : ""}"></div>
                <div class="col-4"><label data-i18n="interest_value">Interest Value</label>
                <input type="number" step="0.01" class="form-control" id="bcInterestValue" value="${certificate ? certificate.interest_value : ""}"></div>
                <div class="col-6">
                    <label data-i18n="frequency">Frequency</label>
                    <select class="form-select" id="bcFrequency">
                        <option value="" data-i18n="select_frequency">— Select Frequency —</option>
                        <option value="monthly" data-i18n="freq_monthly" ${certificate && certificate.frequency === "monthly" ? "selected" : ""}>Monthly</option>
                        <option value="quarterly" data-i18n="freq_quarterly" ${certificate && certificate.frequency === "quarterly" ? "selected" : ""}>Quarterly</option>
                        <option value="semi_annually" data-i18n="freq_semi_annually" ${certificate && certificate.frequency === "semi_annually" ? "selected" : ""}>Semi-Annually</option>
                        <option value="annually" data-i18n="freq_annually" ${certificate && certificate.frequency === "annually" ? "selected" : ""}>Annually</option>
                        <option value="at_maturity" data-i18n="freq_at_maturity" ${certificate && certificate.frequency === "at_maturity" ? "selected" : ""}>At Maturity</option>
                    </select>
                </div>
                <div class="col-6"><label data-i18n="notes">Notes</label>
                <textarea class="form-control" id="bcNotes" rows="2">${certificate ? certificate.notes : ""}</textarea></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveBankCertificate(${certificateId})" data-i18n="btn_save">Save</button>
        </div>`;
  showModal(html);
  applyTranslations();

  // --- ADD EVENT LISTENERS FOR LIVE CALCULATION ---
  const inputsToWatch = ["bcAmount", "bcInterestRate", "bcFrequency", "bcIssue", "bcExpiry"];
  inputsToWatch.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      // 'input' catches typing inside number boxes; 'change' handles dropdown modifications and datepickers
      el.addEventListener("input", calculateCertificateInterest);
      el.addEventListener("change", calculateCertificateInterest);
    }
  });

  // If editing an existing record, run it once to ensure correct validation display state
  if (certificateId) {
    calculateCertificateInterest();
  }
}

// Rewritten to return a formatted option string explicitly instead of interacting with DOM nodes mid-render
async function _getCertStatusOptions(currentStatus) {
  try {
    const res = await fetch("/api/cert-statuses/");
    const data = await res.json();
    const statuses = data.statuses || [];
    
    if (statuses.length === 0) {
      return ["Active", "Maturing", "Renewed", "Closed"]
        .map((s) => `<option value="${s}" ${s === (currentStatus || "Active") ? "selected" : ""}>${s}</option>`)
        .join("");
    } else {
      return statuses
        .map(
          (s) => `<option value="${s.name}" ${s.name === (currentStatus || "") || (!currentStatus && s.is_default) ? "selected" : ""}>${s.name}</option>`
        )
        .join("");
    }
  } catch (e) {
    // Fallback if API fails
    return ["Active", "Maturing", "Renewed", "Closed"]
      .map((s) => `<option value="${s}" ${s === (currentStatus || "Active") ? "selected" : ""}>${s}</option>`)
      .join("");
  }
}

function parseNumberInput(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const raw = el.value || "";
  const normalized = String(raw).replace(/,/g, "").trim();
  if (normalized === "") return null;
  const num = Number(normalized);
  return Number.isFinite(num) ? num : null;
}

async function saveBankCertificate(certificateId) {
  // Normalize certificateId to ensure "undefined" or "null" strings are treated as clean null
  let cleanId = certificateId;
  if (cleanId === "undefined" || cleanId === "null" || !cleanId) {
    cleanId = null;
  }

  const amount = parseNumberInput("bcAmount");
  const interestRate = parseNumberInput("bcInterestRate");
  const interestValue = parseNumberInput("bcInterestValue");
  
  const body = {
    status: document.getElementById("bcStatus").value.trim(),
    bank_id: parseInt(document.getElementById("bcBank").value, 10) || null,
    currency_id: parseInt(document.getElementById("bcCurrency").value, 10) || null,
    issue_date: document.getElementById("bcIssue").value || null,
    expiry_date: document.getElementById("bcExpiry").value || null,
    amount: amount === null ? 0 : amount,
    interest_rate: interestRate === null ? 0 : interestRate,
    interest_value: interestValue === null ? 0 : interestValue,
    frequency: document.getElementById("bcFrequency").value.trim(),
    notes: document.getElementById("bcNotes").value.trim(),
  };

  // Use the normalized cleanId variable here
  const url = cleanId
    ? `/api/bank-certificates/${cleanId}/`
    : "/api/bank-certificates/";
  const method = cleanId ? "PUT" : "POST";

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  
  if (res.ok) {
    closeModal();
    showToast("Bank Certificate saved ✓");
    renderBankCertificates();
    if (typeof renderBalanceEntries === "function") {
    renderBalanceEntries(); 
  }
  } else {
    const text = await res.text();
    console.error("Bank certificate save failed", res.status, text);
    showToast("Error saving certificate: " + (text || res.status), "error");
  }
}

async function deleteBankCertificate(certificateId) {
  if (!confirm("Delete this certificate?")) return;
  const res = await fetch(`/api/bank-certificates/${certificateId}/`, {
    method: "DELETE",
  });
  if (res.ok) {
    showToast("Deleted");
    renderBankCertificates();
  } else {
    showToast("Error deleting certificate", "error");
  }
}

function calculateCertificateInterest() {
  const amount = parseNumberInput("bcAmount") || 0;
  const rate = parseNumberInput("bcInterestRate") || 0; // e.g., 0.10 for 10%
  const frequency = document.getElementById("bcFrequency").value;
  
  // Calculate base yearly interest
  const yearlyInterest = amount * (rate/100);
  let computedValue = 0;

  if (yearlyInterest <= 0) {
    document.getElementById("bcInterestValue").value = "0.00";
    return;
  }

  switch (frequency) {
    case "monthly":
      computedValue = yearlyInterest / 12;
      break;
    case "quarterly":
      computedValue = yearlyInterest / 4;
      break;
    case "semi_annually":
      computedValue = yearlyInterest / 2;
      break;
    case "annually":
      computedValue = yearlyInterest;
      break;
    case "at_maturity":
      const issueDateVal = document.getElementById("bcIssue").value;
      const expiryDateVal = document.getElementById("bcExpiry").value;
      
      if (issueDateVal && expiryDateVal) {
        const issue = new Date(issueDateVal);
        const expiry = new Date(expiryDateVal);
        
        // Calculate total days between dates, converted to fractional years
        const diffTime = Math.max(0, expiry - issue);
        const diffDays = diffTime / (1000 * 60 * 60 * 24);
        const totalYears = diffDays / 365.25; // Accounting for leap years safely
        
        computedValue = yearlyInterest * totalYears;
      } else {
        computedValue = 0; // Can't calculate maturity return without clear dates
      }
      break;
    default:
      computedValue = 0;
  }

  // Populate field locked to standard financial decimal precision
  document.getElementById("bcInterestValue").value = computedValue.toFixed(2);
}