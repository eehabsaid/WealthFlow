/**
 * WealthFlow Document Manager - Shared State & Core Helpers
 *
 * Sibling files in this package (load order matters, see templates/index.html):
 *   doc_state.js   - window.DocumentManager namespace, shared state, escape/format
 *                     helpers, fetch wrapper, init() and the private reload/disabled
 *                     render orchestration used by every other sibling.
 *   doc_list.js    - Builds the attached-file list markup and the widget shell
 *                     (upload form + list container) with metadata per document.
 *   doc_upload.js  - DocumentManager.upload(): posts a new file to /api/documents/.
 *   doc_view.js    - DocumentManager.openInline()/download(): view or download a
 *                     file via /api/documents/file/<id>/?disposition=...
 *   doc_replace.js - DocumentManager.pickReplace(): swaps an existing file's binary.
 *   doc_remove.js  - DocumentManager.remove(): deletes a document attachment.
 *
 * Convention: window.DocumentManager is the single shared namespace. Public API
 * methods (init, upload, openInline, download, pickReplace, remove) are attached
 * directly to it by their respective sibling file. Internal helpers shared across
 * siblings are attached with an underscore prefix (e.g. DocumentManager._reload)
 * so they remain callable across files without polluting the global scope.
 */

"use strict";

window.DocumentManager = window.DocumentManager || {};

DocumentManager._DEFAULT_ALLOWED = ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png";

DocumentManager._state = {
  parentType: "",
  parentId: null,
  categories: [],
  onChanged: null,
  containerId: "",
};

DocumentManager._safeText = function (value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

DocumentManager._fmtFileSize = function (size) {
  const n = Number(size || 0);
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = n;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[idx]}`;
};

DocumentManager._fetchJson = async function (url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.error || payload.detail || `HTTP ${response.status}`;
    throw new Error(String(message));
  }
  return payload;
};

DocumentManager._renderDisabled = function (message) {
  const state = DocumentManager._state;
  const container = document.getElementById(state.containerId);
  if (!container) return;

  container.innerHTML = `
    <div style="border:1px dashed var(--border-color);border-radius:10px;padding:14px;color:var(--text-secondary);">
      ${DocumentManager._safeText(
        message || t("documents_save_first", "Save this record first to manage documents.")
      )}
    </div>
  `;
};

DocumentManager._reload = async function () {
  const state = DocumentManager._state;
  if (!state.parentType || !state.parentId) {
    DocumentManager._renderDisabled();
    return;
  }

  const [categoriesData, docsData] = await Promise.all([
    DocumentManager._fetchJson(
      `/api/documents/categories/?parent_type=${encodeURIComponent(state.parentType)}`
    ),
    DocumentManager._fetchJson(
      `/api/documents/${encodeURIComponent(state.parentType)}/${state.parentId}/`
    ),
  ]);

  state.categories = categoriesData.categories || [];
  DocumentManager._renderShell(docsData.documents || []);
};

DocumentManager.init = async function (options) {
  const state = DocumentManager._state;
  state.parentType = String(options?.parentType || "")
    .trim()
    .toLowerCase();
  state.parentId = Number(options?.parentId || 0) || null;
  state.containerId = String(options?.containerId || "").trim();
  state.onChanged = typeof options?.onChanged === "function" ? options.onChanged : null;

  if (!state.containerId) return;

  if (!state.parentId) {
    DocumentManager._renderDisabled(
      options?.disabledMessage ||
        t("documents_save_first", "Save this record first to manage documents.")
    );
    return;
  }

  try {
    await DocumentManager._reload();
  } catch (error) {
    DocumentManager._renderDisabled(
      error.message || t("documents_error_loading", "Failed to load documents")
    );
  }
};
