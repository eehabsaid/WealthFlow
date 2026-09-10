/**
 * WealthFlow Document Manager - List & Shell Rendering
 * Builds the attached-file rows (filename, category, size, upload date) and
 * the surrounding widget shell (upload form + list container). See doc_state.js
 * for the namespace/package overview.
 */

"use strict";

window.DocumentManager = window.DocumentManager || {};

DocumentManager._buildListRows = function (items) {
  if (!items.length) {
    return `<div style="text-align:center;color:var(--text-secondary);padding: 20px 0;" data-i18n="documents_none">${t("documents_none", "No documents yet")}</div>`;
  }

  return items
    .map((doc) => {
      const id = Number(doc.id || 0);
      const category = DocumentManager._safeText(doc.document_category || "-");
      const name = DocumentManager._safeText(doc.original_file_name || "-");
      const notes = DocumentManager._safeText(doc.notes || "");
      const uploaded = DocumentManager._safeText(formatDate(doc.upload_date) || "-");
      const size = DocumentManager._fmtFileSize(doc.file_size);

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
};

DocumentManager._renderShell = function (items) {
  const state = DocumentManager._state;
  const container = document.getElementById(state.containerId);
  if (!container) return;

  const categoryOptions = (state.categories || [])
    .map(
      (category) =>
        `<option value="${DocumentManager._safeText(category)}">${DocumentManager._safeText(category)}</option>`
    )
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
          <input type="file" id="docUploadFile" class="form-control" accept="${DocumentManager._DEFAULT_ALLOWED}">
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
        ${DocumentManager._buildListRows(items)}
      </div>
    </div>
  `;

  container.querySelectorAll("#documentsListContainer .item-card").forEach((card) => {
    initCollapsibleCard(card, "#documentsListContainer");
  });

  applyTranslations();
};
