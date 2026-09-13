"use strict";
// Property valuation: rate scraping
// This file is part of the settings module. Do not edit directly.

async function scrapePropertyRates(baselineOnly = false) {
  const btn = document.getElementById("btnScrapeAqarmap");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>${t("scraping_property_rates", "Scraping…")}`;
  }

  try {
    const res = await fetch("/api/settings/scrape-property-rates/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ baseline_only: baselineOnly, timeout: 30 }),
    });

    const data = await res.json();

    const badge = document.getElementById("scrapeStatusBadge");
    if (res.ok && data.ok) {
      const textarea = document.getElementById("propertyValuationRateMap");
      if (textarea) textarea.value = data.rate_map_json;

      const liveSuccess = data.source === "aqarmap_live+baseline";
      if (badge) {
        if (liveSuccess) {
          badge.innerHTML = `<span style="color:var(--accent-green)"><i class="bi bi-check-circle-fill"></i> Aqarmap live &mdash; ${data.districts} districts</span>`;
        } else {
          badge.innerHTML = `<span style="color:var(--accent-yellow,#f5a623)"><i class="bi bi-exclamation-triangle-fill"></i> Scrape failed &mdash; baseline used (${data.districts} districts)</span>`;
        }
      }
      showToast(
        liveSuccess
          ? `Rates fetched from Aqarmap - ${data.districts} districts`
          : `Aqarmap unreachable - loaded ${data.districts} baseline districts`,
        liveSuccess ? "success" : "warning"
      );
    } else {
      const badge = document.getElementById("scrapeStatusBadge");
      if (badge)
        badge.innerHTML = `<span style="color:var(--accent-red)"><i class="bi bi-x-circle-fill"></i> ${t("error_scraping_property_rates", "Failed to fetch rates")}</span>`;
      showToast(t("error_scraping_property_rates", "Failed to fetch rates"), "error");
    }
  } catch {
    const badge = document.getElementById("scrapeStatusBadge");
    if (badge)
      badge.innerHTML = `<span style="color:var(--accent-red)"><i class="bi bi-x-circle-fill"></i> ${t("error_scraping_property_rates", "Failed to fetch rates")}</span>`;
    showToast(t("error_scraping_property_rates", "Failed to fetch rates"), "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-cloud-download"></i> ${t("scrape_property_rates", "Scrape from Aqarmap")}`;
    }
  }
}
