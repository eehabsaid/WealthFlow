"use strict";
// Backup & Restore settings tab implementation
// Supports direct download (client-side Save dialog), client upload (client-side Open dialog),
// and server-side backup management (list, restore, delete).

async function renderBackupRestoreSettings() {
    const contentDiv = document.getElementById('settingsContent');
    if (!contentDiv) return;

    // Fetch server-side backup list
    let backups = [];
    try {
        const res = await fetch('/api/settings/backup/list/?t=' + Date.now());
        const data = await res.json();
        backups = data.backups || [];
    } catch (e) {
        console.error("Failed to load server backups list", e);
    }

    const rows = backups.length > 0 
        ? backups.map(b => {
            const formattedSize = (b.size / 1024).toFixed(1) + " KB";
            // Simple date formatting
            const dateObj = new Date(b.created_at);
            const formattedDate = dateObj.toLocaleDateString() + " " + dateObj.toLocaleTimeString();

            return `
            <tr>
                <td><code style="color:var(--accent-primary);font-weight:600">${b.filename}</code></td>
                <td>${formattedSize}</td>
                <td>${formattedDate}</td>
                <td>
                    <button class="btn btn-sm btn-outline-success me-2" onclick="restoreServerBackup('${b.filename}')">
                        <i class="bi bi-arrow-counterclockwise"></i> <span data-i18n="btn_restore">Restore</span>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteServerBackup('${b.filename}')">
                        <i class="bi bi-trash"></i> <span data-i18n="btn_delete">Delete</span>
                    </button>
                </td>
            </tr>`;
        }).join('')
        : `<tr><td colspan="4" class="text-center" data-i18n="no_backups_found" style="padding: 20px; color: var(--text-secondary) !important;">No backups found on server.</td></tr>`;

    contentDiv.innerHTML = `
        <div class="row g-4">
            <!-- Left Panel: Client-side actions -->
            <div class="col-md-5">
                <div class="card card-custom h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <h5 class="mb-3" style="font-weight:600; color:var(--text-primary)" data-i18n="backup_restore_title">Backup & Restore Data</h5>
                    <p class="small mb-4" style="color: var(--text-secondary) !important;">
                        Download a portable backup archive of your database (including all Arabic notes, dates, and files) directly to your local computer, or upload a previously saved file to restore it.
                    </p>

                    <div class="d-grid gap-3">
                        <!-- Create & Download Button -->
                        <button class="btn btn-primary-custom py-2" onclick="triggerDownloadBackup()">
                            <i class="bi bi-download me-2"></i>
                            <span data-i18n="btn_create_download_backup">Create & Download Backup</span>
                        </button>

                        <!-- Upload File Input and Button -->
                        <input type="file" id="backupFileInput" accept=".wfbackup" style="display:none" onchange="triggerUploadRestore(this)">
                        <button class="btn-secondary-custom py-2 justify-content-center" onclick="document.getElementById('backupFileInput').click()">
                            <i class="bi bi-upload me-2"></i>
                            <span data-i18n="btn_upload_restore_backup">Upload & Restore Backup</span>
                        </button>
                    </div>

                    <hr class="my-4" style="border-color: var(--border-color);">

                    <!-- Restore Options -->
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="restoreOverwriteOpt" checked>
                        <label class="form-check-label small ms-2" style="color: var(--text-secondary) !important;" for="restoreOverwriteOpt" data-i18n="restore_overwrite_checkbox">
                            Overwrite existing records (replaces matching records by key/ID)
                        </label>
                    </div>
                </div>
            </div>

            <!-- Right Panel: Server-side backups list -->
            <div class="col-md-7">
                <div class="card card-custom h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px">
                        <h5 style="font-weight:600; color:var(--text-primary)" data-i18n="server_backups_list">Server Backups</h5>
                        <button class="btn btn-sm btn-primary-custom" onclick="createServerBackup()">
                            <i class="bi bi-plus-lg"></i> <span data-i18n="btn_create_server_backup">Create Server Backup</span>
                        </button>
                    </div>

                    <div class="table-container" style="max-height: 400px; overflow-y: auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th data-i18n="backup_filename">Filename</th>
                                    <th data-i18n="backup_size">Size</th>
                                    <th data-i18n="backup_created_at">Created At</th>
                                    <th data-i18n="backup_actions">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    applyTranslations();
}

// Trigger Client-side download
function triggerDownloadBackup() {
    // Standard direct browser download by navigating or opening the endpoint
    // This prompts the native Save File Dialog Window.
    const url = '/api/settings/backup/create/?download=true';
    window.location.href = url;
}

// Trigger Client-side restore (upload)
async function triggerUploadRestore(input) {
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    const overwrite = document.getElementById('restoreOverwriteOpt')?.checked || false;

    const confirmMsg = t('restore_confirm', 'Are you sure you want to restore this backup? This will modify database records.');
    if (!confirm(confirmMsg)) {
        input.value = ''; // Reset file input
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showLoader();
    try {
        const res = await fetch(`/api/settings/backup/restore/?overwrite=${overwrite}`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            showAlert(t('restore_success', 'Restore completed successfully!'), 'success');
            // Re-render settings page to reflect potential schema changes / updates
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showAlert(data.error || 'Restore failed', 'danger');
        }
    } catch (e) {
        showAlert('Network error: ' + e.message, 'danger');
    } finally {
        hideLoader();
        input.value = ''; // Reset file input
    }
}

// Trigger Server-side backup creation
async function createServerBackup() {
    showLoader();
    try {
        const res = await fetch('/api/settings/backup/create/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (data.success) {
            showAlert(t('backup_success', 'Backup created successfully!'), 'success');
            await renderBackupRestoreSettings(); // Refresh list
        } else {
            showAlert(data.error || 'Backup creation failed', 'danger');
        }
    } catch (e) {
        showAlert('Network error: ' + e.message, 'danger');
    } finally {
        hideLoader();
    }
}

// Trigger Server-side restore
async function restoreServerBackup(filename) {
    const overwrite = document.getElementById('restoreOverwriteOpt')?.checked || false;

    const confirmMsg = t('restore_confirm', 'Are you sure you want to restore this backup? This will modify database records.');
    if (!confirm(confirmMsg)) return;

    showLoader();
    try {
        const res = await fetch(`/api/settings/backup/restore/?overwrite=${overwrite}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();

        if (data.success) {
            showAlert(t('restore_success', 'Restore completed successfully!'), 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showAlert(data.error || 'Restore failed', 'danger');
        }
    } catch (e) {
        showAlert('Network error: ' + e.message, 'danger');
    } finally {
        hideLoader();
    }
}

// Trigger Server-side delete
async function deleteServerBackup(filename) {
    const confirmMsg = t('delete_confirm', 'Are you sure you want to delete this backup file?');
    if (!confirm(confirmMsg)) return;

    showLoader();
    try {
        const res = await fetch('/api/settings/backup/delete/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();

        if (data.success) {
            showAlert('Backup deleted successfully', 'success');
            await renderBackupRestoreSettings(); // Refresh list
        } else {
            showAlert(data.error || 'Deletion failed', 'danger');
        }
    } catch (e) {
        showAlert('Network error: ' + e.message, 'danger');
    } finally {
        hideLoader();
    }
}

// Utility Loader helpers (checks if global showLoader/hideLoader exists, or falls back to console/minimal UI)
function showLoader() {
    const globalLoader = document.getElementById('global-loader');
    if (globalLoader) {
        globalLoader.style.display = 'flex';
    } else {
        // Fallback loader if not present
        const loader = document.createElement('div');
        loader.id = 'backup-temp-loader';
        loader.style = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:9999;color:white;font-size:20px;';
        loader.innerHTML = '<div>Processing ...</div>';
        document.body.appendChild(loader);
    }
}

function hideLoader() {
    const globalLoader = document.getElementById('global-loader');
    if (globalLoader) {
        globalLoader.style.display = 'none';
    }
    const tempLoader = document.getElementById('backup-temp-loader');
    if (tempLoader) {
        tempLoader.remove();
    }
}

function showAlert(message, type) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        alert(message);
    }
}
