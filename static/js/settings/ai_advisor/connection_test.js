"use strict";
// AI Advisor settings: "Test Connection" button handler.

window.AIA = window.AIA || {};

window.AIA.testAIConnectionFromGui = async function() {
  const btn = document.getElementById("aiTestConnBtn");
  const resultDiv = document.getElementById("aiTestDiagnosticResult");
  if (!resultDiv) return;

  const provider = document.getElementById("aiProviderSelect")?.value || "ollama";
  const model = (document.getElementById("aiModelInput")?.value || "").trim();
  const timeout = (document.getElementById("aiTimeoutInput")?.value || "").trim();

  const payload = {
    provider: provider,
    model: model,
    timeout: parseInt(timeout, 10) || 60,
  };

  // Include provider specific fields
  const schema = window.AIA.state.currentProviderSchemas.find((s) => s.key === provider);
  if (schema && Array.isArray(schema.fields)) {
    schema.fields.forEach((f) => {
      const el = document.getElementById(f.name);
      if (el) payload[f.name] = el.value.trim();
    });
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> ${t("ai_testing", "Testing...")}`;
  }

  resultDiv.style.display = "block";
  resultDiv.innerHTML = `
        <div class="alert alert-info d-flex align-items-center mb-0">
            <span class="spinner-border spinner-border-sm me-2"></span>
            <span>${t("ai_testing_connection_desc", "Connecting to AI provider and inspecting model availability...")}</span>
        </div>`;

  try {
    const res = await fetch("/api/settings/ai/test-connection/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    window.AIA.renderAIDiagnosticResult(data);
  } catch (err) {
    resultDiv.innerHTML = `
            <div class="alert alert-danger d-flex align-items-center mb-0">
                <i class="bi bi-x-circle-fill me-2 fs-5"></i>
                <div>
                    <strong>${t("ai_test_failed", "Test Connection Failed")}</strong><br>
                    ${escapeHtml(err.message || "Network error")}
                </div>
            </div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-activity me-1"></i> <span>${t("ai_test_connection", "Test Connection")}</span>`;
    }
  }
}

