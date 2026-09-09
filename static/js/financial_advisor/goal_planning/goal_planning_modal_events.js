"use strict";
// Goal Planning tab — event wiring for the Add button, card action buttons
// (view/edit/delete), and the modal Save button. Split out of
// goal_planning.js (200-line backlog). Bare global; converted from closures
// inside _renderGoalPlanning to a standalone function taking explicit params.
// ════════════════════════════════════════════════════════════════════════════

function wireGoalModalEvents(cardsContainer, goals, els) {
  const { currencySelect, linkedAssetSelect, modal } = els;

  const addBtn = document.getElementById("btnAddGoal");
  if (addBtn) {
    addBtn.addEventListener("click", () => openGoalModal(null, els));
  }

  if (cardsContainer) {
    cardsContainer.addEventListener("click", async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const actionEl = target.closest("[data-goal-action]");
      if (!(actionEl instanceof HTMLElement)) return;
      const action = actionEl.getAttribute("data-goal-action");
      const goalId = Number(actionEl.getAttribute("data-goal-id") || 0);
      if (!goalId) return;

      if (action === "edit") {
        try {
          const response = await fetch(`/api/goals/`);
          const data = await response.json();
          const rawGoal = (data.goals || []).find((item) => Number(item.id) === goalId);
          if (rawGoal) openGoalModal(rawGoal, els);
        } catch (_error) {
          showToast(t("goal_planning_error"), "error");
        }
        return;
      }

      if (action === "view") {
        showToast(
          `${t("goal_planning_target_amount")}: ${fmt(Number(goals.find((goal) => Number(goal.id) === goalId)?.target_amount_egp || 0))}`
        );
        return;
      }

      if (action === "delete") {
        const okay = window.confirm(t("goal_planning_delete_confirm"));
        if (!okay) return;
        try {
          const response = await fetch(`/api/goals/${goalId}/`, { method: "DELETE" });
          if (!response.ok) throw new Error("goal_delete_failed");
          await loadGoalPlanning(true);
          showToast(t("goal_planning_deleted"));
        } catch (_error) {
          showToast(t("goal_planning_save_error"), "error");
        }
      }
    });
  }

  const saveBtn = document.getElementById("btnSaveGoal");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const idInput = document.getElementById("goalIdInput");
      const nameInput = document.getElementById("goalNameInput");
      const typeInput = document.getElementById("goalTypeInput");
      const targetInput = document.getElementById("goalTargetAmountInput");
      const savedInput = document.getElementById("goalSavedAmountInput");
      const dateInput = document.getElementById("goalTargetDateInput");
      const priorityInput = document.getElementById("goalPriorityInput");
      const notesInput = document.getElementById("goalNotesInput");

      if (
        !idInput ||
        !nameInput ||
        !typeInput ||
        !targetInput ||
        !savedInput ||
        !dateInput ||
        !priorityInput ||
        !notesInput ||
        !currencySelect ||
        !linkedAssetSelect
      ) {
        return;
      }

      const payloadBody = {
        name: nameInput.value.trim(),
        goal_type: typeInput.value.trim(),
        target_amount: Number(targetInput.value || 0),
        current_saved_amount: Number(savedInput.value || 0),
        target_date: dateInput.value || null,
        currency_id: currencySelect.value ? Number(currencySelect.value) : null,
        linked_asset_id: linkedAssetSelect.value ? Number(linkedAssetSelect.value) : null,
        priority: priorityInput.value || "Medium",
        notes: notesInput.value || "",
      };

      if (!payloadBody.name || !payloadBody.goal_type) {
        showToast(t("goal_planning_validation_required"), "error");
        return;
      }

      const goalId = Number(idInput.value || 0);
      const url = goalId ? `/api/goals/${goalId}/` : "/api/goals/";
      const method = goalId ? "PUT" : "POST";

      try {
        const response = await fetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payloadBody),
        });
        if (!response.ok) throw new Error("goal_save_failed");
        if (modal) modal.hide();
        await loadGoalPlanning(true);
        showToast(t("goal_planning_saved"));
      } catch (_error) {
        showToast(t("goal_planning_save_error"), "error");
      }
    });
  }
}
