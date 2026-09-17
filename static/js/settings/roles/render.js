"use strict";
// Roles settings tab — sysadmin-only. Roles bundle grantable permission
// keys (main-app pages + settings tabs) and are assigned to users from
// the Users tab's "Manage Access" modal (see settings/permissions.js).
// This file is part of the settings module. Do not edit directly.

let _rolesAvailableKeys = [];

async function renderRoleSettings() {
  const mc = document.getElementById("settingsContent");
  const res = await fetch("/api/roles/");
  if (!res.ok) {
    mc.innerHTML = `<div class="p-4" data-i18n="no_permission">You do not have permission to manage roles.</div>`;
    applyTranslations();
    return;
  }
  const d = await res.json();
  _rolesAvailableKeys = d.available_keys || [];

  const rows = (d.roles || [])
    .map(
      (r) => `
        <tr>
            <td>${r.name}</td>
            <td>${r.description || "—"}</td>
            <td>${(r.keys || []).length}</td>
            <td>
                <button class="btn-icon" onclick="showRoleModal(${r.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteRole(${r.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`
    )
    .join("");

  mc.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div></div>
            <button class="btn-primary-custom" onclick="showRoleModal(null)" data-i18n="btn_add_role">
                <i class="bi bi-plus-lg"></i> Add Role
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="role_name">Name</th>
                    <th data-i18n="role_description">Description</th>
                    <th data-i18n="role_key_count">Granted Keys</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
  applyTranslations();
}

function _roleKeyCheckboxes(selectedKeys) {
  const selected = new Set(selectedKeys || []);
  const mainKeys = _rolesAvailableKeys.filter((k) => !k[0].startsWith("settings_"));
  const settingsKeys = _rolesAvailableKeys.filter((k) => k[0].startsWith("settings_"));

  const group = (title, keys) => `
        <div style="margin-bottom:8px"><strong>${title}</strong></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:14px">
            ${keys
              .map(
                (k) => `
                <label style="font-weight:400">
                    <input type="checkbox" class="role-key-cb" value="${k[0]}" ${selected.has(k[0]) ? "checked" : ""}>
                    ${k[1]}
                </label>`
              )
              .join("")}
        </div>`;

  return group("Main App Pages", mainKeys) + group("Settings Tabs", settingsKeys);
}

async function showRoleModal(roleId) {
  let role = null;
  if (roleId) {
    const res = await fetch("/api/roles/");
    const d = await res.json();
    role = (d.roles || []).find((r) => r.id === roleId);
    _rolesAvailableKeys = d.available_keys || _rolesAvailableKeys;
  }
  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${roleId ? "edit_role" : "add_role"}">${roleId ? "Edit Role" : "Add Role"}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label data-i18n="role_name">Name</label>
                    <input class="form-control" id="roleName" value="${role?.name || ""}">
                </div>
                <div class="col-12">
                    <label data-i18n="role_description">Description</label>
                    <input class="form-control" id="roleDescription" value="${role?.description || ""}">
                </div>
                <div class="col-12">
                    ${_roleKeyCheckboxes(role?.keys)}
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveRole(${roleId})" data-i18n="save_button">Save</button>
        </div>`);
  applyTranslations();
}

async function saveRole(roleId) {
  const name = document.getElementById("roleName").value.trim();
  const description = document.getElementById("roleDescription").value.trim();
  const keys = Array.from(document.querySelectorAll(".role-key-cb:checked")).map((cb) => cb.value);
  if (!name) {
    showToast("Role name is required", "error");
    return;
  }
  const res = await fetch(roleId ? `/api/roles/${roleId}/` : "/api/roles/", {
    method: roleId ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, keys }),
  });
  if (res.ok) {
    closeModal();
    showToast("Role saved ✓");
    renderRoleSettings();
  } else {
    const d = await res.json().catch(() => ({}));
    showToast(d.error || "Error saving role", "error");
  }
}

async function deleteRole(roleId) {
  if (!confirm("Delete this role? Users assigned to it will lose whatever it granted them.")) return;
  const res = await fetch(`/api/roles/${roleId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Role deleted");
    renderRoleSettings();
  } else showToast("Error deleting role", "error");
}
