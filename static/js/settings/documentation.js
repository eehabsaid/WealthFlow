"use strict";

let docIntervalId = null;
let docHistoryData = [];
let docHistorySortCol = 'date';
let docHistorySortAsc = false;
let deviceInventory = { desktop: [], tablet: [], mobile: [] };

async function renderDocumentationSettings() {
    const contentDiv = document.getElementById('settingsContent');
    if (!contentDiv) return;

    contentDiv.innerHTML = `
        <div class="row g-4">
            <!-- Left Column: Config and Output -->
            <div class="col-md-6">
                <!-- Section 1: Capture Configuration -->
                <div class="card card-custom mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h5 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_section1">Capture Configuration</h5>
                    
                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_lbl_language">Language</label>
                        <select id="docLang" class="form-select" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);">
                            <!-- Populated dynamically -->
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
                </div>

                <!-- Section 2: Output -->
                <div class="card card-custom mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h5 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_section2">Output Files</h5>
                    
                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_output_folder">Output Folder</label>
                        <input type="text" class="form-control" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);" value="docs/screenshots/" readonly>
                    </div>
                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_status_file">Status File</label>
                        <input type="text" class="form-control" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);" value="docs/generated/capture_status.json" readonly>
                    </div>
                    <div class="mb-3">
                        <label class="form-label" style="color:var(--text-primary); font-weight:500;" data-i18n="doc_readme">README</label>
                        <input type="text" class="form-control" style="background:var(--bg-primary); color:var(--text-primary); border:1px solid var(--border-color);" value="doc_engine/README.md" readonly>
                    </div>
                </div>

                <!-- Section 3: Controls -->
                <div class="card card-custom mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h5 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_section3">Controls</h5>
                    
                    <div class="d-grid gap-2 mb-3">
                        <button class="btn btn-primary-custom" id="btnGenerateDocs" onclick="startDocGeneration()">
                            <i class="bi bi-play-fill me-2"></i><span data-i18n="doc_btn_generate">Generate Documentation</span>
                        </button>
                        <button class="btn btn-outline-danger" id="btnCancelDocs" onclick="cancelDocGeneration()" disabled>
                            <i class="bi bi-stop-fill me-2"></i><span data-i18n="doc_btn_cancel">Cancel</span>
                        </button>
                    </div>
                    
                    <div class="d-flex gap-2 flex-wrap">
                        <button class="btn btn-sm btn-secondary-custom flex-grow-1" onclick="openDocFolder('screenshots')">
                            <i class="bi bi-folder2-open me-1"></i> <span data-i18n="doc_open_screenshots">Screenshots Folder</span>
                        </button>
                        <button class="btn btn-sm btn-secondary-custom flex-grow-1" onclick="openDocFolder('generated')">
                            <i class="bi bi-folder2-open me-1"></i> <span data-i18n="doc_open_generated">Generated Folder</span>
                        </button>
                        <button class="btn btn-sm btn-secondary-custom flex-grow-1" onclick="openDocFolder('readme')">
                            <i class="bi bi-file-text me-1"></i> <span data-i18n="doc_open_readme">README</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Right Column: Live Progress & History -->
            <div class="col-md-6">
                <!-- Section 4: Live Progress -->
                <div class="card card-custom mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h5 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_section4">Live Progress</h5>
                    
                    <style>
                        .doc-progress-table, .doc-progress-table tbody, .doc-progress-table tr, .doc-progress-table td {
                            background-color: transparent !important;
                            color: var(--text-primary) !important;
                        }
                    </style>
                    <div class="table-container table-responsive" style="background: transparent;">
                        <table class="table table-borderless table-sm mb-0 doc-progress-table" style="color:var(--text-primary);">
                            <tbody>
                                <tr>
                                    <td style="width: 40%; color:var(--text-secondary)" data-i18n="doc_prog_status">Status</td>
                                    <td id="docProgStatus" style="font-weight:600">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_progress">Progress</td>
                                    <td id="docProgCount">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_page">Current Page</td>
                                    <td id="docProgPage">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_tab">Current Tab</td>
                                    <td id="docProgTab">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_lang">Language</td>
                                    <td id="docProgLang">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_theme">Theme</td>
                                    <td id="docProgTheme">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_device">Device</td>
                                    <td id="docProgDevice">-</td>
                                </tr>
                                <tr>
                                    <td style="color:var(--text-secondary)" data-i18n="doc_prog_elapsed">Elapsed Time</td>
                                    <td id="docProgElapsed">-</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <div id="docProgErrors" class="mt-3 text-danger small" style="display:none; max-height:100px; overflow-y:auto; background:rgba(220,53,69,0.1); padding:10px; border-radius:6px;">
                        <!-- Errors go here -->
                    </div>
                </div>

                <!-- History -->
                <div class="card card-custom" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0" style="font-weight:600; color:var(--text-primary)" data-i18n="doc_engine_history">Execution History</h5>
                        <button class="btn btn-sm btn-outline-secondary" onclick="loadDocHistory()">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                    </div>
                    
                    <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                        <table class="data-table table table-sm table-hover align-middle mb-0" style="color:var(--text-primary); white-space:nowrap;">
                            <thead>
                                <tr>
                                    <th data-i18n="doc_hist_date" style="cursor:pointer;" onclick="sortDocHistory('date')">Date ↕</th>
                                    <th data-i18n="doc_hist_duration">Dur.</th>
                                    <th data-i18n="doc_hist_config">Config</th>
                                    <th data-i18n="doc_hist_by">By</th>
                                    <th data-i18n="doc_hist_total">Tot.</th>
                                    <th data-i18n="doc_hist_failed">Fail</th>
                                    <th data-i18n="doc_hist_status" style="cursor:pointer;" onclick="sortDocHistory('status')">Status ↕</th>
                                </tr>
                            </thead>
                            <tbody id="docHistoryTableBody">
                                <tr><td colspan="7" class="text-center" style="color:var(--text-secondary)">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

// Removed direct innerHTML override of languages to instead fetch dynamically.
    
    applyTranslations();
    updateDocDeviceType();
    
    // Fetch languages dynamically
    try {
        const res = await fetch('/api/settings/?t=' + Date.now());
        const data = await res.json();
        const langs = JSON.parse(data.settings.available_languages || '[]');
        
        const langSelect = document.getElementById('docLang');
        if (langSelect && langs.length > 0) {
            let optionsHtml = `
                <option value="current" data-i18n="doc_lang_current">Current Language</option>
                <option value="ALL" data-i18n="doc_lang_all">All Supported Languages</option>
            `;
            for (const l of langs) {
                optionsHtml += `<option value="${l.code}">${l.label || l.code}</option>`;
            }
            langSelect.innerHTML = optionsHtml;
            applyTranslations(langSelect); // Re-apply for new static options
        }
    } catch (e) {
        console.error("Failed to load languages for documentation:", e);
    }
    
    // Fetch device inventory
    try {
        const res = await fetch('/api/settings/documentation/devices/?t=' + Date.now());
        if (res.ok) {
            deviceInventory = await res.json();
        }
    } catch (e) {
        console.error("Failed to load device inventory:", e);
    }
    
    // Restore from localStorage
    const savedLang = localStorage.getItem('docEngineLang');
    const savedTheme = localStorage.getItem('docEngineTheme');
    const savedCat = localStorage.getItem('docEngineCat');
    const savedType = localStorage.getItem('docEngineType');
    
    if (savedLang) document.getElementById('docLang').value = savedLang;
    if (savedTheme) document.getElementById('docTheme').value = savedTheme;
    if (savedCat) {
        document.getElementById('docDeviceCat').value = savedCat;
        updateDocDeviceType();
        if (savedType) document.getElementById('docDeviceType').value = savedType;
    }
    
    // Start polling
    if (docIntervalId) clearInterval(docIntervalId);
    docIntervalId = setInterval(pollDocStatus, 1000);
    
    // Initial fetch
    pollDocStatus();
    loadDocHistory();
}

function updateDocDeviceType() {
    const cat = document.getElementById('docDeviceCat').value;
    const typeSelect = document.getElementById('docDeviceType');
    
    if (cat === 'ALL') {
        typeSelect.innerHTML = `<option value="ALL" data-i18n="doc_type_all_auto">Automatic</option>`;
        typeSelect.disabled = true;
        return;
    }
    
    typeSelect.disabled = false;
    
    let optionsList = [];
    const catLower = cat.toLowerCase();
    
    if (deviceInventory.categories && deviceInventory.categories[catLower]) {
        optionsList = deviceInventory.categories[catLower].filter(item => item.enabled !== false);
    }
    
    let optionsHtml = '';
    let defaultId = null;
    let firstEnabledId = null;
    
    for (const item of optionsList) {
        optionsHtml += `<option value="${item.id}">${item.display_name}</option>`;
        if (!firstEnabledId) {
            firstEnabledId = item.id;
        }
        if (item.default) {
            defaultId = item.id;
        }
    }
    typeSelect.innerHTML = optionsHtml;
    
    if (optionsList.length > 0) {
        if (defaultId) {
            typeSelect.value = defaultId;
        } else if (firstEnabledId) {
            typeSelect.value = firstEnabledId;
        }
    }
    
    applyTranslations();
}

async function startDocGeneration() {
    let lang = document.getElementById('docLang').value;
    if (lang === 'current') {
        lang = localStorage.getItem('language') || 'en';
    }
    
    let theme = document.getElementById('docTheme').value;
    if (theme === 'current') {
        theme = localStorage.getItem('theme') || 'dark';
    }
    
    const category = document.getElementById('docDeviceCat').value;
    const deviceType = document.getElementById('docDeviceType').value;
    
    // Persist to local storage
    localStorage.setItem('docEngineLang', document.getElementById('docLang').value);
    localStorage.setItem('docEngineTheme', document.getElementById('docTheme').value);
    localStorage.setItem('docEngineCat', category);
    localStorage.setItem('docEngineType', deviceType);
    
    try {
        const btn = document.getElementById('btnGenerateDocs');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Starting...';
        
        const res = await fetch('/api/settings/documentation/generate/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                language: lang,
                theme: theme,
                device_category: category,
                device_type: deviceType
            })
        });
        
        const data = await res.json();
        if (!res.ok) {
            alert("Error: " + (data.error || "Failed to start."));
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-play-fill me-2"></i><span data-i18n="doc_btn_generate">Generate Documentation</span>';
        }
    } catch (e) {
        console.error(e);
        alert("Failed to start generation.");
    }
}

async function cancelDocGeneration() {
    try {
        const btn = document.getElementById('btnCancelDocs');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Cancelling...';
        
        await fetch('/api/settings/documentation/cancel/', { method: 'POST' });
        
        setTimeout(pollDocStatus, 500); // Immediate poll
    } catch (e) {
        console.error(e);
    }
}

async function openDocFolder(target) {
    try {
        const res = await fetch('/api/settings/documentation/open/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target })
        });
        const data = await res.json();
        if (!res.ok) {
            if (typeof showToast === "function") {
                showToast(data.error || "Failed to open folder.", "error");
            } else {
                console.error(data.error);
            }
        }
    } catch (e) {
        if (typeof showToast === "function") {
            showToast("Failed to open folder.", "error");
        } else {
            console.error(e);
        }
    }
}

async function loadDocHistory() {
    try {
        const tbody = document.getElementById('docHistoryTableBody');
        if (!tbody) return;
        
        const res = await fetch('/api/settings/documentation/history/?t=' + Date.now());
        const data = await res.json();
        docHistoryData = data.history || [];
        renderDocHistory();
    } catch (e) {
        console.error(e);
    }
}

function sortDocHistory(col) {
    if (docHistorySortCol === col) {
        docHistorySortAsc = !docHistorySortAsc;
    } else {
        docHistorySortCol = col;
        docHistorySortAsc = (col === 'status'); // status default asc (alphabetical)
    }
    renderDocHistory();
}

function renderDocHistory() {
    const tbody = document.getElementById('docHistoryTableBody');
    if (!tbody) return;
    
    if (docHistoryData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center" style="color:var(--text-secondary)">No history found.</td></tr>';
        return;
    }
    
    const sorted = [...docHistoryData].sort((a, b) => {
        let valA = a[docHistorySortCol];
        let valB = b[docHistorySortCol];
        if (valA < valB) return docHistorySortAsc ? -1 : 1;
        if (valA > valB) return docHistorySortAsc ? 1 : -1;
        return 0;
    });
    
    tbody.innerHTML = sorted.map(item => `
        <tr>
            <td style="color:var(--text-secondary)">${item.date}</td>
            <td>${item.duration}</td>
            <td><small>${item.language.toUpperCase()} | ${item.theme} | ${item.device}</small></td>
            <td>${item.created_by}</td>
            <td>${item.screenshots}</td>
            <td>${item.failed > 0 ? '<span class="text-danger">' + item.failed + '</span>' : item.failed}</td>
            <td>
                <span class="badge ${item.status === 'COMPLETED' ? 'bg-success' : (item.status === 'CANCELLED' ? 'bg-warning' : (item.status === 'RUNNING' ? 'bg-info' : 'bg-danger'))}">
                    ${item.status}
                </span>
            </td>
        </tr>
    `).join('');
}

async function pollDocStatus() {
    const elStatus = document.getElementById('docProgStatus');
    if (!elStatus) {
        // UI is unmounted
        if (docIntervalId) clearInterval(docIntervalId);
        return;
    }
    
    try {
        const res = await fetch('/api/settings/documentation/status/?t=' + Date.now());
        const statusData = await res.json();
        
        const isRunning = statusData.status === 'RUNNING';
        
        const btnGen = document.getElementById('btnGenerateDocs');
        const btnCan = document.getElementById('btnCancelDocs');
        
        if (isRunning) {
            btnGen.disabled = true;
            btnGen.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Documentation generation already running.';
            btnCan.disabled = false;
            btnCan.innerHTML = '<i class="bi bi-stop-fill me-2"></i><span data-i18n="doc_btn_cancel">Cancel</span>';
        } else {
            btnGen.disabled = false;
            btnGen.innerHTML = '<i class="bi bi-play-fill me-2"></i><span data-i18n="doc_btn_generate">Generate Documentation</span>';
            btnCan.disabled = true;
            btnCan.innerHTML = '<i class="bi bi-stop-fill me-2"></i><span data-i18n="doc_btn_cancel">Cancel</span>';
            applyTranslations(btnGen);
            applyTranslations(btnCan);
        }
        
        // Map the internal 'finished' state from playwright to 'COMPLETED' for display
        let displayStatus = statusData.status;
        if (displayStatus === 'finished') displayStatus = 'COMPLETED';
        if (displayStatus === 'running') displayStatus = 'RUNNING';
        if (displayStatus === 'cancelled') displayStatus = 'CANCELLED';
        
        elStatus.textContent = displayStatus || '-';
        if (displayStatus === 'COMPLETED') {
            elStatus.textContent = "Completed Successfully";
            elStatus.style.color = "var(--accent-primary)";
        } else if (displayStatus === 'CANCELLED') {
            elStatus.textContent = "Cancelled";
            elStatus.style.color = "var(--text-secondary)";
        } else if (displayStatus === 'FAILED') {
            elStatus.textContent = "Failed";
            elStatus.style.color = "#dc3545";
        } else if (displayStatus === 'RUNNING') {
            elStatus.style.color = "var(--text-primary)";
        }
        
        if (statusData.total) {
            document.getElementById('docProgCount').innerText = `${statusData.progress || 0} / ${statusData.total}`;
        } else {
            document.getElementById('docProgCount').innerText = '-';
        }
        
        document.getElementById('docProgPage').textContent = statusData.page || '-';
        document.getElementById('docProgTab').textContent = statusData.tab || '-';
        document.getElementById('docProgLang').textContent = statusData.language || '-';
        document.getElementById('docProgTheme').textContent = statusData.theme || '-';
        document.getElementById('docProgDevice').textContent = statusData.device || '-';
        
        const totalSeconds = statusData.elapsed_seconds || 0;
        const mm = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
        const ss = String(totalSeconds % 60).padStart(2, '0');
        document.getElementById('docProgElapsed').textContent = `${mm}:${ss}`;
        
        const errorsDiv = document.getElementById('docProgErrors');
        if (statusData.failed_pages && statusData.failed_pages.length > 0) {
            errorsDiv.style.display = 'block';
            errorsDiv.innerHTML = '<strong>Errors:</strong><br>' + statusData.failed_pages.map(f => f.route + ': ' + f.error).join('<br>');
        } else {
            errorsDiv.style.display = 'none';
        }
        
        if (!isRunning && ['COMPLETED', 'CANCELLED', 'FAILED'].includes(displayStatus)) {
            if (docIntervalId) {
                clearInterval(docIntervalId);
                docIntervalId = null;
            }
            loadDocHistory(); // refresh history once done
        }
        
    } catch (e) {
        console.error("Status poll failed:", e);
    }
}

// Attach to window for routing
window.renderDocumentationSettings = renderDocumentationSettings;
window.updateDocDeviceType = updateDocDeviceType;
window.startDocGeneration = startDocGeneration;
window.cancelDocGeneration = cancelDocGeneration;
window.openDocFolder = openDocFolder;
window.loadDocHistory = loadDocHistory;
