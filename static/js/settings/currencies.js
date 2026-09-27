"use strict";
// Currency configuration settings
// This file is part of the settings module. Do not edit directly.

async function renderCurrencySettings() {
  const [res, settingsRes] = await Promise.all([
    fetch("/api/currencies/"),
    fetch("/api/settings/"),
  ]);
  const { currencies = [] } = await res.json();
  const settingsData = await settingsRes.json().catch(() => ({}));
  const multiCurrencyEnabled =
    (settingsData?.settings?.multi_currency_enabled ?? "true") !== "false";

  const rows = currencies
    .map(
      (c) => `
        <tr>
            <td style="font-size:20px">${c.flag}</td>
            <td><code style="color:var(--accent-primary);font-weight:700">${c.code}</code></td>
            <td>${c.symbol || "—"}</td>
            <td>${c.name}</td>
            <td>${
              c.is_default
                ? `<span class="badge bg-success" data-i18n="currency_default_badge">${t("currency_default_badge", "Default")}</span>`
                : c.can_be_default === false
                  ? "—"
                  : `<button class="btn-secondary-custom" style="padding:2px 10px;font-size:12px" onclick="setDefaultCurrency('${c.code}')" data-i18n="currency_default_set">${t("currency_default_set", "Set as default")}</button>`
            }</td>
            <td>
                <button class="btn-icon" onclick="showCurrencyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                ${c.is_default ? "" : `<button class="btn-icon del" onclick="deleteCurrency(${c.id})"><i class="bi bi-trash"></i></button>`}
            </td>
        </tr>`
    )
    .join("");

  const contentEl = document.getElementById("settingsContent");
  if (!contentEl) return;
  contentEl.innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;padding:14px;margin-bottom:14px;display:flex;
                    justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
            <div>
                <div style="font-weight:600" data-i18n="multi_currency_toggle_label">${t("multi_currency_toggle_label", "Allow users to choose a non-default currency")}</div>
                <div style="font-size:12px;color:var(--text-secondary)" data-i18n="multi_currency_toggle_hint">${t("multi_currency_toggle_hint", "When off, every user is locked to the platform's default currency.")}</div>
            </div>
            <div class="form-check form-switch" style="margin:0">
                <input class="form-check-input" type="checkbox" role="switch" id="multiCurrencyToggle"
                    ${multiCurrencyEnabled ? "checked" : ""} onchange="setMultiCurrencyEnabled(this.checked)">
            </div>
        </div>
        <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:14px">
            
            <button class="btn-primary-custom" onclick="showCurrencyModal(null)" data-i18n="add_currency">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="currency_flag">Flag</th>
                    <th data-i18n="currency_code">Code</th>
                    <th data-i18n="currency_symbol">Symbol</th>
                    <th data-i18n="currency_name">Name</th>
                    <th data-i18n="currency_default_col">Default</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>
        <div style="margin-top:14px;font-size:13px;color:var(--text-secondary)"
            data-i18n="currency_settings_desc"></div>`;
  applyTranslations();
}

async function showCurrencyModal(currencyId) {
  let c = null;
  if (currencyId) {
    const res = await fetch(`/api/currencies/${currencyId}/`);
    c = await res.json();
  }
  const titleText = c
    ? typeof t === "function"
      ? t("edit_currency", "Edit Currency")
      : "Edit Currency"
    : typeof t === "function"
      ? t("add_currency", "Add Currency")
      : "Add Currency";
  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${c ? "edit_currency" : "add_currency"}">${titleText}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">

            <div class="row g-3">
                <div class="col-4">
                    <label data-i18n="currency_code">Code</label>
                    <input class="form-control" id="curCode" value="${c?.code || ""}" placeholder="USD">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_symbol">Symbol</label>
                    <input class="form-control" id="curSymbol" value="${c?.symbol || ""}" placeholder="$">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_flag">Flag</label>
                    <input class="form-control" id="curFlag" value="${c?.flag || "💱"}" placeholder="🇺🇸" maxlength="5">
                </div>
                <div class="col-12">
                    <label data-i18n="currency_name">Name</label>
                    <input class="form-control" id="curName" value="${c?.name || ""}" placeholder="US Dollar">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_order">Order</label>
                    <input type="number" class="form-control" id="curOrder" value="${c?.order ?? 0}">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCurrency(${currencyId})" data-i18n="save_button">Save</button>
        </div>`);
  applyTranslations();
}

async function saveCurrency(currencyId) {
  const body = {
    code: document.getElementById("curCode").value.toUpperCase(),
    symbol: document.getElementById("curSymbol").value,
    flag: document.getElementById("curFlag").value,
    name: document.getElementById("curName").value,
    order: parseInt(document.getElementById("curOrder").value) || 0,
  };
  if (!body.code || !body.name) {
    showToast("Code and Name are required", "error");
    return;
  }
  const res = await fetch(currencyId ? `/api/currencies/${currencyId}/` : "/api/currencies/", {
    method: currencyId ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Currency saved ✓");
    renderCurrencySettings();
  } else showToast("Error", "error");
}

async function deleteCurrency(currencyId) {
  if (!confirm("Delete this currency?")) return;
  const res = await fetch(`/api/currencies/${currencyId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Deleted");
    renderCurrencySettings();
  } else showToast("Error deleting currency", "error");
}

async function setMultiCurrencyEnabled(enabled) {
  const res = await fetch("/api/settings/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings: { multi_currency_enabled: enabled ? "true" : "false" } }),
  });
  if (res.ok) {
    showToast(
      enabled
        ? t("multi_currency_enabled_saved", "Users can now choose their own default currency ✓")
        : t(
            "multi_currency_disabled_saved",
            "Currency choice is now locked to the platform default ✓"
          )
    );
  } else {
    showToast(t("error_saving_settings", "Error saving setting"), "error");
    document.getElementById("multiCurrencyToggle").checked = !enabled;
  }
}

async function setDefaultCurrency(code) {
  const warning = t(
    "currency_default_confirm",
    "Changing your default currency recalculates all your totals in the new currency. Continue?"
  );
  if (!confirm(warning)) return;
  const res = await fetch("/api/base-currency/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  const body = await res.json().catch(() => ({}));
  if (res.ok) {
    showToast(t("currency_default_saved", "Default currency updated ✓"));
    window.location.reload();
  } else {
    showToast(t(body.error_key || "currency_default_invalid", body.error || "Error"), "error");
  }
}

// ════════════════════════════════════════════════════════════════════════════
// COMPANY SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════
