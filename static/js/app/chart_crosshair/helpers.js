"use strict";

// ─────────────────────────────────────────────────────────────────────────────
// SharedCrosshairPlugin
// Standing pattern: any new line/area chart added to this app should use this
// plugin rather than reimplementing the scrubber interaction.
//
// Behaviour:
//   • A vertical hairline tracks the pointer/touch across the full chart area.
//   • A filled dot appears on each dataset line at the intersecting index.
//   • A floating card (HTML overlay) shows the x-axis label + formatted values.
//     The card flips to the opposite side when it is near the right/left edge.
//   • All state is stored on the chart instance so multiple charts on one page
//     work independently without interfering with each other.
//   • Chart.register() is never called here – the plugin object is passed
//     directly into the `plugins` array of each Chart config so it cannot fire
//     before Chart.js has loaded.
//   • The mouse/touch listeners are cleaned up in `destroy` so that a stale
//     instance never keeps drawing after chart.destroy() is called.
// ─────────────────────────────────────────────────────────────────────────────

(function () {
  // ── helpers ────────────────────────────────────────────────────────────────

  /** Nearest data index for a given canvas-relative X pixel. */
  function _nearestIndex(chart, canvasX) {
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data || !meta.data.length) return -1;

    let nearest = 0;
    let minDist = Infinity;
    meta.data.forEach((pt, i) => {
      const d = Math.abs(pt.x - canvasX);
      if (d < minDist) {
        minDist = d;
        nearest = i;
      }
    });
    return nearest;
  }

  /** Canvas-relative X for a data index (uses first dataset's meta). */
  function _xForIndex(chart, index) {
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data || !meta.data[index]) return null;
    return meta.data[index].x;
  }

  /** Build or reuse the shared overlay card for this chart canvas. */
  function _ensureCard(chart) {
    if (chart._crosshairCard) return chart._crosshairCard;

    const wrapper = chart.canvas.parentElement;
    if (!wrapper) return null;
    // wrapper must be position:relative so the card positions correctly
    if (getComputedStyle(wrapper).position === "static") {
      wrapper.style.position = "relative";
    }

    const card = document.createElement("div");
    card.style.cssText = [
      "position:absolute",
      "pointer-events:none",
      "z-index:10",
      "background:var(--bg-secondary)",
      "border:1px solid var(--border-color)",
      "border-radius:var(--radius-md, 12px)",
      "padding:10px 14px",
      "min-width:130px",
      "max-width:220px",
      "box-shadow:var(--shadow-lg)",
      "backdrop-filter:blur(12px)",
      "-webkit-backdrop-filter:blur(12px)",
      "transition:opacity 0.12s",
      "opacity:0",
      "display:none",
    ].join(";");
    wrapper.appendChild(card);

    chart._crosshairCard = card;
    return card;
  }

  /** Remove and nullify the overlay card. */
  function _removeCard(chart) {
    if (chart._crosshairCard) {
      chart._crosshairCard.remove();
      chart._crosshairCard = null;
    }
  }

  /** Update card content and position. */
  function _updateCard(chart, index, canvasX) {
    const card = _ensureCard(chart);
    if (!card) return;

    const labels = chart.data.labels || [];
    const label = labels[index] !== undefined ? labels[index] : "";

    // Build value rows for each visible dataset
    const rows = chart.data.datasets
      .map((ds, di) => {
        // skip hidden datasets
        const meta = chart.getDatasetMeta(di);
        if (meta.hidden) return "";
        const raw = ds.data[index];
        if (raw === null || raw === undefined) return "";

        // Use the dataset's configured tooltip label callback when available,
        // otherwise fall back to the chart's format helper or raw value.
        let formatted;
        try {
          const tooltipCb = chart.options?.plugins?.tooltip?.callbacks?.label;
          if (typeof tooltipCb === "function") {
            // Build a minimal ctx object that matches what Chart.js would pass
            const ptMeta = meta.data[index];
            const fakeCtx = {
              chart,
              dataset: ds,
              datasetIndex: di,
              dataIndex: index,
              raw,
              parsed: { x: index, y: raw },
              label,
              formattedValue: String(raw),
              element: ptMeta,
            };
            formatted = tooltipCb(fakeCtx);
          }
        } catch (_) {
          /* fallback below */
        }

        if (!formatted) {
          // Generic fallback: use window.fmt if available
          formatted =
            (ds.label ? ds.label + ": " : "") +
            (typeof window.fmt === "function" ? window.fmt(raw) : raw);
        }

        const color = ds.borderColor || "var(--accent-primary)";
        return `<div style="display:flex;align-items:center;gap:6px;margin-top:3px;">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;flex-shrink:0;background:${color};"></span>
        <span style="color:var(--text-primary);font-size:12px;font-weight:600;white-space:nowrap;">${formatted}</span>
      </div>`;
      })
      .join("");

    if (!rows.trim()) {
      card.style.opacity = "0";
      card.style.display = "none";
      return;
    }

    card.innerHTML = `
      <div style="color:var(--text-muted);font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">${typeof formatDate === "function" ? formatDate(label) : label}</div>
      ${rows}
    `;
    card.style.display = "block";

    // ── Position card (flip near edges) ────────────────────────────────────
    const wrapper = chart.canvas.parentElement;
    const wrapW = wrapper.clientWidth;
    const cardW = card.offsetWidth || 160;
    const MARGIN = 12;
    const topY = chart.scales.y ? chart.scales.y.top : 8;

    let leftPx = canvasX + MARGIN;
    if (leftPx + cardW > wrapW - 4) {
      leftPx = canvasX - cardW - MARGIN;
    }
    leftPx = Math.max(4, leftPx);

    card.style.left = leftPx + "px";
    card.style.top = topY + "px";
    card.style.opacity = "1";
  }

  function _hideOverlay(chart) {
    chart._crosshairIndex = -1;
    chart.update("none");
    if (chart._crosshairCard) {
      chart._crosshairCard.style.opacity = "0";
      chart._crosshairCard.style.display = "none";
    }
  }

  // Expose helpers for plugin.js to consume via window._ChartCrosshairHelpers
  window._ChartCrosshairHelpers = {
    _nearestIndex,
    _xForIndex,
    _ensureCard,
    _removeCard,
    _updateCard,
    _hideOverlay,
  };
})();
