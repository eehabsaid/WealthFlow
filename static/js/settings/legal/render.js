"use strict";
// Legal Text settings tab (sysadmin-only): page shell, version history and
// publishing. Editing helpers live in legal/editor.js.
// This file is part of the settings module. Do not edit directly.

async function renderLegalSettings() {
  const mc = document.getElementById("settingsContent");
  const res = await fetch("/api/settings/legal/");
  if (!res.ok) {
    mc.innerHTML = `<div class="p-4" data-i18n="legal_editor_no_permission">Only a system administrator can edit the legal text.</div>`;
    applyTranslations();
    return;
  }
  const payload = await res.json();
  _legalState = {
    payload,
    lang: "en",
    doc: "terms",
    edits: _legalClone(payload.current),
  };
  mc.innerHTML = `
    <div class="legal-editor">
      <p class="legal-editor-intro" data-i18n="legal_editor_intro">
        Edit the Privacy Policy and Terms of Service shown at /privacy/ and /terms/. Each save publishes a new
        version; empty languages keep the built-in text. Existing accounts keep the version they accepted.
      </p>
      <div id="retentionCard"></div>
      <div class="legal-edit-row">
        <select id="legalLangSelect" class="form-select" onchange="legalSelect('lang', this.value)"
                data-i18n-title="legal_editor_language" title="Language">
          ${_LEGAL_LANGS.map((l) => `<option value="${l}">${_LEGAL_LANG_NAMES[l]}</option>`).join("")}
        </select>
        <select id="legalDocSelect" class="form-select" onchange="legalSelect('doc', this.value)">
          <option value="terms" data-i18n="legal_terms_title">Terms of Service</option>
          <option value="privacy" data-i18n="legal_privacy_title">Privacy Policy</option>
        </select>
        <span class="legal-current-badge">
          <span data-i18n="legal_editor_current_version">Current version</span>:
          <bdi>${_legalEsc(payload.current_label)}</bdi>
        </span>
      </div>
      <div id="legalEditorBody"></div>
      <div class="legal-publish-box">
        <label class="form-label" for="legalNewLabel" data-i18n="legal_editor_new_version">New version label</label>
        <input id="legalNewLabel" type="text" class="form-control" maxlength="40" placeholder="2026-11-v1" />
        <label class="legal-reconsent">
          <input id="legalReconsent" type="checkbox" />
          <span data-i18n="legal_editor_require_reconsent">Require every user to accept this version again</span>
        </label>
        <button id="legalPublishBtn" type="button" class="btn-primary-custom" onclick="publishLegalVersion()">
          <i class="bi bi-cloud-upload"></i> <span data-i18n="legal_editor_publish">Publish new version</span>
        </button>
      </div>
      <h3 class="legal-history-title" data-i18n="legal_editor_history">Version history</h3>
      <div id="legalHistory"></div>
    </div>`;
  renderLegalEditorBody();
  renderLegalHistory();
  renderRetentionCard();
}

function renderLegalHistory() {
  const versions = _legalState.payload.versions || [];
  const box = document.getElementById("legalHistory");
  if (!versions.length) {
    box.innerHTML = `<div class="text-muted" data-i18n="legal_editor_history_empty">No edited versions yet; the built-in text is in use.</div>`;
    applyTranslations();
    return;
  }
  const rows = versions
    .map(
      (v, i) => `
      <tr>
        <td><bdi>${_legalEsc(v.label)}</bdi>${i === 0 ? ` <span class="badge bg-success" data-i18n="legal_editor_current">Current</span>` : ""}</td>
        <td><bdi>${_legalEsc((v.created_at || "").slice(0, 16).replace("T", " "))}</bdi></td>
        <td>${_legalEsc(v.created_by || "—")}</td>
        <td>${v.require_reconsent ? "✓" : "—"}</td>
        <td><button type="button" class="btn-secondary-custom" onclick="loadLegalVersion(${v.id})"
                    data-i18n="legal_editor_load">Load into editor</button></td>
      </tr>`
    )
    .join("");
  box.innerHTML = `
    <div class="table-container"><table class="data-table">
      <thead><tr>
        <th data-i18n="legal_version_label">Version</th>
        <th data-i18n="legal_editor_published">Published</th>
        <th data-i18n="legal_editor_by">By</th>
        <th data-i18n="legal_editor_reconsent_col">Re-consent</th>
        <th data-i18n="actions">Actions</th>
      </tr></thead><tbody>${rows}</tbody></table></div>`;
  applyTranslations();
}

async function loadLegalVersion(id) {
  const res = await fetch(`/api/settings/legal/${id}/`);
  if (!res.ok) return;
  const stored = (await res.json()).version.content || {};
  const s = _legalState;
  _LEGAL_LANGS.forEach((lang) =>
    _LEGAL_DOCS.forEach((doc) => {
      const node = (stored[lang] || {})[doc];
      s.edits[lang][doc] = node ? _legalClone(node) : _legalClone(s.payload.defaults[lang][doc]);
    })
  );
  renderLegalEditorBody();
  showToast(
    t("legal_editor_loaded", "Version loaded into the editor. Publish to make it current.")
  );
}

async function publishLegalVersion() {
  const label = document.getElementById("legalNewLabel").value.trim();
  const btn = document.getElementById("legalPublishBtn");
  btn.disabled = true;
  const res = await fetch("/api/settings/legal/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      label,
      content: _legalState.edits,
      require_reconsent: document.getElementById("legalReconsent").checked,
    }),
  });
  btn.disabled = false;
  if (!res.ok) {
    const code = ((await res.json().catch(() => ({}))).error || "error").toString();
    showToast(
      t(`legal_editor_err_${code}`, t("legal_editor_err_error", "Could not publish.")),
      "error"
    );
    return;
  }
  showToast(t("legal_editor_published_ok", "New version published."));
  await renderLegalSettings();
}
