"use strict";
// AI Advisor settings: Platform overview panel + scan/promote actions.

window.AIA = window.AIA || {};

window.AIA.loadAIPlatformOverviewData = async function() {
  try {
    const [dsRes, mRes] = await Promise.all([
      fetch("/api/ai-platform/datasets/"),
      fetch("/api/ai-platform/models/"),
    ]);

    if (dsRes.ok) {
      const dsData = await dsRes.json();
      const stats = dsData.dataset_stats || {};
      const container = document.getElementById("aiPlatformDatasetHealth");
      if (container) {
        container.innerHTML = `
                    <div class="small">
                        <div><strong data-i18n="ai_platform_total_sft_samples">${t("ai_platform_total_sft_samples", "Total SFT Samples:")}</strong> ${stats.total_samples || 0}</div>
                        <div><strong data-i18n="ai_platform_duplicates_removed">${t("ai_platform_duplicates_removed", "Duplicates Removed:")}</strong> ${stats.duplicates_removed || 0}</div>
                        <div><strong data-i18n="ai_platform_validation_status">${t("ai_platform_validation_status", "Validation Status:")}</strong> <span class="badge bg-success">${stats.validation_status || "Clean"}</span></div>
                    </div>
                `;
      }
    }

    if (mRes.ok) {
      const mData = await mRes.json();
      const versions = mData.model_versions || [];
      const tbody = document.getElementById("aiPlatformModelList");
      if (tbody) {
        if (versions.length === 0) {
          tbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center py-2" data-i18n="ai_platform_no_models">${t("ai_platform_no_models", "No custom model versions found.")}</td></tr>`;
        } else {
          let html = "";
          versions.forEach((v) => {
            const activeBadge = v.is_active
              ? `<span class="badge bg-primary" data-i18n="ai_platform_active_production">${t("ai_platform_active_production", "Active Production")}</span>`
              : `<span class="badge bg-secondary" data-i18n="ai_platform_archived">${t("ai_platform_archived", "Archived")}</span>`;
            const actionBtn = v.is_active
              ? `<button class="btn btn-sm btn-outline-secondary" disabled data-i18n="ai_platform_btn_active">${t("ai_platform_btn_active", "Active")}</button>`
              : `<button class="btn btn-sm btn-outline-success" onclick="window.AIA.promoteModelVersion('${v.version_name}')" data-i18n="ai_platform_btn_promote">${t("ai_platform_btn_promote", "Promote")}</button>`;
            html += `
                            <tr>
                                <td class="fw-bold">${v.version_name}</td>
                                <td>${v.base_model}</td>
                                <td>${v.training_backend}</td>
                                <td>${v.dataset_version}</td>
                                <td><span class="badge bg-info text-dark">${v.benchmark_score} / 100</span></td>
                                <td>${activeBadge}</td>
                                <td>${actionBtn}</td>
                            </tr>
                        `;
          });
          tbody.innerHTML = html;
        }
      }
    }

    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  } catch (err) {
    // Silently ignore AI Platform overview load failures.
  }
}

window.AIA.runAutonomousAppScan = async function(btn) {
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/ai-platform/knowledge/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "scan" }),
    });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function")
        showToast(`Autonomous scan complete ✓ (${data.updated_entries_count} entries updated)`);
      window.AIA.loadAIPlatformOverviewData();
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Autonomous scan failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.AIA.refreshDatasetStats = async function(btn) {
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/ai-platform/datasets/", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function") showToast("Dataset re-generated & validated ✓");
      window.AIA.loadAIPlatformOverviewData();
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Dataset validation failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.AIA.triggerModelFineTuning = async function(btn) {
  const backend = document.getElementById("aiTrainingBackendSelect")?.value || "ollama";
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/ai-platform/models/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "fine_tune", backend_name: backend }),
    });
    const data = await res.json();
    if (data.ok) {
      const promotedText = data.promoted_to_active
        ? "Candidate promoted to Production ✓"
        : "Benchmark score did not exceed production ⚠️";
      if (typeof showToast === "function") showToast(`Fine-tuning finished. ${promotedText}`);
      window.AIA.loadAIPlatformOverviewData();
    } else {
      if (typeof showToast === "function") showToast(data.error || "Fine-tuning failed", "error");
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Fine-tuning request failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.AIA.promoteModelVersion = async function(versionName) {
  try {
    const res = await fetch("/api/ai-platform/models/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "promote", version_name: versionName }),
    });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function")
        showToast(`Promoted ${versionName} to active production ✓`);
      window.AIA.loadAIPlatformOverviewData();
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Promotion failed", "error");
  }
}

window.renderAIAdvisorSettings = window.AIA.renderAIAdvisorSettings;
