"use strict";
// Legal Text settings tab (sysadmin-only): the section editor for one
// language + document. Edits for every language/document are kept in
// _legalState.edits until a new version is published (see legal/render.js).
// This file is part of the settings module. Do not edit directly.

const _LEGAL_LANGS = ["en", "ar", "fr", "de"];
const _LEGAL_LANG_NAMES = { en: "English", ar: "العربية", fr: "Français", de: "Deutsch" };
const _LEGAL_DOCS = ["terms", "privacy"];
let _legalState = null;

function _legalEsc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function _legalClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function _legalCurrentDoc() {
  const s = _legalState;
  return s.edits[s.lang][s.doc];
}

function _legalSectionHtml(section, index) {
  const dir = _legalState.lang === "ar" ? "rtl" : "ltr";
  return `
    <div class="legal-edit-section" data-index="${index}">
      <div class="legal-edit-row">
        <input type="text" class="form-control legal-edit-title" dir="${dir}" maxlength="200"
               value="${_legalEsc(section.title)}" oninput="legalEditSection(${index}, 'title', this.value)"
               data-i18n-placeholder="legal_editor_section_title" placeholder="Section title" />
        <button type="button" class="btn-icon del" onclick="legalRemoveSection(${index})"
                data-i18n-title="legal_editor_remove_section" title="Remove section">
          <i class="bi bi-trash"></i>
        </button>
      </div>
      <textarea class="form-control legal-edit-body" dir="${dir}" rows="4" maxlength="8000"
                oninput="legalEditSection(${index}, 'body', this.value)"
                data-i18n-placeholder="legal_editor_section_body"
                placeholder="Section text">${_legalEsc(section.body)}</textarea>
    </div>`;
}

function renderLegalEditorBody() {
  const s = _legalState;
  const doc = _legalCurrentDoc();
  const dir = s.lang === "ar" ? "rtl" : "ltr";
  document.getElementById("legalEditorBody").innerHTML = `
    <label class="form-label" for="legalDocTitle" data-i18n="legal_editor_doc_title">Page title</label>
    <input id="legalDocTitle" type="text" class="form-control mb-3" dir="${dir}" maxlength="200"
           value="${_legalEsc(doc.title)}" oninput="legalEditTitle(this.value)" />
    ${doc.sections.map(_legalSectionHtml).join("")}
    <div class="legal-edit-actions">
      <button type="button" class="btn-secondary-custom" onclick="legalAddSection()">
        <i class="bi bi-plus-lg"></i> <span data-i18n="legal_editor_add_section">Add section</span>
      </button>
      <button type="button" class="btn-secondary-custom" onclick="legalResetDoc()">
        <i class="bi bi-arrow-counterclockwise"></i>
        <span data-i18n="legal_editor_reset_default">Reset to built-in text</span>
      </button>
    </div>`;
  applyTranslations();
}

function legalSelect(kind, value) {
  _legalState[kind] = value;
  renderLegalEditorBody();
}

function legalEditTitle(value) {
  _legalCurrentDoc().title = value;
}

function legalEditSection(index, field, value) {
  _legalCurrentDoc().sections[index][field] = value;
}

function legalAddSection() {
  _legalCurrentDoc().sections.push({ title: "", body: "" });
  renderLegalEditorBody();
}

function legalRemoveSection(index) {
  _legalCurrentDoc().sections.splice(index, 1);
  renderLegalEditorBody();
}

function legalResetDoc() {
  const s = _legalState;
  s.edits[s.lang][s.doc] = _legalClone(s.payload.defaults[s.lang][s.doc]);
  renderLegalEditorBody();
}
