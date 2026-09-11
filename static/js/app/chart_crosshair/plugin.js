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
  const {
    _nearestIndex,
    _xForIndex,
    _ensureCard,
    _removeCard,
    _updateCard,
    _hideOverlay,
  } = window._ChartCrosshairHelpers;

  // ── Plugin ─────────────────────────────────────────────────────────────────

  const SharedCrosshairPlugin = {
    id: "sharedCrosshair",

    // ── afterInit: attach pointer/touch listeners ─────────────────────────
    afterInit(chart) {
      if (!chart || !chart.config) return;
      if (chart.config.type !== "line") return;

      // Disable Chart.js native tooltip – we render our own card overlay
      if (chart.options.plugins && chart.options.plugins.tooltip) {
        chart.options.plugins.tooltip.enabled = false;
      }

      const canvas = chart.canvas;

      // Store active scrub index on the chart instance
      chart._crosshairIndex = -1;

      // ── pointer move (covers mouse & stylus) ──────────────────────────
      function onPointerMove(e) {
        if (!chart.ctx) return; // chart already destroyed
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const rawX = (e.clientX - rect.left) * scaleX;

        // Clamp to the plot area
        const plotLeft = chart.chartArea?.left ?? 0;
        const plotRight = chart.chartArea?.right ?? canvas.width;
        if (rawX < plotLeft || rawX > plotRight) {
          _hideOverlay(chart);
          return;
        }

        const idx = _nearestIndex(chart, rawX);
        chart._crosshairIndex = idx;
        chart.update("none"); // redraw without animation so afterDraw fires

        // Position card using the snapped X of the nearest data point
        const snappedX = _xForIndex(chart, idx);
        const dispX = (snappedX !== null ? snappedX : rawX) / scaleX;
        _updateCard(chart, idx, dispX);
      }

      function onPointerLeave() {
        _hideOverlay(chart);
      }

      // ── touch events ──────────────────────────────────────────────────
      function onTouchMove(e) {
        if (e.touches && e.touches.length) {
          e.preventDefault(); // prevent scroll while scrubbing
          onPointerMove(e.touches[0]);
        }
      }

      function onTouchEnd() {
        _hideOverlay(chart);
      }

      canvas.addEventListener("pointermove", onPointerMove);
      canvas.addEventListener("pointerleave", onPointerLeave);
      canvas.addEventListener("touchmove", onTouchMove, { passive: false });
      canvas.addEventListener("touchend", onTouchEnd);

      // Stash handlers so we can remove them on destroy
      chart._crosshairHandlers = {
        onPointerMove,
        onPointerLeave,
        onTouchMove,
        onTouchEnd,
      };
    },

    // ── afterDraw: draw the vertical line + dots ───────────────────────────
    afterDraw(chart) {
      if (!chart || !chart.config) return;
      if (chart.config.type !== "line") return;
      const idx = chart._crosshairIndex;
      if (idx < 0) return;

      const snappedX = _xForIndex(chart, idx);
      if (snappedX === null) return;

      const ctx = chart.ctx;
      const topY = chart.scales.y?.top ?? chart.chartArea?.top ?? 0;
      const bottomY = chart.scales.y?.bottom ?? chart.chartArea?.bottom ?? chart.height;

      ctx.save();

      // Vertical hairline
      ctx.beginPath();
      ctx.moveTo(snappedX, topY);
      ctx.lineTo(snappedX, bottomY);
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(123,147,201,0.55)";
      ctx.setLineDash([]);
      ctx.stroke();

      // Dots – one per visible dataset
      chart.data.datasets.forEach((ds, di) => {
        const meta = chart.getDatasetMeta(di);
        if (meta.hidden) return;
        const pt = meta.data[idx];
        if (!pt) return;

        const color = ds.borderColor || "#7b93c9";
        // Use the first dataset's color for the outer ring stroke
        const outerColor = color;
        const innerColor = ds.backgroundColor || "rgba(10,20,46,0.9)";

        // Outer filled ring
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 7, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(10,20,46,0.85)";
        ctx.fill();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = outerColor;
        ctx.stroke();

        // Inner dot
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = outerColor;
        ctx.fill();
      });

      ctx.restore();
    },

    // ── destroy: remove listeners and overlay card ─────────────────────────
    destroy(chart) {
      const canvas = chart.canvas;
      const h = chart._crosshairHandlers;
      if (h && canvas) {
        canvas.removeEventListener("pointermove", h.onPointerMove);
        canvas.removeEventListener("pointerleave", h.onPointerLeave);
        canvas.removeEventListener("touchmove", h.onTouchMove);
        canvas.removeEventListener("touchend", h.onTouchEnd);
      }
      _removeCard(chart);
      chart._crosshairHandlers = null;
      chart._crosshairIndex = -1;
    },
  };

  // Expose globally so each chart file can reference it as
  //   plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : []
  if (typeof window !== "undefined") {
    window.SharedCrosshairPlugin = SharedCrosshairPlugin;
  }
})();
