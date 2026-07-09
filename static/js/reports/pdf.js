'use strict';

async function generatePDF(type) {
  let year = parseInt(
    document.getElementById("rYear")?.value ||
      document.getElementById("rYearOnly")?.value ||
      new Date().getFullYear(),
  );
  let month = parseInt(
    document.getElementById("rMonth")?.value || new Date().getMonth() + 1,
  );
  const start = document.getElementById("rStart")?.value || "";
  const end = document.getElementById("rEnd")?.value || "";

  if (type === "custom") {
    if (start) {
      year = new Date(start).getFullYear();
    }
    month = 1;
  }

  const body = {
    type,
    year,
    month,
    start_date: start,
    end_date: end,
    lang: currentLang(),
  };

  const btn = event?.target;
  const generatingText = t('generating', 'Generating…');
  const generatePdfText = t('generate_pdf', 'Generate PDF');
  
  if (btn) {
    btn.disabled = true;
    btn.innerHTML =
      `<div class="spinner-border spinner-border-sm"></div> ${generatingText}`;
  }

  try {
    const res = await fetch("/api/reports/generate/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(t('error_prefix', 'Error: ') + (err.error || t('unknown_error', 'Unknown error')), "error");
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const cd = res.headers.get("Content-Disposition") || "";
    const fnMatch = cd.match(/filename="(.+)"/);
    a.download = fnMatch ? fnMatch[1] : "report.pdf";
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
    showToast(t('pdf_downloaded', 'PDF downloaded ✓'), "success");
  } catch (e) {
    showToast(t('network_error_prefix', 'Network error: ') + e.message, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-file-earmark-pdf"></i> ${generatePdfText}`;
    }
  }
  applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════