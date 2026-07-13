"use strict";

(function () {
  const DEFAULT_ALLOWED = ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png";

  function _safeText(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function _fmtFileSize(size) {
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
  }

  async function _fetchJson(url, options) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = payload.error || payload.detail || `HTTP ${response.status}`;
      throw new Error(String(message));
    }
    return payload;
  }

  function _buildListRows(items) {
    if (!items.length) {
      return `<div style="text-align:center;color:var(--text-secondary);padding: 20px 0;" data-i18n="documents_none">${t("documents_none", "No documents yet")}</div>`;
    }

    return items
      .map((doc) => {
        const id = Number(doc.id || 0);
        const category = _safeText(doc.document_category || "-");
        const name = _safeText(doc.original_file_name || "-");
        const notes = _safeText(doc.notes || "");
        const uploaded = _safeText(String(doc.upload_date || "").slice(0, 10));
        const size = _fmtFileSize(doc.file_size);

        return `
          <div class="item-card card" id="doc-card-${id}">
            <div class="item-header card-header">
              <div class="item-header-left">
                <svg class="item-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
                <span class="item-category-badge">${category}</span>
                <span class="item-name-preview" title="${name}">${name}</span>
              </div>
              <div class="item-header-right">
                <span class="item-amount-preview text-secondary" style="font-size:12px; font-weight:normal;">${size}</span>
                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" style="font-size: 11px;" title="${t("view", "View")}" onclick="event.stopPropagation(); DocumentManager.openInline(${id})">
                  <i class="bi bi-eye"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" style="font-size: 11px;" title="${t("download", "Download")}" onclick="event.stopPropagation(); DocumentManager.download(${id})">
                  <i class="bi bi-download"></i>
                </button>
                <button type="button" class="item-remove-btn" title="${t("delete", "Delete")}" onclick="event.stopPropagation(); DocumentManager.remove(${id})">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"/></svg>
                </button>
              </div>
            </div>
            <div class="item-body card-body">
              <div class="field-grid">
                <div class="field span-2">
                  <label class="form-label" data-i18n="document_name">${t("document_name", "File")}</label>
                  <input type="text" class="form-control" value="${name}" readonly>
                </div>
                <div class="field">
                  <label class="form-label" data-i18n="upload_date">${t("upload_date", "Uploaded")}</label>
                  <input type="text" class="form-control" value="${uploaded}" readonly>
                </div>
                <div class="field">
                  <label class="form-label" data-i18n="file_size">${t("file_size", "Size")}</label>
                  <input type="text" class="form-control" value="${size}" readonly>
                </div>
                <div class="field span-2">
                  <label class="form-label" data-i18n="document_category">${t("document_category", "Category")}</label>
                  <input type="text" class="form-control" value="${category}" readonly>
                </div>
                <div class="field span-2 d-flex align-items-end">
                  <button type="button" class="btn btn-outline-primary btn-sm w-100" style="height:38px;" onclick="DocumentManager.pickReplace(${id})">
                    <i class="bi bi-arrow-repeat me-1"></i> <span data-i18n="replace">${t("replace", "Replace")}</span>
                  </button>
                </div>
                <div class="field span-4">
                  <label class="form-label" data-i18n="notes">${t("notes", "Notes")}</label>
                  <textarea class="form-control" rows="2" readonly>${notes || "-"}</textarea>
                </div>
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  const state = {
    parentType: "",
    parentId: null,
    categories: [],
    onChanged: null,
    containerId: "",
  };

  function _renderDisabled(message) {
    const container = document.getElementById(state.containerId);
    if (!container) return;

    container.innerHTML = `
      <div style="border:1px dashed var(--border-color);border-radius:10px;padding:14px;color:var(--text-secondary);">
        ${_safeText(message || t("documents_save_first", "Save this record first to manage documents."))}
      </div>
    `;
  }

  function _renderShell(items) {
    const container = document.getElementById(state.containerId);
    if (!container) return;

    const categoryOptions = (state.categories || [])
      .map((category) => `<option value="${_safeText(category)}">${_safeText(category)}</option>`)
      .join("");

    container.innerHTML = `
      <div style="border:1px solid var(--border-color);border-radius:10px;padding:12px;background:var(--bg-secondary);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:8px;flex-wrap:wrap;">
          <h6 style="margin:0;color:var(--text-primary);" data-i18n="documents_title">${t("documents_title", "Documents")}</h6>
          <small style="color:var(--text-secondary);" data-i18n="documents_allowed_hint">${t("documents_allowed_hint", "Allowed: PDF, DOC, DOCX, XLS, XLSX, JPG, PNG")}</small>
        </div>

        <div class="field-grid mb-3">
          <div class="field span-2">
            <label class="form-label small" data-i18n="file">${t("file", "File")}</label>
            <input type="file" id="docUploadFile" class="form-control" accept="${DEFAULT_ALLOWED}">
          </div>
          <div class="field">
            <label class="form-label small" data-i18n="document_category">${t("document_category", "Category")}</label>
            <select id="docUploadCategory" class="form-select">
              ${categoryOptions}
            </select>
          </div>
          <div class="field">
            <label class="form-label small" data-i18n="notes">${t("notes", "Notes")}</label>
            <input type="text" id="docUploadNotes" class="form-control" placeholder="${t("notes", "Notes")}">
          </div>
          <div class="field span-4 d-grid">
            <button class="btn btn-outline-primary btn-sm" onclick="DocumentManager.upload()" data-i18n="upload">${t("upload", "Upload")}</button>
          </div>
        </div>

        <div id="documentsListContainer" class="w-100">
          ${_buildListRows(items)}
        </div>
      </div>
    `;

    container.querySelectorAll("#documentsListContainer .item-card").forEach((card) => {
      initCollapsibleCard(card, "#documentsListContainer");
    });

    applyTranslations();
  }

  async function _reload() {
    if (!state.parentType || !state.parentId) {
      _renderDisabled();
      return;
    }

    const [categoriesData, docsData] = await Promise.all([
      _fetchJson(`/api/documents/categories/?parent_type=${encodeURIComponent(state.parentType)}`),
      _fetchJson(`/api/documents/${encodeURIComponent(state.parentType)}/${state.parentId}/`),
    ]);

    state.categories = categoriesData.categories || [];
    _renderShell(docsData.documents || []);
  }

  async function init(options) {
    state.parentType = String(options?.parentType || "").trim().toLowerCase();
    state.parentId = Number(options?.parentId || 0) || null;
    state.containerId = String(options?.containerId || "").trim();
    state.onChanged = typeof options?.onChanged === "function" ? options.onChanged : null;

    if (!state.containerId) return;

    if (!state.parentId) {
      _renderDisabled(options?.disabledMessage || t("documents_save_first", "Save this record first to manage documents."));
      return;
    }

    try {
      await _reload();
    } catch (error) {
      _renderDisabled(error.message || t("documents_error_loading", "Failed to load documents"));
    }
  }

  async function upload() {
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
      await _fetchJson(`/api/documents/${encodeURIComponent(state.parentType)}/${state.parentId}/`, {
        method: "POST",
        body: formData,
      });
      showToast(t("document_uploaded", "Document uploaded"), "success");
      if (fileInput) fileInput.value = "";
      if (notesInput) notesInput.value = "";
      await _reload();
      if (state.onChanged) state.onChanged();
    } catch (error) {
      showToast(`${t("upload_failed", "Upload failed")}: ${error.message}`, "error");
    }
  }

  function openInline(documentId) {
    window.open(`/api/documents/file/${Number(documentId)}/?disposition=inline`, "_blank", "noopener");
  }

  function download(documentId) {
    window.open(`/api/documents/file/${Number(documentId)}/?disposition=attachment`, "_blank", "noopener");
  }

  function pickReplace(documentId) {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = DEFAULT_ALLOWED;
    fileInput.addEventListener("change", async () => {
      const file = fileInput.files?.[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        await _fetchJson(`/api/documents/file/${Number(documentId)}/`, {
          method: "POST",
          body: formData,
        });
        showToast(t("document_replaced", "Document replaced"), "success");
        await _reload();
        if (state.onChanged) state.onChanged();
      } catch (error) {
        showToast(`${t("error_saving", "Error saving")}: ${error.message}`, "error");
      }
    });
    fileInput.click();
  }

  async function remove(documentId) {
    if (!confirm(t("confirm_delete_document", "Delete this document?"))) return;

    try {
      await _fetchJson(`/api/documents/file/${Number(documentId)}/`, {
        method: "DELETE",
      });
      showToast(t("document_deleted", "Document deleted"), "success");
      await _reload();
      if (state.onChanged) state.onChanged();
    } catch (error) {
      showToast(`${t("error_deleting", "Error deleting")}: ${error.message}`, "error");
    }
  }

  window.DocumentManager = {
    init,
    upload,
    openInline,
    download,
    pickReplace,
    remove,
  };
})();
