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
  if (
    action === "delete" &&
    !confirm(
      t(
        "users_bulk_delete_confirm",
        "Schedule {count} selected users for deletion? They can be restored during the grace period."
      ).replace("{count}", String(ids.length))
    )
  )
    return;

  const payload = { action, ids };
  if (action.startsWith("set_staff")) payload.value = action.endsWith("true");
  if (action.startsWith("set_sysadmin")) {
    payload.action = "set_sysadmin";
    payload.value = action.endsWith("true");
  }

  try {
    const res = await fetch("/api/users/bulk/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const d = await res.json();
    if (res.ok) {
      showToast(`${d.changed || 0} users updated`);
      if (d.blocked_last_admin?.length) {
        showToast(
          t("users_bulk_blocked_last_admin", "Not deleted (last administrator): {names}").replace(
            "{names}",
            d.blocked_last_admin.join(", ")
          ),
          "error"
        );
      }
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

  const accessLevel = document.getElementById("uAccessLevel").value;
  const body = {
    username,
    email,
    is_active: document.getElementById("uActive").value === "true",
    is_staff: accessLevel === "staff" || accessLevel === "sysadmin",
    is_sysadmin: accessLevel === "sysadmin",
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
  if (
    !confirm(
      t(
        "user_delete_confirm",
        "Delete this user? The account is disabled now and can be restored until the grace period ends; after that it is permanently removed."
      )
    )
  )
    return;
  const res = await fetch(`/api/users/${id}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("user_delete_scheduled", "Account scheduled for deletion"));
    renderUserSettings();
  } else {
    const e = await res.json().catch(() => ({}));
    showToast(e.message || t("user_delete_error", "Error deleting user"), "error");
  }
}

async function restoreUser(id) {
  const res = await fetch(`/api/users/${id}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "restore" }),
  });
  showToast(
    res.ok
      ? t("user_restored", "Account restored")
      : t("user_restore_error", "Couldn't restore the account"),
    res.ok ? "success" : "error"
  );
  if (res.ok) renderUserSettings();
}

async function purgeUserNow(id) {
  if (
    !confirm(
      t(
        "user_purge_now_confirm",
        "Permanently delete this account and all its data now? This cannot be undone."
      )
    )
  )
    return;
  const res = await fetch(`/api/users/${id}/?purge_now=1`, { method: "DELETE" });
  showToast(
    res.ok
      ? t("user_purged", "Account permanently deleted")
      : t("user_delete_error", "Error deleting user"),
    res.ok ? "success" : "error"
  );
  if (res.ok) renderUserSettings();
}
