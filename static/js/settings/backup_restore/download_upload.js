function triggerDownloadBackup() {
  // Standard direct browser download by navigating or opening the endpoint
  // This prompts the native Save File Dialog Window.
  const url = "/api/settings/backup/create/?download=true";
  window.location.href = url;
}

// Trigger Client-side restore (upload)
async function triggerUploadRestore(input) {
  if (!input.files || input.files.length === 0) return;

  const file = input.files[0];
  const overwrite = document.getElementById("restoreOverwriteOpt")?.checked || false;

  const confirmMsg = t(
    "restore_confirm",
    "Are you sure you want to restore this backup? This will modify database records."
  );
  if (!confirm(confirmMsg)) {
    input.value = ""; // Reset file input
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  showLoader();
  try {
    const res = await fetch(`/api/settings/backup/restore/?overwrite=${overwrite}`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.success) {
      showAlert(t("restore_success", "Restore completed successfully!"), "success");
      // Re-render settings page to reflect potential schema changes / updates
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
    input.value = ""; // Reset file input
  }
}

// Trigger Server-side backup creation
