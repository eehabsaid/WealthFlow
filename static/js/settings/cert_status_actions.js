"use strict";
// cert_status_settings.js — Certificate Status: delete/refresh/helpers

async function deleteCertStatus(id) {
  const confirmMsg = t("confirm_delete_status", "Delete this status?");
  if (!confirm(confirmMsg)) return;
  const res = await fetch(`/api/cert-statuses/${id}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("status_deleted", "Status deleted"), "success");
    renderCertStatusSettings();
  }
}

// ════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════

async function _refreshCertStatusOptions() {
  // If a cert form is open, refresh its status dropdown
  const select = document.getElementById("certStatus");
  if (!select) return;
  const res = await fetch("/api/cert-statuses/");
  const data = await res.json();
  const current = select.value;
  select.innerHTML = (data.statuses || [])
    .map(
      (s) => `<option value="${s.name}" ${s.name === current ? "selected" : ""}>${s.name}</option>`
    )
    .join("");
}

function esc(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
