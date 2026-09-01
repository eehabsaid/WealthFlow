"use strict";

async function showBalanceModal(entryId) {
  let entry = null;
  if (entryId) {
    const res = await fetch("/api/balance/");
    const data = await res.json();
    entry = data.entries.find((e) => e.id === entryId);
  }

  const [purityRes] = await Promise.all([fetch("/api/settings/gold-purities/")]);
  const purityData = await purityRes.json();

  const bankOpts = _banks
    .map(
      (b) =>
        `<option value="${b.id}" ${entry && entry.bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");
  const curOpts = _currencies
    .map((c) => {
      // Match your existing JSON translation keys
      const key = c.code === "Gold" ? "type_gold" : c.code;

      // Get the translated name or fallback to the currency name
      let translatedName = _t && _t[key] ? _t[key] : `${c.code} - ${c.name}`;

      // Clean up any double emojis if your 'type_gold' translation already includes one (e.g., "🪙 Gold")
      if (c.code === "Gold" && _t && _t["type_gold"]) {
        translatedName = _t["type_gold"].replace(/[\u{1F300}-\u{1F9FF}]/gu, "").trim();
      }

      // Combine the flag/emoji with the translated currency label
      const displayName = `${c.flag || "💵"} ${translatedName}`;

      return `<option value="${c.id}" data-i18n="${key}" ${entry && entry.currency_id === c.id ? "selected" : ""}>${displayName}</option>`;
    })
    .join("");

  const typeOpts = `
        <option value="cash" data-i18n="type_cash" ${entry && entry.balance_type === "cash" ? "selected" : ""}>${t("type_cash", "💵 Cash")}</option>
        <option value="bank" data-i18n="type_bank" ${entry && entry.balance_type === "bank" ? "selected" : ""}>${t("type_bank", "🏦 Bank Account")}</option>
        <option value="gold" data-i18n="type_gold" ${entry && entry.balance_type === "gold" ? "selected" : ""}>${t("type_gold", "🪙 Gold")}</option>
        <option value="certificate" data-i18n="type_certificate" ${entry && entry.balance_type === "certificate" ? "selected" : ""}>${t("type_certificate", "📜 Certificate")}</option>
    `;

  const titleText = entry
    ? t("title_edit_balance", "Edit Balance Entry")
    : t("title_add_balance", "Add Balance Entry");
  const balanceTitleLabel = t("balance_title", "Title");
  const balanceTypeLabel = t("balance_type", "Balance Type");
  const balanceBankLabel = t("balance_bank", "Bank");
  const balanceCurrencyLabel = t("balance_currency", "Currency");
  const balanceAmountLabel = t("balance_amount", "Amount");
  const notesLabel = t("notes", "Notes");
  const purityLabel = t("purity", "Purity");
  const selectTypeText = t("select_type", "— Select Type —");
  const noneOptionText = t("none_option", "— None —");
  const cancelText = t("btn_cancel", "Cancel");
  const saveText = t("btn_save", "Save");

  const purityOpts = (purityData.items || [])
    .filter((p) => p.is_active)
    .map(
      (p) =>
        `<option value="${p.key}" ${entry && String(entry.purity || "").toLowerCase() === String(p.key || "").toLowerCase() ? "selected" : ""}>${p.label || p.key}</option>`
    )
    .join("");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${entry ? "title_edit_balance" : "title_add_balance"}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12"><label data-i18n="balance_title">${balanceTitleLabel}</label><input type="text" class="form-control" id="bTitle" value="${entry ? entry.title : ""}"></div>
                <div class="col-12"><label data-i18n="balance_type">${balanceTypeLabel}</label><select class="form-select" id="bbalance_type"><option value="" data-i18n="select_type">${selectTypeText}</option>${typeOpts}</select></div>
                <div class="col-6"><label data-i18n="balance_bank">${balanceBankLabel}</label><select class="form-select" id="bBank"><option value="" data-i18n="none_option">${noneOptionText}</option>${bankOpts}</select></div>
                <div class="col-3"><label data-i18n="balance_currency">${balanceCurrencyLabel}</label><select class="form-select" id="bCurrency">${curOpts}</select></div>
                <div class="col-3"><label data-i18n="balance_amount">${balanceAmountLabel}</label><input type="number" step="0.01" class="form-control" id="bAmount" value="${entry ? entry.amount : ""}"></div>
                <div class="col-4" id="bPurityWrap"><label data-i18n="purity">${purityLabel}</label><select class="form-select" id="bPurity"><option value="">--</option>${purityOpts}</select></div>
                <div class="col-12"><label data-i18n="notes">${notesLabel}</label><input type="text" class="form-control" id="bNotes" value="${entry ? entry.notes : ""}"></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveBalanceEntry(${entryId})" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

  showModal(html);

  const typeEl = document.getElementById("bbalance_type");
  const purityWrap = document.getElementById("bPurityWrap");
  const currencyEl = document.getElementById("bCurrency");

  function toggleGoldFields() {
    const isGold = typeEl && typeEl.value === "gold";
    if (purityWrap) purityWrap.style.display = isGold ? "" : "none";

    if (isGold && currencyEl) {
      const goldOption = Array.from(currencyEl.options).find((opt) =>
        (opt.textContent || "").toLowerCase().includes("gold")
      );
      if (goldOption) currencyEl.value = goldOption.value;
    }
  }

  if (typeEl) typeEl.addEventListener("change", toggleGoldFields);
  toggleGoldFields();

  applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & DELETE
// ════════════════════════════════════════════════════════════════════════════
