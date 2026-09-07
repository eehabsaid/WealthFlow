"use strict";
// Currency Exchange tab main renderer.
// Part of the balance module (split from the former monolithic
// currency_exchange.js, 200-line rule). Do not edit directly.

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

