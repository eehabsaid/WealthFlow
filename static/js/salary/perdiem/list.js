"use strict";

async function showPerDiemListModal(companyId, year) {
  if (!year) {
    year =
      parseInt(document.querySelector(".year-pill.active")?.textContent) ||
      new Date().getFullYear();
  }

  // Show spinner while loading
  showModal(
    '<div class="modal-body text-center py-5"><div class="spinner-border text-primary"></div></div>'
  );

  try {
    const [pdRes, bRes] = await Promise.all([
      fetch(`/api/per-diems/?company_id=${companyId}&year=${year}`),
      fetch("/api/banks/"),
    ]);
    const pdData = await pdRes.json();
    const bData = await bRes.json();

    const perDiems = pdData.entries || [];
    const banks = bData.banks || [];

    const modalHtml = `
            <div class="modal-header">
                <h5 class="modal-title" data-i18n="per_diem_list">Per Diem List</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div style="display:flex; align-items:center; gap:8px">
                        <label data-i18n="currency_filter" style="margin-bottom:0">Currency Filter</label>
                        <select class="form-select form-select-sm" id="pdCurrencyFilter" style="width:120px" onchange="filterPerDiems()">
                            <option value="ALL" data-i18n="all_option">All</option>
                        </select>
                    </div>
                    <button class="btn btn-primary btn-sm btn-primary-custom" onclick="showPerDiemFormModal(null, ${companyId}, ${year})" data-i18n="add_per_diem">
                        <i class="bi bi-plus-lg"></i> Add Per Diem
                    </button>
                </div>
                
                <div class="table-container" style="max-height: 400px; overflow-y: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th data-i18n="date">Date</th>
                                <th data-i18n="currency">Currency</th>
                                <th class="text-end" data-i18n="amount_label">Amount</th>
                                <th class="text-end" data-i18n="amount_egp">Amount (EGP)</th>
                                <th data-i18n="received_in">Received In</th>
                                <th data-i18n="notes">Notes</th>
                                <th data-i18n="actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="perDiemTableBody">
                        </tbody>
                        <tfoot id="perDiemTableFoot">
                        </tfoot>
                    </table>
                </div>
            </div>
        `;

    showModal(modalHtml);

    // Populate Currency Filter
    const filterSelect = document.getElementById("pdCurrencyFilter");
    const uniqueCurrencies = [...new Set(perDiems.map((pd) => pd.currency_code))];
    uniqueCurrencies.forEach((code) => {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = code;
      filterSelect.appendChild(opt);
    });

    window._currentPerDiems = perDiems;
    window._currentBanks = banks;
    window._currentCompanyId = companyId;
    window._currentYear = year;

    filterPerDiems();
  } catch (e) {
    showToast("Failed to load Per Diem data", "error");
  }
}

function filterPerDiems() {
  const filterVal = document.getElementById("pdCurrencyFilter").value;
  const pds = window._currentPerDiems || [];

  const filtered = filterVal === "ALL" ? pds : pds.filter((pd) => pd.currency_code === filterVal);

  const tbody = document.getElementById("perDiemTableBody");
  const tfoot = document.getElementById("perDiemTableFoot");
  if (!tbody) return;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center" data-i18n="no_records">No records found</td></tr>`;
    tfoot.innerHTML = "";
    applyTranslations();
    return;
  }

  tbody.innerHTML = filtered
    .map(
      (pd) => `
        <tr>
            <td>${pd.date}</td>
            <td>${pd.currency_flag} ${pd.currency_code}</td>
            <td class="text-end">${fmt(pd.amount)}</td>
            <td class="text-end amt-positive">${fmt(pd.amount_egp)}</td>
            <td>${pd.bank_name ? pd.bank_name : `<span class="badge bg-secondary" style="font-weight: normal;" data-i18n="cash_option">${t("cash_option", "Cash")}</span>`}</td>
            <td>${pd.notes || ""}</td>
            <td>
                <button class="btn-icon" onclick="showPerDiemFormModal(${pd.id}, ${window._currentCompanyId}, ${window._currentYear})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deletePerDiem(${pd.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `
    )
    .join("");

  let sumAmount = 0;
  let sumEgp = 0;
  filtered.forEach((pd) => {
    sumAmount += pd.amount;
    sumEgp += pd.amount_egp;
  });

  const displayAmount = filterVal === "ALL" ? "—" : fmt(sumAmount);

  tfoot.innerHTML = `
        <tr style="font-weight:bold; background: rgba(13, 110, 253, 0.05)">
            <td colspan="2" data-i18n="totals">Totals</td>
            <td class="text-end">${displayAmount}</td>
            <td class="text-end amt-positive">${fmt(sumEgp)}</td>
            <td colspan="3"></td>
        </tr>
    `;

  applyTranslations();
}
