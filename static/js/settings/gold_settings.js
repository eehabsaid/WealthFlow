"use strict";
// Gold settings (types and purities) management
// This file is part of the settings module. Do not edit directly.

async function renderGoldSettings() {
  const [typesRes, puritiesRes] = await Promise.all([
    fetch("/api/settings/gold-types/"),
    fetch("/api/settings/gold-purities/"),
  ]);

  const typeData = await typesRes.json();
  const purityData = await puritiesRes.json();

  const types = typeData.items || [];
  const purities = purityData.items || [];

  const typeRows = types
    .map(
      (item) => `
        <tr>
            <td>${item.name}</td>
            <td>${item.order ?? 0}</td>
            <td><span style="color:${item.is_active ? "var(--accent-green)" : "var(--accent-red)"}" data-i18n="${item.is_active ? "active" : "inactive"}">${item.is_active ? t("active", "Active") : t("inactive", "Inactive")}</span></td>
            <td>
                <button class="btn-icon" onclick="showGoldTypeModal(${item.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="disableGoldType(${item.id})"><i class="bi bi-slash-circle"></i></button>
            </td>
        </tr>
    `
    )
    .join("");

  const purityRows = purities
    .map(
      (item) => `
        <tr>
            <td>${item.key}</td>
            <td>${item.label}</td>
            <td class="num-fmt" data-value="${item.cashback_per_gram || 0}">${fmt(item.cashback_per_gram || 0)}</td>
            <td>${item.order ?? 0}</td>
            <td><span style="color:${item.is_active ? "var(--accent-green)" : "var(--accent-red)"}" data-i18n="${item.is_active ? "active" : "inactive"}">${item.is_active ? t("active", "Active") : t("inactive", "Inactive")}</span></td>
            <td>
                <button class="btn-icon" onclick="showGoldPurityModal(${item.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="disableGoldPurity(${item.id})"><i class="bi bi-slash-circle"></i></button>
            </td>
        </tr>
    `
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `


        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="gold_types">${t("gold_types", "Gold Types")}</div>
                <button class="btn-primary-custom" onclick="showGoldTypeModal(null)" data-i18n="add_gold_type">${t("add_gold_type", "Add Gold Type")}</button>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="gold_type">${t("gold_type", "Gold Type")}</th>
                            <th data-i18n="order">${t("order", "Order")}</th>
                            <th data-i18n="active">${t("active", "Active")}</th>
                            <th data-i18n="actions">${t("actions", "Actions")}</th>
                        </tr>
                    </thead>
                    <tbody>${typeRows}</tbody>
                </table>
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="gold_purities">${t("gold_purities", "Gold Purities")}</div>
                <button class="btn-primary-custom" onclick="showGoldPurityModal(null)" data-i18n="add_gold_purity">${t("add_gold_purity", "Add Gold Purity")}</button>
            </div>
            <div style="margin-bottom:8px;color:var(--text-muted);font-size:12px;" data-i18n="gold_purities_cashback_hint">${t("gold_purities_cashback_hint", "Cashback per gram here is used in all gold valuation calculations across the app.")}</div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="gold_purity_key">${t("gold_purity_key", "Purity Key")}</th>
                            <th data-i18n="gold_purity_label">${t("gold_purity_label", "Purity Label")}</th>
                            <th data-i18n="cashback_per_gram">${t("cashback_per_gram", "Cashback per Gram")}</th>
                            <th data-i18n="order">${t("order", "Order")}</th>
                            <th data-i18n="active">${t("active", "Active")}</th>
                            <th data-i18n="actions">${t("actions", "Actions")}</th>
                        </tr>
                    </thead>
                    <tbody>${purityRows}</tbody>
                </table>
            </div>
        </div>
    `;

  applyTranslations();
}

async function showGoldTypeModal(itemId) {
  let item = null;
  if (itemId) {
    const res = await fetch("/api/settings/gold-types/");
    const data = await res.json();
    item = (data.items || []).find((x) => x.id === itemId) || null;
  }

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${item ? "edit_gold_type" : "add_gold_type"}">${item ? t("edit_gold_type", "Edit Gold Type") : t("add_gold_type", "Add Gold Type")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-7"><label data-i18n="gold_type">${t("gold_type", "Gold Type")}</label><input type="text" class="form-control" id="gstName" value="${item?.name || ""}"></div>
                <div class="col-3"><label data-i18n="order">${t("order", "Order")}</label><input type="number" class="form-control" id="gstOrder" value="${item?.order ?? 0}"></div>
                <div class="col-2"><label data-i18n="active">${t("active", "Active")}</label><select class="form-select" id="gstActive"><option value="true" ${item == null || item.is_active ? "selected" : ""}>${t("yes", "Yes")}</option><option value="false" ${item && !item.is_active ? "selected" : ""}>${t("no", "No")}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="saveGoldType(${itemId || "null"})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>
    `);
  applyTranslations();
}

async function saveGoldType(itemId) {
  const body = {
    name: document.getElementById("gstName").value.trim(),
    order: parseInt(document.getElementById("gstOrder").value) || 0,
    is_active: document.getElementById("gstActive").value === "true",
  };

  if (!body.name) {
    showToast(t("gold_type_required", "Gold type name is required"), "error");
    return;
  }

  const url = itemId ? `/api/settings/gold-types/${itemId}/` : "/api/settings/gold-types/";
  const method = itemId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    closeModal();
    showToast(t("gold_type_saved", "Gold type saved ✓"), "success");
    renderGoldSettings();
  } else {
    showToast(t("error_saving_gold_type", "Error saving gold type"), "error");
  }
}

async function disableGoldType(itemId) {
  if (!confirm(t("confirm_disable_gold_type", "Disable this gold type?"))) return;
  const res = await fetch(`/api/settings/gold-types/${itemId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("gold_type_disabled", "Gold type disabled"), "success");
    renderGoldSettings();
  } else {
    showToast(t("error_disabling_gold_type", "Error disabling gold type"), "error");
  }
}

async function showGoldPurityModal(itemId) {
  let item = null;
  if (itemId) {
    const res = await fetch("/api/settings/gold-purities/");
    const data = await res.json();
    item = (data.items || []).find((x) => x.id === itemId) || null;
  }

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${item ? "edit_gold_purity" : "add_gold_purity"}">${item ? t("edit_gold_purity", "Edit Gold Purity") : t("add_gold_purity", "Add Gold Purity")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-3"><label data-i18n="gold_purity_key">${t("gold_purity_key", "Purity Key")}</label><input type="text" class="form-control" id="gspKey" value="${item?.key || ""}" placeholder="24k"></div>
                <div class="col-3"><label data-i18n="gold_purity_label">${t("gold_purity_label", "Purity Label")}</label><input type="text" class="form-control" id="gspLabel" value="${item?.label || ""}" placeholder="24K"></div>
                <div class="col-3"><label data-i18n="cashback_per_gram">${t("cashback_per_gram", "Cashback per Gram")}</label><input type="number" step="0.0001" class="form-control" id="gspCashback" value="${item?.cashback_per_gram ?? 0}"></div>
                <div class="col-2"><label data-i18n="order">${t("order", "Order")}</label><input type="number" class="form-control" id="gspOrder" value="${item?.order ?? 0}"></div>
                <div class="col-1"><label data-i18n="active">${t("active", "Active")}</label><select class="form-select" id="gspActive"><option value="true" ${item == null || item.is_active ? "selected" : ""}>${t("yes", "Yes")}</option><option value="false" ${item && !item.is_active ? "selected" : ""}>${t("no", "No")}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="saveGoldPurity(${itemId || "null"})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>
    `);
  applyTranslations();
}

async function saveGoldPurity(itemId) {
  const body = {
    key: document.getElementById("gspKey").value.trim().toLowerCase(),
    label: document.getElementById("gspLabel").value.trim(),
    cashback_per_gram: parseFloat(document.getElementById("gspCashback").value) || 0,
    order: parseInt(document.getElementById("gspOrder").value) || 0,
    is_active: document.getElementById("gspActive").value === "true",
  };

  if (!body.key) {
    showToast(t("gold_purity_key_required", "Purity key is required"), "error");
    return;
  }

  if (!body.label) {
    body.label = body.key.toUpperCase();
  }

  const url = itemId ? `/api/settings/gold-purities/${itemId}/` : "/api/settings/gold-purities/";
  const method = itemId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    closeModal();
    showToast(t("gold_purity_saved", "Gold purity saved ✓"), "success");
    renderGoldSettings();
  } else {
    showToast(t("error_saving_gold_purity", "Error saving gold purity"), "error");
  }
}

async function disableGoldPurity(itemId) {
  if (!confirm(t("confirm_disable_gold_purity", "Disable this gold purity?"))) return;
  const res = await fetch(`/api/settings/gold-purities/${itemId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("gold_purity_disabled", "Gold purity disabled"), "success");
    renderGoldSettings();
  } else {
    showToast(t("error_disabling_gold_purity", "Error disabling gold purity"), "error");
  }
}

// ════════════════════════════════════════════════════════════════════════════
// LANGUAGE SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════
