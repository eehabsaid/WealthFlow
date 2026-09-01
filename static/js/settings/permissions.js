"use strict";
// User permissions modal and role mapping manager
// This file is part of the settings module. Do not edit directly.

async function showPermissionsModal(userId) {
  const res = await fetch(`/api/users/${userId}/permissions/`);
  if (!res.ok) {
    showToast("Unable to load permissions", "error");
    return;
  }
  const d = await res.json();

  const rows = (d.permissions || [])
    .map(
      (p) => `
        <tr>
            <td>${p.username}</td>
            <td>${p.page}</td>
            <td><button class="btn-icon del" onclick="deletePermission(${p.id})"><i class="bi bi-trash"></i></button></td>
        </tr>`
    )
    .join("");

  const optHtml = (d.available_pages || [])
    .map((p) => `<option value="${p[0]}">${p[1]}</option>`)
    .join("");

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="manage_permissions">Manage Permissions</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <strong data-i18n="existing_permissions">Existing Permissions</strong>
            <div style="max-height:240px;overflow:auto;margin:10px 0">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="user_username">User</th>
                        <th data-i18n="page">Page</th>
                        <th data-i18n="actions">Actions</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
            <hr>
            <div class="row g-3">
                <div class="col-8"><select id="permPage" class="form-select">${optHtml}</select></div>
                <div class="col-4">
                    <button class="btn-primary-custom" onclick="addPermission(${userId})" data-i18n="btn_add">Add</button>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="close_button">Close</button>
        </div>`);
  applyTranslations();
}

async function addPermission(userId) {
  const page = document.getElementById("permPage").value;
  const res = await fetch(`/api/users/${userId}/permissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page }),
  });
  if (res.ok) {
    showToast("Permission added");
    showPermissionsModal(userId);
  } else showToast("Error adding permission", "error");
}

async function deletePermission(permId) {
  if (!confirm("Remove this permission?")) return;
  const res = await fetch(`/api/users/permissions/${permId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Removed");
    closeModal();
  } else showToast("Error removing permission", "error");
}

// ════════════════════════════════════════════════════════════════════════════
// TRANSLATION SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════
