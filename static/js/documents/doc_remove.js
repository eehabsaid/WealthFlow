/**
 * WealthFlow Document Manager - Delete
 * DocumentManager.remove(): deletes a document attachment via
 * DELETE /api/documents/file/<id>/.
 * See doc_state.js for the namespace/package overview.
 */

"use strict";

window.DocumentManager = window.DocumentManager || {};

DocumentManager.remove = async function (documentId) {
  const state = DocumentManager._state;
  if (!confirm(t("confirm_delete_document", "Delete this document?"))) return;

  try {
    await DocumentManager._fetchJson(`/api/documents/file/${Number(documentId)}/`, {
      method: "DELETE",
    });
    showToast(t("document_deleted", "Document deleted"), "success");
    await DocumentManager._reload();
    if (state.onChanged) state.onChanged();
  } catch (error) {
    showToast(`${t("error_deleting", "Error deleting")}: ${error.message}`, "error");
  }
};
