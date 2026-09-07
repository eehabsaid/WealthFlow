"use strict";
// Table filters + filtered table re-render.
// Part of the balance module (split from the former monolithic
// currency_exchange.js, 200-line rule). Do not edit directly.

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
