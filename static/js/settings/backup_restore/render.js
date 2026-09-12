"use strict";
// Backup & Restore settings tab implementation
// Supports direct download (client-side Save dialog), client upload (client-side Open dialog),
// and server-side backup management (list, restore, delete).

async function renderBackupRestoreSettings() {
  const contentDiv = document.getElementById("settingsContent");
  if (!contentDiv) return;

  // Fetch server-side backup list
  let backups = [];
  try {
    const res = await fetch("/api/settings/backup/list/?t=" + Date.now());
    const data = await res.json();
    backups = data.backups || [];
  } catch (e) {
  }

  const rows =
    backups.length > 0
      ? backups
          .map((b) => {
            const formattedSize = (b.size / 1024).toFixed(1) + " KB";
            // Simple date formatting
            const formattedDate = formatDate(b.created_at);

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
          })
          .join("")
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
            ${renderVendorAssetsUpdateCard()}
        </div>
    `;

  applyTranslations();
}

// Trigger Client-side download
