"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings: "Autonomous App Scan" card markup (split from render_settings_form.js).

window.AIA.buildPlatformCardHtml = function () {
  return `
        <div class="si-modern-card p-4" id="aiPlatformScanCard">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h5 class="fw-bold mb-1" style="color:var(--text-primary);">
                        <i class="bi bi-radar text-primary me-2"></i> <span data-i18n="ai_platform_scan_title">${t("ai_platform_scan_title", "Autonomous App Scan")}</span>
                    </h5>
                    <small class="text-muted" data-i18n="ai_platform_scan_hint">${t("ai_platform_scan_hint", "Refreshes what the AI knows about the app (screens, code structure) so new features are picked up.")}</small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary d-flex align-items-center gap-1" onclick="window.AIA.runAutonomousAppScan(this)">
                    <i class="bi bi-radar"></i> <span data-i18n="ai_platform_trigger_scan">${t("ai_platform_trigger_scan", "Trigger Autonomous Scan")}</span>
                </button>
            </div>
        </div>`;
};
