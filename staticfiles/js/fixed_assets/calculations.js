"use strict";
// Gold read-only state, gold field refresh, net sale amount, payment methods
// This file is part of the fixed_assets module. Do not edit directly.function updateNetSaleAmount() {
  const salePrice =
    parseFloat(document.getElementById("fa_sale_price")?.value) || 0;
  const sellingExpenses =
    parseFloat(document.getElementById("fa_selling_expenses")?.value) || 0;
  const netSaleField = document.getElementById("fa_net_sale_amount");

  if (!netSaleField) return;

  netSaleField.value = (salePrice - sellingExpenses).toFixed(2);
}

