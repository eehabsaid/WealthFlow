"use strict";
// User management settings and modal editor
// This file is part of the settings module. Do not edit directly.

async function renderUserSettings() {
  const mc = document.getElementById("settingsContent");
  const meRes = await fetch("/api/auth/me/");
  const me = await meRes.json();
  const canManage = me.user?.is_staff || (me.allowed_pages || []).includes("user_management");

  if (!canManage) {
    mc.innerHTML = `<div class="p-4" data-i18n="no_permission">You do not have permission to manage users.</div>`;
    applyTranslations();
    return;
  }
  await loadUsers({ page: 1, pageSize: 10, q: "" });
}

async function loadUsers({ page = 1, pageSize = 10, q = "" } = {}) {
  const container = document.getElementById("settingsContent");
  if (!container) {
    return;
  }

  const requestId = ++usersLoadRequestId;

  container.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div style="display:flex;gap:8px;align-items:center">
                <button class="btn-secondary-custom" onclick="toggleSelectAll()" data-i18n="btn_toggle_select">Toggle Select</button>
                <select id="bulkActionSelect" class="form-select" style="width:220px">
                    <option value=""             data-i18n="bulk_actions">Bulk actions</option>
                    <option value="activate"     data-i18n="activate_selected">Activate selected</option>
                    <option value="deactivate"   data-i18n="deactivate_selected">Deactivate selected</option>
                    <option value="delete"       data-i18n="delete_selected">Delete selected</option>
                    <option value="set_staff_true"  data-i18n="set_staff">Set staff</option>
                    <option value="set_staff_false" data-i18n="unset_staff">Unset staff</option>
                </select>
                <button class="btn-primary-custom" onclick="applyBulkAction()" data-i18n="btn_apply">Apply</button>
            </div>
            <div style="display:flex;gap:8px">
                <input id="userSearch" class="form-control"
                    data-i18n-placeholder="search_placeholder" value="${q}"
                    style="width:260px" placeholder="Search...">
                <button class="btn-primary-custom" onclick="handleUserSearch()" data-i18n="btn_search">Search</button>
                <button class="btn-primary-custom" onclick="showUserModal(null)" data-i18n="btn_add_user">
                    <i class="bi bi-plus-lg"></i>
                </button>
            </div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th></th>
                    <th data-i18n="user_username">Username</th>
                    <th data-i18n="user_email">Email</th>
                    <th data-i18n="auth_email_verified_label">Email Verified</th>
                    <th data-i18n="auth_account_status_label">Account Status</th>
                    <th data-i18n="user_is_active">Active</th>
                    <th data-i18n="user_roles">Roles</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody id="usersTableBody"></tbody>
            </table>
            </div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px">
            <div id="usersPager"></div>
            <select id="usersPageSize" class="form-select" style="width:80px">
                <option>5</option><option selected>10</option><option>25</option><option>50</option>
            </select>
        </div>`;

  const pageSizeEl = document.getElementById("usersPageSize");
  if (pageSizeEl) {
    pageSizeEl.value = pageSize;
  }

  const resp = await fetch(
    `/api/users/?page=${page}&page_size=${pageSize}&q=${encodeURIComponent(q)}`
  );
  const data = await resp.json();

  if (requestId !== usersLoadRequestId) {
    return;
  }

  const usersTableBody = document.getElementById("usersTableBody");
  if (!usersTableBody) {
    return;
  }

  const statusKeyForUser = (user) => {
    const status = String(user.account_status || "active");
    if (status === "pending_email_verification") return "auth_status_verify_email";
    if (status === "pending_admin_approval") return "auth_status_pending_admin_approval";
    if (status === "rejected") return "auth_status_rejected";
    if (status === "disabled") return "auth_status_disabled";
    return "auth_status_active_label";
  };

  usersTableBody.innerHTML = (data.users || [])
    .map(
      (u) => `
        <tr>
            <td><input type="checkbox" class="user-select" data-id="${u.id}"></td>
            <td>${u.username}</td>
            <td>${u.email || "—"}</td>
            <td data-i18n="${u.email_verified ? "yes" : "no"}">${u.email_verified ? t("yes", "Yes") : t("no", "No")}</td>
            <td data-i18n="${statusKeyForUser(u)}">${t(statusKeyForUser(u), u.account_status || "active")}</td>
            <td data-i18n="${u.is_active ? "active" : "inactive"}">${u.is_active ? t("active", "Active") : t("inactive", "Inactive")}</td>
            <td>
                ${u.is_staff ? '<span data-i18n="user_is_staff">Staff</span> ' : ""}
                ${u.is_superuser ? '<span data-i18n="user_is_superuser">Superuser</span>' : ""}
            </td>
            <td>
                <button class="btn-icon" onclick="showUserModal(${u.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon" onclick="showPermissionsModal(${u.id})"><i class="bi bi-shield-lock"></i></button>
                <button class="btn-icon del" onclick="deleteUser(${u.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`
    )
    .join("");

  applyTranslations();
}

async function showUserModal(userId) {
  let u = null;
  if (userId) {
    const res = await fetch(`/api/users/${userId}/`);
    u = (await res.json()).user;
  }
  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${userId ? "edit_user" : "add_user"}">${userId ? "Edit User" : "Add User"}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label data-i18n="user_username">Username</label>
                    <input class="form-control" id="uName" value="${u?.username || ""}" ${u ? "disabled" : ""}>
                </div>
                <div class="col-12">
                    <label data-i18n="user_email">Email</label>
                    <input class="form-control" id="uEmail" value="${u?.email || ""}">
                </div>
                <div class="col-12">
                    <label data-i18n="user_password">Password</label>
                    <input type="password" class="form-control" id="uPassword">
                </div>
                <div class="col-6">
                    <label data-i18n="user_is_active">Active</label>
                    <select class="form-select" id="uActive">
                        <option value="true"  ${!u || u.is_active ? "selected" : ""} data-i18n="yes">Yes</option>
                        <option value="false" ${u && !u.is_active ? "selected" : ""} data-i18n="no">No</option>
                    </select>
                </div>
                <div class="col-6">
                    <label data-i18n="user_is_staff">Staff</label>
                    <select class="form-select" id="uStaff">
                        <option value="false" ${!u?.is_staff ? "selected" : ""} data-i18n="no">No</option>
                        <option value="true"  ${u?.is_staff ? "selected" : ""} data-i18n="yes">Yes</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveUser(${userId})" data-i18n="save_button">Save</button>
        </div>`);
  applyTranslations();
}

function handleUserSearch() {
  const pageSizeEl = document.getElementById("usersPageSize");
  const qEl = document.getElementById("userSearch");
  if (!pageSizeEl || !qEl) {
    return;
  }
  loadUsers({
    page: 1,
    pageSize: pageSizeEl.value,
    q: qEl.value,
  });
}

function toggleSelectAll() {
  const boxes = Array.from(document.querySelectorAll(".user-select"));
  const some = boxes.some((b) => !b.checked);
  boxes.forEach((b) => (b.checked = some));
}

function getSelectedUserIds() {
  return Array.from(document.querySelectorAll(".user-select:checked")).map((cb) =>
    parseInt(cb.dataset.id)
  );
}

async function applyBulkAction() {
  const action = document.getElementById("bulkActionSelect").value;
  const ids = getSelectedUserIds();
  if (!action) {
    showToast("Choose an action", "error");
    return;
  }
  if (!ids.length) {
    showToast("No users selected", "error");
    return;
  }
  if (action === "delete" && !confirm(`Delete ${ids.length} selected users?`)) return;

  const payload = { action, ids };
  if (action.startsWith("set_staff")) payload.value = action.endsWith("true");

  try {
    const res = await fetch("/api/users/bulk/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const d = await res.json();
    if (res.ok) {
      showToast(`${d.changed || 0} users updated`);
      const pageSizeEl = document.getElementById("usersPageSize");
      const qEl = document.getElementById("userSearch");
      loadUsers({
        page: 1,
        pageSize: pageSizeEl ? pageSizeEl.value : 10,
        q: qEl ? qEl.value : "",
      });
    } else showToast(d.error || "Bulk action failed", "error");
  } catch (e) {
    showToast("Network error", "error");
  }
}

async function saveUser(userId) {
  const username = document.getElementById("uName")?.value.trim() || "";
  const email = document.getElementById("uEmail").value.trim();
  const password = document.getElementById("uPassword").value;

  if (!userId && !username) {
    showToast("Username required", "error");
    return;
  }
  if (!email) {
    showToast("Email required", "error");
    return;
  }

  const body = {
    username,
    email,
    is_active: document.getElementById("uActive").value === "true",
    is_staff: document.getElementById("uStaff").value === "true",
  };
  if (password) body.password = password;

  const res = await fetch(userId ? `/api/users/${userId}/` : "/api/users/", {
    method: userId ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("User saved ✓");
    renderUserSettings();
  } else {
    const e = await res.json().catch(() => ({}));
    showToast(e.error || "Error saving user", "error");
  }
}

async function deleteUser(id) {
  if (!confirm("Delete user? This cannot be undone.")) return;
  const res = await fetch(`/api/users/${id}/`, { method: "DELETE" });
  if (res.ok) {
    showToast("Deleted");
    renderUserSettings();
  } else showToast("Error deleting user", "error");
}
