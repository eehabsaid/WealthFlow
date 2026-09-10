/**
 * WealthFlow Document Manager - Replace
 * DocumentManager.pickReplace(): prompts for a new file and swaps it in for an
 * existing document via POST /api/documents/file/<id>/.
 * See doc_state.js for the namespace/package overview.
 */

"use strict";

window.DocumentManager = window.DocumentManager || {};

DocumentManager.pickReplace = function (documentId) {
  const state = DocumentManager._state;
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = DocumentManager._DEFAULT_ALLOWED;
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      await DocumentManager._fetchJson(`/api/documents/file/${Number(documentId)}/`, {
        method: "POST",
        body: formData,
      });
      showToast(t("document_replaced", "Document replaced"), "success");
      await DocumentManager._reload();
      if (state.onChanged) state.onChanged();
    } catch (error) {
      showToast(`${t("error_saving", "Error saving")}: ${error.message}`, "error");
    }
  });
  fileInput.click();
};
