"use strict";

async function showExpenseModal(expId) {
  let exp = null;
  if (expId) {
    const res = await fetch("/api/expenses/?");
    const all = (await res.json()).entries || [];
    exp = all.find((e) => e.id === expId) || null;
  }

  const cats = window._expCategories || [];
  const curs = window._expCurrencies || [];
  const banks = window._expBanks || [];
  const today = new Date().toISOString().split("T")[0];

  const catOpts = cats
    .map(
      (c) =>
        `<option value="${c.id}" ${exp && exp.category_id === c.id ? "selected" : ""}>${c.icon} ${c.name}</option>`
    )
    .join("");
  const curOpts = curs
    .map(
      (c) =>
        `<option value="${c.id}" ${exp && exp.currency_code === c.code ? "selected" : c.code === "EGP" ? "selected" : ""}>${c.flag} ${c.code}</option>`
    )
    .join("");
  const methOpts = PAYMENT_METHODS.map(
    (m) =>
      `<option value="${m.value}" ${exp && exp.payment_method === m.value ? "selected" : ""} data-i18n="${m.key}">${m.value}</option>`
  ).join("");
  const bankOpts = banks
    .map(
      (b) =>
        `<option value="${b.id}" ${exp && exp.bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");

  if (exp && exp.is_readonly) {
    showReadonlyExpenseModal(exp);
    return;
  }

  showModal(`
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="${exp ? "edit_expense" : "add_expense"}">${exp ? "Edit" : "Add"} Expense</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body"><div class="row g-3">
      <div class="col-sm-6">
        <label class="form-label"><span data-i18n="date">Date</span> *</label>
        <input type="date" class="form-control" id="eDate" value="${exp ? exp.date : today}">
      </div>
      <div class="col-sm-6">
        <label class="form-label"><span data-i18n="amount">Amount</span> *</label>
        <input type="number" step="0.01" min="0" class="form-control" id="eAmount"
               value="${exp ? exp.amount : ""}">
      </div>
      <div class="col-sm-6">
        <label class="form-label" data-i18n="category">Category</label>
        <select class="form-select" id="eCat" onchange="updateSubcategories()">${catOpts}</select>
      </div>
      <div class="col-sm-6">
        <label class="form-label" data-i18n="subcategory">Subcategory</label>
        <select class="form-select" id="eSubcat">
          <option value="" data-i18n="none_option">— None —</option>
        </select>
      </div>
      <div class="col-12">
        <label class="form-label" data-i18n="description">Description</label>
        <input type="text" class="form-control" id="eDesc"
               value="${exp ? exp.description : ""}" placeholder="What was this expense?" data-i18n-placeholder="expense_description_placeholder">
      </div>
      <div class="col-sm-6">
        <label class="form-label" data-i18n="payment_method">Payment Method</label>
        <select class="form-select" id="eMethod" onchange="toggleExpenseBankField()">${methOpts}</select>
      </div>
      <div class="col-sm-6 d-none" id="eBankWrap">
        <label class="form-label"><span data-i18n="bank_account">Bank Account</span> *</label>
        <select class="form-select" id="eBank">
          <option value="" data-i18n="select_bank_account">Select bank account</option>
          ${bankOpts}
        </select>
      </div>
      <div class="col-sm-6">
        <label class="form-label" data-i18n="currency">Currency</label>
        <select class="form-select" id="eCurrency">${curOpts}</select>
      </div>
      <div class="col-12">
        <label class="form-label" data-i18n="notes">Notes</label>
        <textarea class="form-control" id="eNotes" rows="2">${exp ? exp.notes : ""}</textarea>
      </div>
    </div></div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()" data-i18n="btn_cancel">Cancel</button>
      <button class="btn-primary-custom" onclick="saveExpense(${expId || "null"})" data-i18n="btn_save">Save</button>
    </div>`);

  // Populate subcategories
  updateSubcategories(exp ? exp.subcategory_id : null);
  toggleExpenseBankField();
  applyTranslations();
}

/* ── Read-only view for asset-mirrored expenses ────────────────── */

function showReadonlyExpenseModal(exp) {
  const sourceLabels = {
    asset_renovation: t("asset_renovation", "Asset Renovation"),
    asset_acquisition_cost: t("asset_acquisition_cost", "Asset Acquisition Cost"),
    asset_furniture: t("asset_furniture", "Asset Furniture"),
  };
  const sourceLabel =
    sourceLabels[exp.source_type] || t("linked_asset_record", "Linked to a fixed asset record");

  showModal(`
    <div class="modal-header">
      <h5 class="modal-title"><i class="bi bi-lock"></i> <span data-i18n="linked_expense">Linked Expense</span></h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
    </div>
    <div class="modal-body">
      <div class="alert alert-info" style="font-size:13px" data-i18n="readonly_mirrored_expense_notice">
        This expense is generated automatically from a fixed asset record and can't be edited or deleted here. Edit or delete the source record on the asset instead.
      </div>
      <div class="row g-3">
        <div class="col-sm-6">
          <label class="form-label" data-i18n="date">Date</label>
          <div class="form-control-plaintext">${formatDate(exp.date)}</div>
        </div>
        <div class="col-sm-6">
          <label class="form-label" data-i18n="amount">Amount</label>
          <div class="form-control-plaintext">${fmt(exp.amount)} ${exp.currency_code || "EGP"}</div>
        </div>
        <div class="col-sm-6">
          <label class="form-label" data-i18n="category">Category</label>
          <div class="form-control-plaintext">${exp.category_icon || ""} ${exp.category_name || "—"}</div>
        </div>
        <div class="col-sm-6">
          <label class="form-label" data-i18n="subcategory">Subcategory</label>
          <div class="form-control-plaintext">${exp.subcategory_name || "—"}</div>
        </div>
        <div class="col-12">
          <label class="form-label" data-i18n="description">Description</label>
          <div class="form-control-plaintext">${exp.description || "—"}</div>
        </div>
        <div class="col-sm-6">
          <label class="form-label" data-i18n="payment_method">Payment Method</label>
          <div class="form-control-plaintext">${exp.payment_method || "—"}</div>
        </div>
        <div class="col-sm-6">
          <label class="form-label" data-i18n="source">Source</label>
          <div class="form-control-plaintext">${sourceLabel}</div>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()" data-i18n="btn_close">Close</button>
    </div>`);
  applyTranslations();
}

function isExpenseBankRequired(methodValue) {
  const normalized = String(methodValue || "")
    .trim()
    .toLowerCase();
  return normalized === "bank" || normalized === "bank transfer" || normalized === "card";
}

function toggleExpenseBankField() {
  const methodEl = document.getElementById("eMethod");
  const bankWrap = document.getElementById("eBankWrap");
  const bankEl = document.getElementById("eBank");
  if (!methodEl || !bankWrap || !bankEl) return;

  const required = isExpenseBankRequired(methodEl.value);
  bankWrap.classList.toggle("d-none", !required);
  bankEl.required = required;
  if (!required) {
    bankEl.value = "";
  }
}
