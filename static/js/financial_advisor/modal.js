"use strict";

function _renderGoalPlanningModalSection() {
  return `
      <div class="modal fade goal-editor-modal" id="goalEditorModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
          <div class="modal-content goal-editor-surface" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
            <div class="modal-header goal-editor-header" style="border-bottom:1px solid var(--border-color);">
              <h5 class="modal-title" id="goalEditorTitle" data-i18n="goal_planning_create_title"></h5>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              <form id="goalEditorForm" class="row g-3 goal-editor-form">
                <input type="hidden" id="goalIdInput">
                <div class="col-12 col-md-6 goal-field goal-field-half">
                  <label class="form-label" data-i18n="goal_planning_field_name"></label>
                  <input type="text" class="form-control" id="goalNameInput" required>
                </div>
                <div class="col-12 col-md-6 goal-field goal-field-half">
                  <label class="form-label" data-i18n="goal_planning_field_type"></label>
                  <input type="text" class="form-control" id="goalTypeInput" required>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_target_amount"></label>
                  <input type="number" min="0" step="0.01" class="form-control" id="goalTargetAmountInput" required>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_saved_amount"></label>
                  <input type="number" min="0" step="0.01" class="form-control" id="goalSavedAmountInput" required>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_target_date"></label>
                  <input type="date" class="form-control" id="goalTargetDateInput">
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_currency"></label>
                  <select class="form-select" id="goalCurrencyInput"></select>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_priority"></label>
                  <select class="form-select" id="goalPriorityInput">
                    <option value="High">${_escapeHtml(t("goal_planning_priority_high"))}</option>
                    <option value="Medium">${_escapeHtml(t("goal_planning_priority_medium"))}</option>
                    <option value="Low">${_escapeHtml(t("goal_planning_priority_low"))}</option>
                  </select>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_linked_asset"></label>
                  <select class="form-select" id="goalLinkedAssetInput"></select>
                </div>
                <div class="col-12 goal-field goal-field-full">
                  <label class="form-label" data-i18n="goal_planning_field_notes"></label>
                  <textarea class="form-control" rows="3" id="goalNotesInput"></textarea>
                </div>
              </form>
            </div>
            <div class="modal-footer goal-editor-footer" style="border-top:1px solid var(--border-color);">
              <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal" data-i18n="btn_cancel"></button>
              <button type="button" class="btn btn-primary" id="btnSaveGoal" data-i18n="btn_save"></button>
            </div>
          </div>
        </div>
      </div>
  `;
}
