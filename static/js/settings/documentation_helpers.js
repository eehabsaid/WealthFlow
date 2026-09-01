"use strict";

let docHistorySortCol = "date";
let docHistorySortAsc = false;

function buildDocumentationSettingsLayoutHtml() {
  return `
        <div class="row g-4">
            <!-- SECTION 1: SCREENSHOT CAPTURE -->
            <div class="col-md-6">
                <div class="card card-custom mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h4 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_capture_title">Screenshot Capture</h4>
                    <p style="color:var(--text-secondary); font-size:0.9rem;" data-i18n="doc_engine_capture_desc">Capture application screenshots without generating documents.</p>
                    
                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_lbl_language">Language</label>
                        <select id="docLang" class="form-select" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);">
                            <option value="current" data-i18n="doc_lang_current">Current Language</option>
                            <option value="ALL" data-i18n="doc_lang_all">All Supported Languages</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_engine_theme">Theme</label>
                        <select id="docTheme" class="form-select" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);">
                            <option value="current" data-i18n="doc_theme_current">Current Theme</option>
                            <option value="dark" data-i18n="doc_theme_dark">Dark</option>
                            <option value="light" data-i18n="doc_theme_light">Light</option>
                            <option value="ALL" data-i18n="doc_theme_all">All Themes</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_engine_device_cat">Device Category</label>
                        <select id="docDeviceCat" class="form-select" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);" onchange="updateDocDeviceType()">
                            <option value="Desktop" data-i18n="doc_cat_desktop">Desktop</option>
                            <option value="Tablet" data-i18n="doc_cat_tablet">Tablet</option>
                            <option value="Mobile" data-i18n="doc_cat_mobile">Mobile</option>
                            <option value="ALL" data-i18n="doc_cat_all">All Devices</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_engine_device_type">Device Type</label>
                        <select id="docDeviceType" class="form-select" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);">
                            <!-- Populated dynamically -->
                        </select>
                    </div>

                    <!-- Capture Progress Info -->
                    <div id="captureProgressSection" class="p-3 mb-3 mt-4" style="background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:8px; display:none;">
                        <h6 style="color:var(--text-primary); margin-bottom: 12px;" data-i18n="doc_cap_prog_title">Capture Progress</h6>
                        <table class="table-borderless table-sm mb-0 w-100" style="color:var(--text-secondary); font-size:0.9rem; background:transparent !important;">
                            <tr><td style="width:50%; padding:4px 0;" data-i18n="doc_prog_status">Status:</td><td id="capStatus" style="color:var(--text-primary); padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_page">Page:</td><td id="capPage" style="padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_tab_nested">Tab/Nested:</td><td style="padding:4px 0;"><span id="capTab">-</span> / <span id="capNested">-</span></td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_modal">Modal:</td><td id="capModal" style="padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_config">Config:</td><td style="padding:4px 0;"><span id="capLang">-</span> | <span id="capTheme">-</span> | <span id="capDevice">-</span></td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_progress">Progress:</td><td id="capCount" style="padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_time">Time (Elapsed / Rem.):</td><td style="padding:4px 0;"><span id="capElapsed">-</span> / <span id="capRemaining">-</span></td></tr>
                        </table>
                    </div>

                    <div class="d-grid gap-2 mb-3">
                        <button class="btn btn-primary" id="btnCaptureScreenshots" onclick="handleCaptureClick()">
                            <i class="bi bi-camera me-2"></i><span data-i18n="doc_btn_capture">Capture Screenshots</span>
                        </button>
                        <button class="btn btn-danger" id="btnCancelCapture" onclick="cancelDocumentationProcess()" disabled>
                            <i class="bi bi-stop-fill me-2"></i><span data-i18n="doc_btn_cancel">Cancel Capture</span>
                        </button>
                    </div>
                    <div class="d-grid">
                        <button class="btn btn-sm btn-outline-secondary" onclick="openDocFolder('screenshots')">
                            <i class="bi bi-folder2-open me-1"></i> <span data-i18n="doc_open_screenshots">Open Screenshot Folder</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- SECTION 2: DOCUMENTATION GENERATION -->
            <div class="col-md-6">
                <div class="card card-custom mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h4 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_generate_title">Documentation Generation</h4>
                    <p style="color:var(--text-secondary); font-size:0.9rem;" data-i18n="doc_engine_generate_desc">Generate documents exclusively from existing screenshots.</p>
                    
                    <!-- Generation Progress Info -->
                    <div id="generationProgressSection" class="p-3 mb-4 mt-4" style="background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:8px; display:none;">
                        <h6 style="color:var(--text-primary); margin-bottom: 12px;" data-i18n="doc_gen_prog_title">Generation Progress</h6>
                        <table class="table-borderless table-sm mb-0 w-100" style="color:var(--text-secondary); font-size:0.9rem; background:transparent !important;">
                            <tr><td style="width:50%; padding:4px 0;" data-i18n="doc_prog_status">Status:</td><td id="genStatus" style="color:var(--text-primary); padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_doc">Current Document:</td><td id="genDoc" style="padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_format">Output Format:</td><td id="genFormat" style="padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_page_shot">Current Page/Screenshot:</td><td style="padding:4px 0;"><span id="genPage">-</span> / <span id="genScreenshot">-</span></td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_progress">Progress:</td><td id="genPercent" style="padding:4px 0;">-</td></tr>
                            <tr><td style="padding:4px 0;" data-i18n="doc_prog_time">Time (Elapsed / Rem.):</td><td style="padding:4px 0;"><span id="genElapsed">-</span> / <span id="genRemaining">-</span></td></tr>
                        </table>
                    </div>

                    <div class="d-grid gap-2 mb-3">
                        <button class="btn btn-success" id="btnGenerateAll" onclick="handleGenerateClick('all')">
                            <i class="bi bi-file-earmark-check me-2"></i><span data-i18n="doc_btn_gen_all">Generate All Documents</span>
                        </button>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-success flex-grow-1" id="btnGenerateUser" onclick="handleGenerateClick('user')" data-i18n="doc_btn_gen_user">User Guide</button>
                            <button class="btn btn-outline-success flex-grow-1" id="btnGenerateAdmin" onclick="handleGenerateClick('admin')" data-i18n="doc_btn_gen_admin">Admin Guide</button>
                            <button class="btn btn-outline-success flex-grow-1" id="btnGenerateTech" onclick="handleGenerateClick('technical')" data-i18n="doc_btn_gen_tech">Technical Guide</button>
                        </div>
                        <button class="btn btn-danger mt-2" id="btnCancelGeneration" onclick="cancelDocumentationProcess()" disabled>
                            <i class="bi bi-stop-fill me-2"></i><span data-i18n="doc_btn_cancel">Cancel Generation</span>
                        </button>
                    </div>
                    
                    <div class="d-grid mt-3">
                        <button class="btn btn-sm btn-outline-secondary" onclick="openDocFolder('generated')">
                            <i class="bi bi-folder2-open me-1"></i> <span data-i18n="doc_open_generated">Open Generated Folder</span>
                        </button>
                    </div>
                </div>

                <!-- Execution History -->
                <div class="card card-custom" style="background-color: var(--bg-secondary) !important; border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_history">Execution History</h5>
                        <button class="btn btn-sm btn-outline-secondary" onclick="loadDocHistory()">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                    </div>
                    
                    <div class="table-responsive" style="max-height: 250px; overflow-y: auto;">
                        <table class="data-table table table-sm table-hover align-middle mb-0" style="color:var(--text-primary); white-space:nowrap; font-size:0.85rem;">
                            <thead>
                                <tr>
                                    <th style="cursor:pointer;" onclick="sortDocHistory('date')" data-i18n="doc_engine_history_date">Date ↕</th>
                                    <th data-i18n="doc_engine_history_type">Type</th>
                                    <th data-i18n="doc_engine_history_dur">Dur.</th>
                                    <th data-i18n="doc_engine_history_config">Config/Files</th>
                                    <th data-i18n="doc_engine_history_tot_fail">Tot. / Fail</th>
                                    <th style="cursor:pointer;" onclick="sortDocHistory('status')" data-i18n="doc_engine_history_status">Status ↕</th>
                                </tr>
                            </thead>
                            <tbody id="docHistoryTableBody">
                                <tr><td colspan="6" class="text-center" style="color:var(--text-secondary)">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadDocHistory() {
  try {
    const tbody = document.getElementById("docHistoryTableBody");
    if (!tbody) return;
    const res = await fetch("/api/settings/documentation/history/?t=" + Date.now());
    const data = await res.json();
    docHistoryData = data.history || [];
    renderDocHistory();
  } catch (e) {
    console.error(e);
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
