"use strict";
// documentation_history.js — Documentation execution history: fetch,
// sort, and render. Split out of the former documentation_helpers.js
// monolith; see documentation_layout.js for the page layout builder.

async function loadDocHistory() {
  try {
    const tbody = document.getElementById("docHistoryTableBody");
    if (!tbody) return;
    const res = await fetch("/api/settings/documentation/history/?t=" + Date.now());
    const data = await res.json();
    docHistoryData = data.history || [];
    renderDocHistory();
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
}

function sortDocHistory(col) {
  if (docHistorySortCol === col) docHistorySortAsc = !docHistorySortAsc;
  else {
    docHistorySortCol = col;
    docHistorySortAsc = col === "status";
  }
  renderDocHistory();
}

function renderDocHistory() {
  const tbody = document.getElementById("docHistoryTableBody");
  if (!tbody) return;
  if (typeof docHistoryData === "undefined" || docHistoryData.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="text-center" style="color:var(--text-secondary)" data-i18n="doc_engine_none">No history found.</td></tr>';
    if (typeof applyTranslations === "function") applyTranslations(tbody);
    return;
  }
  const sorted = [...docHistoryData].sort((a, b) => {
    let valA = a[docHistorySortCol];
    let valB = b[docHistorySortCol];
    if (valA < valB) return docHistorySortAsc ? -1 : 1;
    if (valA > valB) return docHistorySortAsc ? 1 : -1;
    return 0;
  });
  tbody.innerHTML = sorted
    .map((item) => {
      let filesInfo = "";
      if (item.type === "GENERATION" || item.type === "BOTH") {
        let noneText = typeof window.t === "function" ? window.t("doc_engine_none") : "None";
        filesInfo =
          item.files_generated && item.files_generated.length > 0
            ? item.files_generated.join(", ")
            : noneText;
      } else {
        filesInfo = `${item.language.toUpperCase()} | ${item.theme} | ${item.device}`;
      }

      let typeBadge =
        item.type === "CAPTURE"
          ? "bg-primary"
          : item.type === "GENERATION"
            ? "bg-success"
            : "bg-secondary";
      let statusBadge =
        item.status === "COMPLETED"
          ? "bg-success"
          : item.status === "CANCELLED"
            ? "bg-warning text-dark"
            : item.status === "RUNNING"
              ? "bg-info"
              : "bg-danger";

      let typeTranslationKey =
        item.type === "CAPTURE"
          ? "doc_engine_type_capture"
          : item.type === "GENERATION"
            ? "doc_engine_type_generation"
            : "doc_engine_type_both";
      let statusTranslationKey =
        item.status === "COMPLETED"
          ? "doc_engine_status_completed"
          : item.status === "CANCELLED"
            ? "doc_engine_status_cancelled"
            : item.status === "RUNNING"
              ? "doc_engine_status_running"
              : "doc_engine_status_failed";

      return `<tr>
            <td style="color:var(--text-secondary)">${item.date}</td>
            <td><span class="badge ${typeBadge}" data-i18n="${typeTranslationKey}">${item.type}</span></td>
            <td>${item.duration}</td>
            <td style="max-width:150px; overflow:hidden; text-overflow:ellipsis;" title="${filesInfo}">${filesInfo}</td>
            <td>${item.screenshots} / <span class="${item.failed > 0 ? "text-danger" : ""}">${item.failed}</span></td>
            <td><span class="badge ${statusBadge}" data-i18n="${statusTranslationKey}">${item.status}</span></td>
        </tr>`;
    })
    .join("");
  if (typeof applyTranslations === "function") applyTranslations(tbody);
}

window.buildDocumentationSettingsLayoutHtml = buildDocumentationSettingsLayoutHtml;
window.loadDocHistory = loadDocHistory;
window.sortDocHistory = sortDocHistory;
window.renderDocHistory = renderDocHistory;
