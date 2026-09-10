/**
 * WealthFlow Document Manager - Upload
 * DocumentManager.upload(): posts a new file to /api/documents/<parentType>/<parentId>/.
 * See doc_state.js for the namespace/package overview.
 */

"use strict";

window.DocumentManager = window.DocumentManager || {};

DocumentManager.upload = async function () {
  const state = DocumentManager._state;
  if (!state.parentType || !state.parentId) return;

  const fileInput = document.getElementById("docUploadFile");
  const categoryInput = document.getElementById("docUploadCategory");
  const notesInput = document.getElementById("docUploadNotes");
  const file = fileInput?.files?.[0];

  if (!file) {
    showToast(t("file_required", "Please choose a file"), "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_category", categoryInput?.value || "Related Files");
  formData.append("notes", notesInput?.value || "");

  try {
    await DocumentManager._fetchJson(
      `/api/documents/${encodeURIComponent(state.parentType)}/${state.parentId}/`,
      {
        method: "POST",
        body: formData,
      }
    );
    showToast(t("document_uploaded", "Document uploaded"), "success");
    if (fileInput) fileInput.value = "";
    if (notesInput) notesInput.value = "";
    await DocumentManager._reload();
    if (state.onChanged) state.onChanged();
  } catch (error) {
    showToast(`${t("upload_failed", "Upload failed")}: ${error.message}`, "error");
  }
};
