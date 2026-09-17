"use strict";
// User permissions modal — role assignment + per-user overrides (grant/revoke)
// This file is part of the settings module. Do not edit directly.

async function showPermissionsModal(userId) {
  const [permRes, userRolesRes, rolesRes] = await Promise.all([
    fetch(`/api/users/${userId}/permissions/`),
    fetch(`/api/users/${userId}/roles/`),
    fetch(`/api/roles/`),
  ]);
  if (!permRes.ok || !userRolesRes.ok) {
    showToast("Unable to load permissions", "error");
    return;
  }
  const d = await permRes.json();
  const userRoles = (await userRolesRes.json()).roles || [];
  const allRoles = rolesRes.ok ? (await rolesRes.json()).roles || [] : [];
  const assignedRoleIds = new Set(userRoles.map((ur) => ur.role_id));

  const roleRows = userRoles
    .map(
      (ur) => `
        <tr>
            <td>${ur.role_name}</td>
            <td><button class="btn-icon del" onclick="removeUserRole(${userId}, ${ur.id})"><i class="bi bi-trash"></i></button></td>
        </tr>`
    )
    .join("");

  const assignableRoleOpts = allRoles
    .filter((r) => !assignedRoleIds.has(r.id))
    .map((r) => `<option value="${r.id}">${r.name}</option>`)
    .join("");

  const overrideRows = (d.permissions || [])
    .map(
      (p) => `
        <tr>
            <td>${p.page}</td>
            <td>${p.granted ? '<span data-i18n="granted">Grant</span>' : '<span data-i18n="revoked">Revoke</span>'}</td>
            <td><button class="btn-icon del" onclick="deletePermission(${p.id})"><i class="bi bi-trash"></i></button></td>
        </tr>`
    )
    .join("");

  const pageOptHtml = (d.available_pages || [])
    .map((p) => `<option value="${p[0]}">${p[1]}</option>`)
    .join("");

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="manage_permissions">Manage Access</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <strong data-i18n="user_roles">Roles</strong>
            <div style="max-height:160px;overflow:auto;margin:10px 0">
                <table class="data-table"><tbody>${roleRows}</tbody></table>
            </div>
            <div class="row g-3">
                <div class="col-8"><select id="assignRoleSelect" class="form-select">${assignableRoleOpts}</select></div>
                <div class="col-4">
                    <button class="btn-primary-custom" onclick="assignUserRole(${userId})" data-i18n="btn_add">Add</button>
                </div>
            </div>
            <hr>
            <strong data-i18n="existing_permissions">Per-user Overrides</strong>
            <div style="max-height:200px;overflow:auto;margin:10px 0">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="page">Key</th>
                        <th data-i18n="granted">Grant/Revoke</th>
                        <th data-i18n="actions">Actions</th>
                    </tr></thead>
                    <tbody>${overrideRows}</tbody>
                </table>
            </div>
            <div class="row g-3">
                <div class="col-6"><select id="permPage" class="form-select">${pageOptHtml}</select></div>
                <div class="col-3">
                    <select id="permGranted" class="form-select">
                        <option value="true" data-i18n="grant">Grant</option>
                        <option value="false" data-i18n="revoke">Revoke</option>
                    </select>
                </div>
                <div class="col-3">
                    <button class="btn-primary-custom" onclick="addPermission(${userId})" data-i18n="btn_add">Add</button>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="close_button">Close</button>
        </div>`);
  applyTranslations();
}

async function assignUserRole(userId) {
  const roleId = document.getElementById("assignRoleSelect").value;
  if (!roleId) return;
  const res = await fetch(`/api/users/${userId}/roles/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_id: parseInt(roleId) }),
  });
  if (res.ok) {
    showToast("Role assigned");
    showPermissionsModal(userId);
  } else showToast("Error assigning role", "error");
}

async function removeUserRole(userId, userRoleId) {
  if (!confirm("Remove this role from the user?")) return;
  const res = await fetch(`/api/users/roles/${userRoleId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Removed");
    showPermissionsModal(userId);
  } else showToast("Error removing role", "error");
}

async function addPermission(userId) {
  const page = document.getElementById("permPage").value;
  const granted = document.getElementById("permGranted").value === "true";
  const res = await fetch(`/api/users/${userId}/permissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page, granted }),
  });
  if (res.ok) {
    showToast("Override saved");
    showPermissionsModal(userId);
  } else showToast("Error adding override", "error");
}

async function deletePermission(permId) {
  if (!confirm("Remove this override?")) return;
  const res = await fetch(`/api/users/permissions/${permId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Removed");
    closeModal();
  } else showToast("Error removing override", "error");
}

// ════════════════════════════════════════════════════════════════════════════
// TRANSLATION SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════
