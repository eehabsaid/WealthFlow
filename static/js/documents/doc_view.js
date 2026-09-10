/**
 * WealthFlow Document Manager - View & Download
 * DocumentManager.openInline()/download(): open a file via
 * /api/documents/file/<id>/?disposition=inline|attachment.
 * See doc_state.js for the namespace/package overview.
 */

"use strict";

window.DocumentManager = window.DocumentManager || {};

DocumentManager.openInline = function (documentId) {
  window.open(
    `/api/documents/file/${Number(documentId)}/?disposition=inline`,
    "_blank",
    "noopener"
  );
};

DocumentManager.download = function (documentId) {
  window.open(
    `/api/documents/file/${Number(documentId)}/?disposition=attachment`,
    "_blank",
    "noopener"
  );
};
