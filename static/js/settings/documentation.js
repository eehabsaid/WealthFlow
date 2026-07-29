"use strict";

let docIntervalId = null;
let docHistoryData = [];
let deviceInventory = { desktop: [], tablet: [], mobile: [] };
let isCancelling = false;
let activeProcessType = null; // 'CAPTURE', 'GENERATION', or null

async function renderDocumentationSettings() {
    const contentDiv = document.getElementById('settingsContent');
    if (!contentDiv) return;

    if (typeof buildDocumentationSettingsLayoutHtml === 'function') {
        contentDiv.innerHTML = buildDocumentationSettingsLayoutHtml();
    }

    applyTranslations();
    updateDocDeviceType();
    
    try {
        const res = await fetch('/api/settings/?t=' + Date.now());
        const data = await res.json();
        const langs = JSON.parse(data.settings.available_languages || '[]');
        const langSelect = document.getElementById('docLang');
        if (langSelect && langs.length > 0) {
            let optionsHtml = '<option value="current" data-i18n="doc_lang_current">Current Language</option><option value="ALL" data-i18n="doc_lang_all">All Supported Languages</option>';
            for (const l of langs) {
                optionsHtml += `<option value="${l.code}">${l.label || l.code}</option>`;
            }
            langSelect.innerHTML = optionsHtml;
            applyTranslations(langSelect);
        }
    } catch (e) {
        console.error("Failed to load languages:", e);
    }
    
    try {
        const res = await fetch('/api/settings/documentation/devices/?t=' + Date.now());
        if (res.ok) deviceInventory = await res.json();
    } catch (e) {
        console.error("Failed to load device inventory:", e);
    }
    
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
    
    if (docIntervalId) clearInterval(docIntervalId);
    pollDocStatus(); // check once on load
    loadDocHistory();
}

function updateDocDeviceType() {
    const cat = document.getElementById('docDeviceCat').value;
    const typeSelect = document.getElementById('docDeviceType');
    if (cat === 'ALL') {
        typeSelect.innerHTML = '<option value="ALL">Automatic</option>';
        typeSelect.disabled = true;
        return;
    }
    typeSelect.disabled = false;
    let optionsList = [];
    if (deviceInventory.categories && deviceInventory.categories[cat.toLowerCase()]) {
        optionsList = deviceInventory.categories[cat.toLowerCase()].filter(item => item.enabled !== false);
    }
    let optionsHtml = '';
    let defaultId = null;
    let firstEnabledId = null;
    for (const item of optionsList) {
        let i18nAttr = item.display_name === 'Current Resolution' ? ' data-i18n="doc_engine_current_res"' : '';
        optionsHtml += `<option value="${item.id}"${i18nAttr}>${item.display_name}</option>`;
        if (!firstEnabledId) firstEnabledId = item.id;
        if (item.default) defaultId = item.id;
    }
    typeSelect.innerHTML = optionsHtml;
    if (optionsList.length > 0) {
        typeSelect.value = defaultId || firstEnabledId;
    }
    if (typeof applyTranslations === 'function') applyTranslations(typeSelect);
}

function showValidationDialog(title, errors) {
    const errorKeys = {
        "Node.js is not installed or not in PATH.": "doc_err_node_missing",
        "npm is not installed or not in PATH.": "doc_err_npm_missing",
        "Playwright is not installed.": "doc_err_playwright_missing",
        "Screenshots directory is not writable.": "doc_err_capture_dir_not_writable",
        "Cannot create screenshots directory.": "doc_err_capture_dir_not_created",
        "Screenshot folder does not exist.": "doc_err_screenshots_folder_missing",
        "Screenshot folder contains no screenshots.": "doc_err_screenshots_empty",
        "manifest.json does not exist.": "doc_err_manifest_missing",
        "manifest.json is not valid JSON.": "doc_err_manifest_invalid",
        "capture_metadata.json does not exist.": "doc_err_metadata_missing",
        "capture_metadata.json is not valid JSON.": "doc_err_metadata_invalid",
        "page_descriptions.json does not exist.": "doc_err_descriptions_missing",
        "Output directory is not writable.": "doc_err_output_not_writable",
        "Cannot create output directory.": "doc_err_output_not_created",
        "Playwright PDF renderer (html_to_pdf.js) is missing.": "doc_err_pdf_script_missing",
        "python-docx is not installed.": "doc_err_python_docx_missing",
        "pdf2docx is not installed.": "doc_err_pdf2docx_missing"
    };

    const titleKeys = {
        "Capture Validation Failed": "doc_err_title_capture",
        "Generation Validation Failed": "doc_err_title_generation",
        "Error": "doc_err_title_error"
    };

    const tFallback = (key, defaultText) => (typeof window.t === 'function') ? window.t(key, defaultText) : defaultText;

    const translatedTitle = tFallback(titleKeys[title] || title, title);
    const translatedMissingPrereqs = tFallback("doc_err_missing_prereqs", "The following prerequisites are missing or invalid:");
    const translatedCloseBtn = tFallback("btn_close", "Close");

    const errorItems = errors.map(e => {
        const translatedErr = tFallback(errorKeys[e] || e, e);
        return `<li>${translatedErr}</li>`;
    }).join('');

    const modalHtml = `
        <div class="modal-header" style="border-color:var(--border-color);">
            <h5 class="modal-title text-danger"><i class="bi bi-exclamation-triangle-fill me-2"></i>${translatedTitle}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" style="filter: invert(var(--invert-icons, 0));"></button>
        </div>
        <div class="modal-body">
            <p style="color:var(--text-primary);">${translatedMissingPrereqs}</p>
            <ul style="color:#ff6b6b; font-weight:500;">
                ${errorItems}
            </ul>
        </div>
        <div class="modal-footer" style="border-color:var(--border-color);">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="if(typeof closeModal === 'function') closeModal();">${translatedCloseBtn}</button>
        </div>
    `;
    if (typeof showModal === 'function') {
        showModal(modalHtml);
    } else {
        alert(`${translatedTitle}\n\n${translatedMissingPrereqs}\n${errors.map(e => tFallback(errorKeys[e] || e, e)).join('\n')}`);
    }
}

async function handleCaptureClick() {
    try {
        const res = await fetch('/api/settings/documentation/validate-capture/');
        const data = await res.json();
        if (data.valid) {
            startCapture();
        } else {
            showValidationDialog('Capture Validation Failed', data.errors);
        }
    } catch (e) {
        showValidationDialog('Error', ['Failed to run capture validation. Server may be down.']);
    }
}

async function handleGenerateClick(docType) {
    try {
        const res = await fetch('/api/settings/documentation/validate-generate/');
        const data = await res.json();
        if (data.valid) {
            startGeneration(docType);
        } else {
            showValidationDialog('Generation Validation Failed', data.errors);
        }
    } catch (e) {
        showValidationDialog('Error', ['Failed to run generation validation.']);
    }
}

async function startCapture() {
    let lang = document.getElementById('docLang').value;
    if (lang === 'current') lang = localStorage.getItem('language') || 'en';
    let theme = document.getElementById('docTheme').value;
    if (theme === 'current') theme = localStorage.getItem('theme') || 'dark';
    const category = document.getElementById('docDeviceCat').value;
    const deviceType = document.getElementById('docDeviceType').value;
    
    localStorage.setItem('docEngineLang', document.getElementById('docLang').value);
    localStorage.setItem('docEngineTheme', document.getElementById('docTheme').value);
    localStorage.setItem('docEngineCat', category);
    localStorage.setItem('docEngineType', deviceType);
    
    try {
        const btn = document.getElementById('btnCaptureScreenshots');
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Starting...';
        
        const res = await fetch('/api/settings/documentation/capture/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang, theme: theme, device_category: category, device_type: deviceType })
        });
        const data = await res.json();
        if (!res.ok) {
            alert("Error: " + (data.error || "Failed to start capture."));
        } else {
            if (!docIntervalId) docIntervalId = setInterval(pollDocStatus, 1000);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to start capture.");
    }
}

async function startGeneration(docType) {
    try {
        const res = await fetch('/api/settings/documentation/generate-docs/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ docs: docType })
        });
        const data = await res.json();
        if (!res.ok) {
            alert("Error: " + (data.error || "Failed to start generation."));
        } else {
            if (!docIntervalId) docIntervalId = setInterval(pollDocStatus, 1000);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to start generation.");
    }
}

async function cancelDocumentationProcess() {
    try {
        isCancelling = true;
        await fetch('/api/settings/documentation/cancel/', { method: 'POST' });
        setTimeout(pollDocStatus, 500);
    } catch (e) {
        console.error(e);
        isCancelling = false;
    }
}

async function openDocFolder(target) {
    try {
        await fetch('/api/settings/documentation/open/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target })
        });
    } catch (e) {
        console.error(e);
    }
}

// (History table rendering functions loadDocHistory, sortDocHistory, renderDocHistory are loaded from documentation_helpers.js)

async function pollDocStatus() {
    const btnCap = document.getElementById('btnCaptureScreenshots');
    if (!btnCap) return;
    
    try {
        const res = await fetch('/api/settings/documentation/status/?t=' + Date.now());
        const statusData = await res.json();
        const rawStatus = (statusData.status || '').toUpperCase();
        const isRunning = rawStatus === 'RUNNING';
        
        const capProgress = document.getElementById('captureProgressSection');
        const genProgress = document.getElementById('generationProgressSection');
        const btnCancelCap = document.getElementById('btnCancelCapture');
        const btnCancelGen = document.getElementById('btnCancelGeneration');
        
        const btnGenAll = document.getElementById('btnGenerateAll');
        const btnGenUser = document.getElementById('btnGenerateUser');
        const btnGenAdmin = document.getElementById('btnGenerateAdmin');
        const btnGenTech = document.getElementById('btnGenerateTech');
        
        if (isRunning) {
            if (!docIntervalId) {
                docIntervalId = setInterval(pollDocStatus, 1000);
            }
            activeProcessType = statusData.device === 'N/A' ? 'GENERATION' : 'CAPTURE';
            
            if (activeProcessType === 'CAPTURE') {
                btnCap.disabled = true;
                btnCap.innerHTML = '<i class="bi bi-camera me-2"></i><span data-i18n="doc_btn_running_capture">Running Capture...</span>';
                if (typeof applyTranslations === 'function') applyTranslations(btnCap);
                if (!isCancelling) btnCancelCap.disabled = false;
                capProgress.style.display = 'block';
                
                document.getElementById('capStatus').textContent = statusData.page || 'Capturing...';
                document.getElementById('capPage').textContent = statusData.page || '-';
                document.getElementById('capTab').textContent = statusData.tab || '-';
                document.getElementById('capNested').textContent = statusData.nested_tab || '-';
                document.getElementById('capModal').textContent = statusData.modal || '-';
                document.getElementById('capLang').textContent = statusData.language || '-';
                document.getElementById('capTheme').textContent = statusData.theme || '-';
                document.getElementById('capDevice').textContent = statusData.device || '-';
                document.getElementById('capCount').textContent = `${statusData.screenshots_count || 0} / ${statusData.total || '?'}`;
                const mm = String(Math.floor((statusData.elapsed_seconds || 0) / 60)).padStart(2, '0');
                const ss = String((statusData.elapsed_seconds || 0) % 60).padStart(2, '0');
                document.getElementById('capElapsed').textContent = `${mm}:${ss}`;
                
                btnGenAll.disabled = true; btnGenUser.disabled = true; btnGenAdmin.disabled = true; btnGenTech.disabled = true;
            } else {
                btnGenAll.disabled = true; btnGenUser.disabled = true; btnGenAdmin.disabled = true; btnGenTech.disabled = true;
                
                let activeBtn = btnGenAll;
                let activeText = 'doc_btn_generating';
                let defaultText = 'Generating...';
                if (statusData.current_doc === 'User') { activeBtn = btnGenUser; }
                else if (statusData.current_doc === 'Admin') { activeBtn = btnGenAdmin; }
                else if (statusData.current_doc === 'Technical') { activeBtn = btnGenTech; }
                
                activeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><span data-i18n="' + activeText + '">' + defaultText + '</span>';
                if (typeof applyTranslations === 'function') applyTranslations(activeBtn);
                if (!isCancelling) btnCancelGen.disabled = false;
                genProgress.style.display = 'block';
                
                document.getElementById('genStatus').textContent = statusData.page || 'Building...';
                document.getElementById('genDoc').textContent = statusData.current_doc || '-';
                document.getElementById('genFormat').textContent = statusData.current_format || '-';
                document.getElementById('genPage').textContent = statusData.page || '-';
                document.getElementById('genScreenshot').textContent = statusData.screenshots_count || '-';
                document.getElementById('genPercent').textContent = `${statusData.progress || 0}%`;
                const mm = String(Math.floor((statusData.elapsed_seconds || 0) / 60)).padStart(2, '0');
                const ss = String((statusData.elapsed_seconds || 0) % 60).padStart(2, '0');
                document.getElementById('genElapsed').textContent = `${mm}:${ss}`;
                
                btnCap.disabled = true;
            }
        } else {
            btnCap.disabled = false;
            btnCap.innerHTML = '<i class="bi bi-camera me-2"></i><span data-i18n="doc_btn_capture">Capture Screenshots</span>';
            if (typeof applyTranslations === 'function') applyTranslations(btnCap);
            btnCancelCap.disabled = true;
            
            btnGenAll.disabled = false; btnGenUser.disabled = false; btnGenAdmin.disabled = false; btnGenTech.disabled = false;
            btnGenAll.innerHTML = '<i class="bi bi-file-earmark-check me-2"></i><span data-i18n="doc_btn_gen_all">Generate All Documents</span>';
            btnGenUser.innerHTML = '<i class="bi bi-person-badge me-2"></i><span data-i18n="doc_btn_gen_user">User Guide</span>';
            btnGenAdmin.innerHTML = '<i class="bi bi-shield-lock me-2"></i><span data-i18n="doc_btn_gen_admin">Admin Guide</span>';
            btnGenTech.innerHTML = '<i class="bi bi-code-slash me-2"></i><span data-i18n="doc_btn_gen_tech">Technical Guide</span>';
            if (typeof applyTranslations === 'function') {
                applyTranslations(btnGenAll); applyTranslations(btnGenUser); applyTranslations(btnGenAdmin); applyTranslations(btnGenTech);
            }
            btnCancelGen.disabled = true;
            
            if (['COMPLETED', 'CANCELLED', 'FAILED'].includes(rawStatus)) {
                if (activeProcessType === 'CAPTURE') {
                    document.getElementById('capStatus').textContent = rawStatus;
                    document.getElementById('capStatus').style.color = rawStatus === 'COMPLETED' ? 'var(--accent-primary)' : '#ff6b6b';
                } else if (activeProcessType === 'GENERATION') {
                    document.getElementById('genStatus').textContent = rawStatus;
                    document.getElementById('genStatus').style.color = rawStatus === 'COMPLETED' ? 'var(--accent-primary)' : '#ff6b6b';
                }
            }
            
            if (!isRunning) {
                isCancelling = false;
                activeProcessType = null;
                if (docIntervalId) {
                    clearInterval(docIntervalId);
                    docIntervalId = null;
                }
                if (['COMPLETED', 'CANCELLED', 'FAILED'].includes(rawStatus)) {
                    loadDocHistory();
                }
            }
        }
    } catch (e) {
        console.error("Status poll failed:", e);
    }
}

window.renderDocumentationSettings = renderDocumentationSettings;
window.updateDocDeviceType = updateDocDeviceType;
window.handleCaptureClick = handleCaptureClick;
window.handleGenerateClick = handleGenerateClick;
window.cancelDocumentationProcess = cancelDocumentationProcess;
window.openDocFolder = openDocFolder;
window.loadDocHistory = loadDocHistory;
