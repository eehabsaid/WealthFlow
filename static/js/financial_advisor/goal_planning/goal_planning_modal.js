"use strict";
// Goal Planning tab — editor modal setup (currency/asset select population)
// and open/populate logic. Split out of goal_planning.js (200-line
// backlog). Bare globals; converted from closures inside _renderGoalPlanning
// to standalone functions taking explicit params.
// ════════════════════════════════════════════════════════════════════════════

function setupGoalModal() {
  const meta = _goalPlanningMeta || { currencies: [], assets: [] };
  const modalEl = document.getElementById("goalEditorModal");
  const modal =
    modalEl && window.bootstrap
      ? new bootstrap.Modal(modalEl, { backdrop: "static", keyboard: false, focus: true })
      : null;

  const currencySelect = document.getElementById("goalCurrencyInput");
  const linkedAssetSelect = document.getElementById("goalLinkedAssetInput");
  if (currencySelect) {
    currencySelect.innerHTML = (meta.currencies || [])
      .map(
        (item) => `
      <option value="${item.id}">${_escapeHtml(item.code || "EGP")}${item.symbol ? ` (${_escapeHtml(item.symbol)})` : ""}</option>
    `
      )
      .join("");
  }
  if (linkedAssetSelect) {
    linkedAssetSelect.innerHTML = `
      <option value="">${_escapeHtml(t("goal_planning_none"))}</option>
      ${(meta.assets || []).map((item) => `<option value="${item.id}">${_escapeHtml(item.name || "-")}</option>`).join("")}
    `;
  }

  return { modal, currencySelect, linkedAssetSelect };
}

function openGoalModal(goalItem, els) {
  const { currencySelect, linkedAssetSelect, modal } = els;
  const title = document.getElementById("goalEditorTitle");
  const idInput = document.getElementById("goalIdInput");
  const nameInput = document.getElementById("goalNameInput");
  const typeInput = document.getElementById("goalTypeInput");
  const targetInput = document.getElementById("goalTargetAmountInput");
  const savedInput = document.getElementById("goalSavedAmountInput");
  const dateInput = document.getElementById("goalTargetDateInput");
  const priorityInput = document.getElementById("goalPriorityInput");
  const notesInput = document.getElementById("goalNotesInput");

  if (
    !title ||
    !idInput ||
    !nameInput ||
    !typeInput ||
    !targetInput ||
    !savedInput ||
    !dateInput ||
    !priorityInput ||
    !notesInput ||
    !currencySelect ||
    !linkedAssetSelect ||
    !modal
  ) {
    return;
  }

  if (goalItem) {
    title.setAttribute("data-i18n", "goal_planning_edit_title");
    idInput.value = String(goalItem.id || "");
    nameInput.value = goalItem.name || "";
    typeInput.value = goalItem.goal_type || "";
    targetInput.value = Number(goalItem.target_amount || 0);
    savedInput.value = Number(goalItem.current_saved_amount || 0);
    dateInput.value = goalItem.target_date || "";
    priorityInput.value = goalItem.priority || "Medium";
    notesInput.value = goalItem.notes || "";
    currencySelect.value = goalItem.currency_id
      ? String(goalItem.currency_id)
      : currencySelect.options[0]?.value || "";
    linkedAssetSelect.value = goalItem.linked_asset_id ? String(goalItem.linked_asset_id) : "";
  } else {
    title.setAttribute("data-i18n", "goal_planning_create_title");
    idInput.value = "";
    nameInput.value = "";
    typeInput.value = "";
    targetInput.value = "0";
    savedInput.value = "0";
    dateInput.value = "";
    priorityInput.value = "Medium";
    notesInput.value = "";
    currencySelect.value = currencySelect.options[0]?.value || "";
    linkedAssetSelect.value = "";
  }

  applyTranslations();
  modal.show();
}
