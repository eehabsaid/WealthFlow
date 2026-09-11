"use strict";

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
