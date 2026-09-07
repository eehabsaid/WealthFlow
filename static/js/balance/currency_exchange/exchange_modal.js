"use strict";
// Add/edit exchange modal.
// Part of the balance module (split from the former monolithic
// currency_exchange.js, 200-line rule). Do not edit directly.

async function showExchangeModal(id = null) {
  _editingExchangeId = id;
  const isEdit = id !== null;

  try {
    const optRes = await fetch("/api/currency-exchanges/options/");
    if (!optRes.ok) throw new Error(t("error_loading_options", "Failed to load exchange options"));
    _exchangeFormOptions = await optRes.json();
  } catch (e) {
    showToast(e.message, "danger");
    return;
  }

  let ex = {
    exchange_date: new Date().toISOString().split("T")[0],
    from_balance_id: "",
    to_balance_id: "",
    from_amount: "",
    exchange_rate: "",
    to_amount: "",
    notes: "",
  };

  if (isEdit) {
    ex = _currencyExchangesData.find((x) => x.id === id) || ex;
  }

  const titleText = isEdit
    ? t("edit_exchange", "Edit Currency Exchange")
    : t("new_exchange", "New Currency Exchange");
  const cancelText = t("btn_cancel", "Cancel");
  const saveText = t("btn_save", "Save");

  const balances = _exchangeFormOptions.balances || [];
  const sourceOptions = balances
    .map((b) => `<option value="${b.id}">${getTranslatedBalanceTitle(b)}</option>`)
    .join("");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${isEdit ? "edit_exchange" : "new_exchange"}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="exchangeForm" onsubmit="event.preventDefault(); saveExchange();">
                <div class="row g-3">
                    <div class="col-12">
                        <label class="form-label font-weight-bold" data-i18n="from_balance">${t("from_balance", "Source Balance")}</label>
                        <select class="form-select" id="ce_from_balance" required onchange="calculateBackendExchange()">
                            <option value="" selected data-i18n="select_source_balance">${t("select_source_balance", "Select Source Balance...")}</option>
                            ${sourceOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label class="form-label" data-i18n="from_currency">${t("from_currency", "From Currency")}</label>
                        <input type="text" class="form-control" id="ce_from_currency" readonly style="background:var(--bg-primary);cursor:not-allowed;">
                    </div>

                    <div class="col-6">
                        <label class="form-label" data-i18n="available_balance">${t("available_balance", "Available Balance")}</label>
                        <input type="text" class="form-control text-end" id="ce_available_balance" readonly style="background:var(--bg-primary);font-weight:700;cursor:not-allowed;">
                    </div>

                    <div class="col-12">
                        <label class="form-label font-weight-bold" data-i18n="amount_to_exchange">${t("amount_to_exchange", "Amount to Exchange")}</label>
                        <div class="input-group">
                            <input type="number" step="0.01" class="form-control" id="ce_from_amount" required min="0.01" oninput="calculateBackendExchange()">
                            <span class="input-group-text" id="ce_from_curr_label">-</span>
                        </div>
                    </div>

                    <hr class="my-2" style="border-color:var(--border-color);">

                    <div class="col-12">
                        <label class="form-label font-weight-bold" data-i18n="to_balance">${t("to_balance", "Destination Balance")}</label>
                        <select class="form-select" id="ce_to_balance" required onchange="calculateBackendExchange()">
                            <option value="" selected data-i18n="select_destination_balance">${t("select_destination_balance", "Select Destination Balance...")}</option>
                            ${sourceOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label class="form-label" data-i18n="to_currency">${t("to_currency", "To Currency")}</label>
                        <input type="text" class="form-control" id="ce_to_currency" readonly style="background:var(--bg-primary);cursor:not-allowed;">
                    </div>

                    <div class="col-6">
                        <label class="form-label" data-i18n="exchange_rate">${t("exchange_rate", "Exchange Rate")}</label>
                        <input type="number" step="0.000001" class="form-control text-end" id="ce_rate" required oninput="calculateBackendExchange(true)">
                    </div>

                    <div class="col-12">
                        <label class="form-label font-weight-bold" data-i18n="amount_to_receive">${t("amount_to_receive", "Amount to Receive")}</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-end font-weight-bold" id="ce_to_amount" readonly style="background:var(--bg-primary);cursor:not-allowed;font-size:1.1rem;color:var(--accent-primary);">
                            <span class="input-group-text" id="ce_to_curr_label">-</span>
                        </div>
                    </div>

                    <div class="col-12">
                        <label class="form-label" data-i18n="date">${t("date", "Date")}</label>
                        <input type="date" class="form-control" id="ce_date" required>
                    </div>

                    <div class="col-12">
                        <label class="form-label" data-i18n="notes">${t("notes", "Notes")}</label>
                        <input type="text" class="form-control" id="ce_notes">
                    </div>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button type="submit" form="exchangeForm" class="btn-primary-custom" id="saveExchangeBtn" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

  showModal(html);

  document.getElementById("ce_date").value = ex.exchange_date;
  document.getElementById("ce_notes").value = ex.notes;
  if (ex.from_amount) document.getElementById("ce_from_amount").value = ex.from_amount;
  if (ex.exchange_rate) document.getElementById("ce_rate").value = ex.exchange_rate;

  if (ex.from_balance_id) document.getElementById("ce_from_balance").value = ex.from_balance_id;
  if (ex.to_balance_id) document.getElementById("ce_to_balance").value = ex.to_balance_id;

  if (ex.from_balance_id) {
    calculateBackendExchange();
  }

  applyTranslations();
}

