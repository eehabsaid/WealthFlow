"use strict";
// Sale form payload collection + validation + sync-record submission.
// Part of the fixed_assets module (split from the former monolithic
// validation.js, 200-line rule). Do not edit directly.

function collectSalePayload() {
  return {
    sale_date: document.getElementById("fa_sale_date").value,
    sale_price: parseFloat(document.getElementById("fa_sale_price").value) || 0,
    selling_expenses: parseFloat(document.getElementById("fa_selling_expenses").value) || 0,
    net_sale_amount: parseFloat(document.getElementById("fa_net_sale_amount").value) || 0,
    deposit_currency_id: parseInt(document.getElementById("fa_deposit_currency").value, 10) || null,
    deposit_method: document.getElementById("fa_deposit_method").value || "Cash",
    deposit_bank_id: parseInt(document.getElementById("fa_deposit_bank").value, 10) || null,
    notes: document.getElementById("fa_sale_notes").value,
  };
}

function validateSaleForm() {
  const saleDate = document.getElementById("fa_sale_date").value;
  const salePrice = parseFloat(document.getElementById("fa_sale_price").value) || 0;

  if (!saleDate) {
    throw new Error(t("sale_date_required", "Sale date is required"));
  }

  if (salePrice <= 0) {
    throw new Error(t("sale_price_required", "Sale price must be greater than zero"));
  }

  const depositCurrencyId =
    parseInt(document.getElementById("fa_deposit_currency")?.value, 10) || null;
  const depositMethod = document.getElementById("fa_deposit_method")?.value || "Cash";
  const depositBankId = parseInt(document.getElementById("fa_deposit_bank")?.value, 10) || null;

  if (!depositCurrencyId) {
    throw new Error(t("currency_required", "Currency is required."));
  }
  if (shouldRequireBankForMethod(depositMethod) && !depositBankId) {
    throw new Error(t("bank_account_required", "Bank account is required for this payment method"));
  }
}

async function syncAssetSale(assetId, status) {
  if (status === "Sold") {
    validateSaleForm();

    const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(collectSalePayload()),
    });

    if (!response.ok) {
      let message = t("error_saving_sale", "Error saving sale information");
      try {
        const payload = await response.json();
        if (payload?.error_key) {
          message = t(payload.error_key, payload.error || message);
        } else if (payload?.error) {
          message = payload.error;
        }
      } catch (_) {
        // Keep fallback message.
      }
      throw new Error(message);
    }

    return;
  }

  const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
  });

  if (!response.ok && response.status !== 404) {
    let message = t("error_removing_sale", "Error removing sale information");
    try {
      const payload = await response.json();
      if (payload?.error_key) {
        message = t(payload.error_key, payload.error || message);
      } else if (payload?.error) {
        message = payload.error;
      }
    } catch (_) {
      // Keep fallback message.
    }
    throw new Error(message);
  }
}

