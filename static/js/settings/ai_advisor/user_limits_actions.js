"use strict";
// Event handling for the monthly token limits panel: default save, per-row save, search/filter,
// Toggle Select All and bulk apply. Server is the source of truth; every save reloads the list.

window.AIA = window.AIA || {};

async function aiLimitsPost(payload) {
  const res = await fetch("/api/settings/ai/user-limits/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showToast(t(data.error_key || "settings_save_failed", data.error || "Save failed"), "error");
    return null;
  }
  showToast(t("settings_saved", "Settings saved ✓"));
  return data;
}

window.AIA.bindUserLimitsEvents = function () {
  const L = window.AIA.limits;
  const $ = (id) => document.getElementById(id);

  $("aiDefaultLimitSave").onclick = async () => {
    if (await aiLimitsPost({ default_limit: $("aiDefaultLimitInput").value }))
      window.AIA.loadUserLimitsPanel();
  };

  $("aiLimitsSearch").addEventListener("input", (e) => {
    L.q = e.target.value;
    window.AIA.renderUserLimitsTable();
  });
  $("aiLimitsModeFilter").addEventListener("change", (e) => {
    L.mode = e.target.value;
    window.AIA.renderUserLimitsTable();
  });

  // Toggle Select All: every eligible (general-settings) user matching the current search/filter,
  // including rows hidden behind "Show all N rows". Checkboxes are updated in place so the table stays expanded.
  $("aiLimitsToggleAll").onclick = () => {
    const boxes = [...document.querySelectorAll("#aiLimitsBody .ai-limit-select:not(:disabled)")];
    const ids = boxes.map((b) => Number(b.closest("tr").dataset.userId));
    const allOn = ids.length > 0 && ids.every((id) => L.selected.has(id));
    ids.forEach((id) => (allOn ? L.selected.delete(id) : L.selected.add(id)));
    boxes.forEach((b) => (b.checked = !allOn));
    window.AIA.updateLimitsSelection();
  };

  $("aiLimitsBulkApply").onclick = async () => {
    const data = await aiLimitsPost({
      user_ids: [...L.selected],
      limit: $("aiLimitsBulkValue").value,
    });
    if (!data) return;
    L.selected.clear();
    $("aiLimitsBulkValue").value = "";
    showToast(
      t("ai_limits_applied", "Limit applied to {count} users").replace("{count}", data.updated)
    );
    window.AIA.loadUserLimitsPanel();
  };

  $("aiLimitsTableHost").addEventListener("change", (e) => {
    if (!e.target.classList.contains("ai-limit-select")) return;
    const id = Number(e.target.closest("tr").dataset.userId);
    if (e.target.checked) L.selected.add(id);
    else L.selected.delete(id);
    window.AIA.updateLimitsSelection();
  });

  $("aiLimitsTableHost").addEventListener("click", async (e) => {
    const btn = e.target.closest(".ai-limit-save");
    if (!btn || btn.disabled) return;
    const row = btn.closest("tr");
    const ok = await aiLimitsPost({
      user_id: Number(row.dataset.userId),
      limit: row.querySelector(".ai-limit-input").value,
    });
    if (ok) window.AIA.loadUserLimitsPanel();
  });
};
