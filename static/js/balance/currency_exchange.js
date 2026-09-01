"use strict";

// balance/currency_exchange.js — Currency Exchange tab renderer & interactions
// All calculations, conversions, validations, options, and reversals are done in Django backend.
// ════════════════════════════════════════════════════════════════════════════

let _currencyExchangesData = [];
let _editingExchangeId = null;
let _exchangeFormOptions = { balances: [], currencies: [] };

function getTranslatedBalanceTitle(b) {
  if (!b) return "";
  const rawTitle = b.title || "";
  if (typeof _t !== "undefined" && _t && _t[rawTitle]) {
    return _t[rawTitle];
  }
  let title = rawTitle;

  // Strip duplicate trailing (BANK_NAME) or (CURRENCY_CODE) from title if present
  if (b.bank_name) {
    const dupBank = new RegExp(`\\s*\\(${b.bank_name}\\)\\s*$`, "i");
    title = title.replace(dupBank, "");
  }
  if (b.currency_code) {
    const dupCurr = new RegExp(`\\s*\\(${b.currency_code}\\)\\s*$`, "i");
    title = title.replace(dupCurr, "");
  }

  if (typeof t === "function") {
    title = title
      .replace(/Bank Account Balance/gi, t("bank_account_balance", "Bank Account Balance"))
      .replace(/Bank Account/gi, t("bank_account", "Bank Account"))
      .replace(/Home Balance/gi, t("home_balance", "Home Balance"))
      .replace(/Cash/gi, t("label_cash", "Cash"))
      .replace(/Wallet/gi, t("wallet", "Wallet"));
  }

  let bankStr = "";
  if (b.bank_name && !title.toLowerCase().includes(b.bank_name.toLowerCase())) {
    bankStr = ` (${b.bank_name})`;
  }
  return `${title}${bankStr} - ${b.currency_code}`;
}

async function renderBalanceCurrencyExchange(data) {
  const pane = document.getElementById("bal-pane-currency_exchange");
  if (!pane) return;

  _currencyExchangesData = data.exchanges || [];

  const dateText = t("date", "Date");
  const fromText = t("from_balance", "Source Balance");
  const fromAmtText = t("amount_exchanged", "Amount Exchanged");
  const toText = t("to_balance", "Destination Balance");
  const toAmtText = t("amount_received", "Amount Received");
  const rateText = t("exchange_rate", "Exchange Rate");
  const userText = t("user", "User");
  const statusText = t("status", "Status");
  const notesText = t("notes", "Notes");
  const actionsText = t("actions", "Actions");
  const newExchText = t("new_exchange", "New Exchange");
  const noExchText = t("no_exchanges_found", "No exchange transactions found.");
  const editText = t("edit", "Edit");
  const deleteText = t("delete", "Delete");

  let rowsHtml = "";

  if (_currencyExchangesData.length === 0) {
    rowsHtml = `<tr><td colspan="10" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_exchanges_found">${noExchText}</td></tr>`;
  } else {
    rowsHtml = _currencyExchangesData
      .map((ex) => {
        const statusLabel =
          ex.status === "ACTIVE"
            ? t("status_active", "Active")
            : ex.status === "REVERSED"
              ? t("status_reversed", "Reversed")
              : t("status_edited", "Edited");

        const isReversed = ex.status === "REVERSED";

        return `
                <tr style="${isReversed ? "opacity:0.65;text-decoration:line-through;" : ""}">
                    <td>${formatDate(ex.exchange_date)}</td>
                    <td>${ex.from_balance_title}</td>
                    <td class="text-end amt-negative num-fmt" data-value="${ex.from_amount}">
                        ${fmt(ex.from_amount)} <small class="text-muted">${ex.from_currency_code}</small>
                    </td>
                    <td>${ex.to_balance_title}</td>
                    <td class="text-end amt-positive num-fmt" data-value="${ex.to_amount}">
                        ${fmt(ex.to_amount)} <small class="text-muted">${ex.to_currency_code}</small>
                    </td>
                    <td class="text-end font-monospace">${ex.exchange_rate}</td>
                    <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${statusLabel}</span></td>
                    <td><small>${ex.user_username || "System"}</small></td>
                    <td class="text-truncate" style="max-width: 130px;" title="${ex.notes}">${ex.notes || "-"}</td>
                    <td>
                        ${
                          !isReversed
                            ? `
                            <button class="btn-icon" onclick="showExchangeModal(${ex.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                            <button class="btn-icon del" onclick="deleteExchange(${ex.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                        `
                            : '<span class="text-muted">-</span>'
                        }
                    </td>
                </tr>
            `;
      })
      .join("");
  }

  pane.innerHTML = `
        <div class="d-flex justify-content-end align-items-center mb-3">
            <button class="btn-primary-custom" onclick="showExchangeModal()">
                <i class="bi bi-plus-lg me-1"></i>
                <span data-i18n="new_exchange">${newExchText}</span>
            </button>
        </div>

        <!-- Search & Filter Bar -->
        <div class="card mb-3 border-0" style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:10px;padding:12px;">
            <div class="row g-2 align-items-center">
                <div class="col-md-3">
                    <input type="text" id="ce_filter_search" class="form-control form-control-sm" placeholder="${t("search", "Search...")}" data-i18n-placeholder="search" oninput="filterCurrencyExchanges()">
                </div>
                <div class="col-md-3">
                    <select id="ce_filter_status" class="form-select form-select-sm" onchange="filterCurrencyExchanges()">
                        <option value="ALL" data-i18n="all_statuses">${t("all_statuses", "All Statuses")}</option>
                        <option value="ACTIVE" data-i18n="status_active">${t("status_active", "Active")}</option>
                        <option value="REVERSED" data-i18n="status_reversed">${t("status_reversed", "Reversed")}</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <input type="date" id="ce_filter_date" class="form-control form-control-sm" onchange="filterCurrencyExchanges()">
                </div>
                <div class="col-md-2">
                    <button class="btn btn-sm btn-outline-primary text-white w-100" style="font-weight:600;" onclick="resetCurrencyExchangeFilters()" data-i18n="reset">${t("reset", "Reset")}</button>
                </div>
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="date">${dateText}</th>
                            <th data-i18n="from_balance">${fromText}</th>
                            <th class="text-end" data-i18n="amount_exchanged">${fromAmtText}</th>
                            <th data-i18n="to_balance">${toText}</th>
                            <th class="text-end" data-i18n="amount_received">${toAmtText}</th>
                            <th class="text-end" data-i18n="exchange_rate">${rateText}</th>
                            <th data-i18n="status">${statusText}</th>
                            <th data-i18n="user">${userText}</th>
                            <th data-i18n="notes">${notesText}</th>
                            <th data-i18n="actions">${actionsText}</th>
                        </tr>
                    </thead>
                    <tbody id="currencyExchangesTableBody">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;

  applyTranslations();
}

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

async function calculateBackendExchange(isUserRateChange = false) {
  const fromId = document.getElementById("ce_from_balance")?.value;
  const toId = document.getElementById("ce_to_balance")?.value;
  const fromAmt = document.getElementById("ce_from_amount")?.value || 0;
  const userRate = isUserRateChange ? document.getElementById("ce_rate")?.value || null : null;

  if (!fromId) return;

  try {
    const payload = {
      from_balance_id: fromId,
      to_balance_id: toId,
      from_amount: fromAmt,
      exchange_rate: userRate,
    };

    const res = await fetch("/api/currency-exchanges/calculate/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) return;

    const calc = await res.json();

    const fromCurrEl = document.getElementById("ce_from_currency");
    const availEl = document.getElementById("ce_available_balance");
    const fromLbl = document.getElementById("ce_from_curr_label");
    const toCurrEl = document.getElementById("ce_to_currency");
    const rateEl = document.getElementById("ce_rate");
    const toAmtEl = document.getElementById("ce_to_amount");
    const toLbl = document.getElementById("ce_to_curr_label");

    if (fromCurrEl) fromCurrEl.value = `${calc.from_currency_flag} ${calc.from_currency_code}`;
    if (availEl) availEl.value = `${fmt(calc.available_balance)} ${calc.from_currency_code}`;
    if (fromLbl) fromLbl.textContent = calc.from_currency_code;

    if (toCurrEl && calc.to_currency_code)
      toCurrEl.value = `${calc.to_currency_flag} ${calc.to_currency_code}`;
    if (toLbl && calc.to_currency_code) toLbl.textContent = calc.to_currency_code;

    if (rateEl && !isUserRateChange) {
      rateEl.value = calc.exchange_rate;
    }

    if (toAmtEl) {
      toAmtEl.value = fmt(calc.to_amount);
    }
  } catch (e) {
    console.error("Backend calculation failed", e);
  }
}

async function saveExchange() {
  const btn = document.getElementById("saveExchangeBtn");
  if (btn) btn.disabled = true;

  const payload = {
    exchange_date: document.getElementById("ce_date").value,
    from_balance_id: document.getElementById("ce_from_balance").value,
    to_balance_id: document.getElementById("ce_to_balance").value,
    from_amount: document.getElementById("ce_from_amount").value,
    exchange_rate: document.getElementById("ce_rate").value,
    notes: document.getElementById("ce_notes").value,
  };

  try {
    const url = _editingExchangeId
      ? `/api/currency-exchanges/${_editingExchangeId}/`
      : "/api/currency-exchanges/";
    const method = _editingExchangeId ? "PUT" : "POST";

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      const errMsg = err.error
        ? t(err.error, err.error)
        : t("error_failed_to_save", "Failed to save exchange");
      throw new Error(errMsg);
    }

    if (typeof closeModal === "function") closeModal();
    showToast(t("success_saved", "Saved successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteExchange(id) {
  if (
    !confirm(
      t(
        "confirm_delete",
        "Are you sure you want to delete this exchange transaction? It will be reversed automatically."
      )
    )
  )
    return;
  try {
    const res = await fetch(`/api/currency-exchanges/${id}/`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Delete failed");
    }

    showToast(t("success_reversed", "Transaction reversed successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  }
}

function filterCurrencyExchanges() {
  const query = (document.getElementById("ce_filter_search")?.value || "").toLowerCase();
  const status = document.getElementById("ce_filter_status")?.value || "ALL";
  const date = document.getElementById("ce_filter_date")?.value || "";

  const filtered = _currencyExchangesData.filter((ex) => {
    const matchStatus = status === "ALL" || ex.status === status;
    const matchDate = !date || ex.exchange_date === date;
    const text =
      `${ex.from_balance_title} ${ex.to_balance_title} ${ex.from_currency_code} ${ex.to_currency_code} ${ex.notes}`.toLowerCase();
    const matchQuery = !query || text.includes(query);
    return matchStatus && matchDate && matchQuery;
  });

  renderFilteredCurrencyExchangesTable(filtered);
}

function resetCurrencyExchangeFilters() {
  if (document.getElementById("ce_filter_search"))
    document.getElementById("ce_filter_search").value = "";
  if (document.getElementById("ce_filter_status"))
    document.getElementById("ce_filter_status").value = "ALL";
  if (document.getElementById("ce_filter_date"))
    document.getElementById("ce_filter_date").value = "";
  renderFilteredCurrencyExchangesTable(_currencyExchangesData);
}

function renderFilteredCurrencyExchangesTable(list) {
  const tbody = document.getElementById("currencyExchangesTableBody");
  if (!tbody) return;

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_exchanges_found">${t("no_exchanges_found", "No exchange transactions found.")}</td></tr>`;
    return;
  }

  tbody.innerHTML = list
    .map((ex) => {
      const statusLabel =
        ex.status === "ACTIVE"
          ? t("status_active", "Active")
          : ex.status === "REVERSED"
            ? t("status_reversed", "Reversed")
            : t("status_edited", "Edited");

      const isReversed = ex.status === "REVERSED";

      return `
            <tr style="${isReversed ? "opacity:0.65;text-decoration:line-through;" : ""}">
                <td>${formatDate(ex.exchange_date)}</td>
                <td>${ex.from_balance_title}</td>
                <td class="text-end amt-negative num-fmt" data-value="${ex.from_amount}">
                    ${fmt(ex.from_amount)} <small class="text-muted">${ex.from_currency_code}</small>
                </td>
                <td>${ex.to_balance_title}</td>
                <td class="text-end amt-positive num-fmt" data-value="${ex.to_amount}">
                    ${fmt(ex.to_amount)} <small class="text-muted">${ex.to_currency_code}</small>
                </td>
                <td class="text-end font-monospace">${ex.exchange_rate}</td>
                <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${statusLabel}</span></td>
                <td><small>${ex.user_username || "System"}</small></td>
                <td class="text-truncate" style="max-width: 130px;" title="${ex.notes}">${ex.notes || "-"}</td>
                <td>
                    ${
                      !isReversed
                        ? `
                        <button class="btn-icon" onclick="showExchangeModal(${ex.id})" title="${t("edit", "Edit")}"><i class="bi bi-pencil"></i></button>
                        <button class="btn-icon del" onclick="deleteExchange(${ex.id})" title="${t("delete", "Delete")}"><i class="bi bi-trash"></i></button>
                    `
                        : '<span class="text-muted">-</span>'
                    }
                </td>
            </tr>
        `;
    })
    .join("");

  applyTranslations();
}

window.renderBalanceCurrencyExchange = renderBalanceCurrencyExchange;
window.showExchangeModal = showExchangeModal;
window.calculateBackendExchange = calculateBackendExchange;
window.saveExchange = saveExchange;
window.deleteExchange = deleteExchange;
window.filterCurrencyExchanges = filterCurrencyExchanges;
window.resetCurrencyExchangeFilters = resetCurrencyExchangeFilters;
