"use strict";
// AI Advisor settings: runtime capability inspection (hardware detection +
// Ollama /api/show + /api/ps + a live timing benchmark) -> a recommended
// ai_context_size/ai_max_tokens/ai_timeout/ai_keep_alive. Preview only —
// "Apply" fills the form fields; nothing is saved until Save Settings runs.

window.AIA = window.AIA || {};

window.AIA.detectRuntimeCapabilities = async function (btn) {
  const resultEl = document.getElementById("aiRuntimeCapabilitiesResult");
  if (btn) btn.disabled = true;
  if (resultEl) {
    resultEl.style.display = "block";
    resultEl.innerHTML = `<small class="text-muted" data-i18n="ai_detecting_capabilities">${t(
      "ai_detecting_capabilities",
      "Detecting hardware and querying Ollama — runs one small real generation to measure actual speed, may take a few seconds..."
    )}</small>`;
  }
  try {
    const res = await fetch("/api/settings/ai/runtime-capabilities/");
    const data = await res.json();
    if (!res.ok) {
      if (resultEl)
        resultEl.innerHTML = `<small class="text-danger">${escapeHtml(data.error || "Detection failed")}</small>`;
      return;
    }
    window.AIA._lastRuntimeCapabilities = data;
    if (resultEl) resultEl.innerHTML = window.AIA._renderRuntimeCapabilitiesResult(data);
    if (typeof applyTranslations === "function") applyTranslations();
  } catch (err) {
    if (resultEl)
      resultEl.innerHTML = `<small class="text-danger" data-i18n="ai_detect_capabilities_failed">${t(
        "ai_detect_capabilities_failed",
        "Could not reach the detection endpoint."
      )}</small>`;
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.AIA._renderRuntimeCapabilitiesResult = function (data) {
  const hw = data.hardware || {};
  const rec = data.recommended || {};
  const notes = data.notes || [];
  const hwLine = `CPU: ${hw.cpu_count ?? "?"} cores, RAM: ${hw.total_ram_gb ?? "?"} GB, GPU VRAM: ${
    hw.gpu_vram_gb ?? "n/a"
  }, ${hw.platform ?? ""}`;
  const notesHtml = notes.map((n) => `<li class="small text-muted">${escapeHtml(n)}</li>`).join("");
  return `
        <div class="p-3 rounded" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
            <div class="small mb-2"><strong data-i18n="ai_detected_hardware">${t("ai_detected_hardware", "Detected hardware:")}</strong> ${escapeHtml(hwLine)}</div>
            <div class="small mb-2">
                <strong data-i18n="ai_recommended_config">${t("ai_recommended_config", "Recommended:")}</strong>
                Context Size = ${rec.ai_context_size}, Max Tokens = ${rec.ai_max_tokens}, Timeout = ${rec.ai_timeout}s, Keep Alive = ${escapeHtml(rec.ai_keep_alive ?? "")}
            </div>
            <ul class="mb-2">${notesHtml}</ul>
            <button type="button" class="btn btn-sm btn-outline-success" onclick="window.AIA.applyRuntimeCapabilityRecommendation()">
                <i class="bi bi-check2-circle me-1"></i> <span data-i18n="ai_apply_recommendation">${t("ai_apply_recommendation", "Apply to form (not saved yet)")}</span>
            </button>
        </div>`;
};

window.AIA.applyRuntimeCapabilityRecommendation = function () {
  const data = window.AIA._lastRuntimeCapabilities;
  if (!data || !data.recommended) return;
  const rec = data.recommended;
  const ctxEl = document.getElementById("aiContextSizeInput");
  const maxEl = document.getElementById("aiMaxTokensInput");
  const toEl = document.getElementById("aiTimeoutInput");
  const kaEl = document.getElementById("aiKeepAliveInput");
  if (ctxEl && rec.ai_context_size != null) ctxEl.value = rec.ai_context_size;
  if (maxEl && rec.ai_max_tokens != null) maxEl.value = rec.ai_max_tokens;
  if (toEl && rec.ai_timeout != null) toEl.value = rec.ai_timeout;
  if (kaEl && rec.ai_keep_alive != null) kaEl.value = rec.ai_keep_alive;
  if (typeof showToast === "function")
    showToast("Recommended values applied — click Save Settings to persist.");
};
