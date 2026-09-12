async function createServerBackup() {
  showLoader();
  try {
    const res = await fetch("/api/settings/backup/create/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();

    if (data.success) {
      showAlert(t("backup_success", "Backup created successfully!"), "success");
      await renderBackupRestoreSettings(); // Refresh list
    } else {
      showAlert(data.error || "Backup creation failed", "danger");
    }
  } catch (e) {
    showAlert("Network error: " + e.message, "danger");
  } finally {
    hideLoader();
  }
}

// Trigger Server-side restore
async function restoreServerBackup(filename) {
  const overwrite = document.getElementById("restoreOverwriteOpt")?.checked || false;

  const confirmMsg = t(
    "restore_confirm",
    "Are you sure you want to restore this backup? This will modify database records."
  );
  if (!confirm(confirmMsg)) return;

  showLoader();
  try {
    const res = await fetch(`/api/settings/backup/restore/?overwrite=${overwrite}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    const data = await res.json();

    if (data.success) {
      showAlert(t("restore_success", "Restore completed successfully!"), "success");
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } else {
      showAlert(data.error || "Restore failed", "danger");
    }
  } catch (e) {
    showAlert("Network error: " + e.message, "danger");
  } finally {
    hideLoader();
  }
}

// Trigger Server-side delete
async function deleteServerBackup(filename) {
  const confirmMsg = t("delete_confirm", "Are you sure you want to delete this backup file?");
  if (!confirm(confirmMsg)) return;

  showLoader();
  try {
    const res = await fetch("/api/settings/backup/delete/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    const data = await res.json();

    if (data.success) {
      showAlert("Backup deleted successfully", "success");
      await renderBackupRestoreSettings(); // Refresh list
    } else {
      showAlert(data.error || "Deletion failed", "danger");
    }
  } catch (e) {
    showAlert("Network error: " + e.message, "danger");
  } finally {
    hideLoader();
  }
}

// Utility Loader helpers (checks if global showLoader/hideLoader exists, or falls back to console/minimal UI)
