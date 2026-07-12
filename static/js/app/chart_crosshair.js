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
      if (d < minDist) { minDist = d; nearest = i; }
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
    if (getComputedStyle(wrapper).position === 'static') {
      wrapper.style.position = 'relative';
    }

    const card = document.createElement('div');
    card.style.cssText = [
      'position:absolute',
      'pointer-events:none',
      'z-index:10',
      'background:rgba(10,20,46,0.94)',
      'border:1px solid rgba(123,147,201,0.28)',
      'border-radius:10px',
      'padding:10px 14px',
      'min-width:130px',
      'max-width:220px',
      'backdrop-filter:blur(4px)',
      'transition:opacity 0.12s',
      'opacity:0',
      'display:none',
    ].join(';');
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

    const labels  = chart.data.labels || [];
    const label   = labels[index] !== undefined ? labels[index] : '';

    // Build value rows for each visible dataset
    const rows = chart.data.datasets.map((ds, di) => {
      // skip hidden datasets
      const meta = chart.getDatasetMeta(di);
      if (meta.hidden) return '';
      const raw = ds.data[index];
      if (raw === null || raw === undefined) return '';

      // Use the dataset's configured tooltip label callback when available,
      // otherwise fall back to the chart's format helper or raw value.
      let formatted;
      try {
        const tooltipCb = chart.options?.plugins?.tooltip?.callbacks?.label;
        if (typeof tooltipCb === 'function') {
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
      } catch (_) { /* fallback below */ }

      if (!formatted) {
        // Generic fallback: use window.fmt if available
        formatted = (ds.label ? ds.label + ': ' : '') +
          (typeof window.fmt === 'function' ? window.fmt(raw) : raw);
      }

      const color = ds.borderColor || '#7b93c9';
      return `<div style="display:flex;align-items:center;gap:6px;margin-top:3px;">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;flex-shrink:0;background:${color};"></span>
        <span style="color:#b8caf0;font-size:12px;white-space:nowrap;">${formatted}</span>
      </div>`;
    }).join('');

    if (!rows.trim()) {
      card.style.opacity = '0';
      card.style.display = 'none';
      return;
    }

    card.innerHTML = `
      <div style="color:#7b93c9;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">${label}</div>
      ${rows}
    `;
    card.style.display = 'block';

    // ── Position card (flip near edges) ────────────────────────────────────
    const wrapper = chart.canvas.parentElement;
    const wrapW   = wrapper.clientWidth;
    const cardW   = card.offsetWidth || 160;
    const MARGIN  = 12;
    const topY    = chart.scales.y ? chart.scales.y.top : 8;

    let leftPx = canvasX + MARGIN;
    if (leftPx + cardW > wrapW - 4) {
      leftPx = canvasX - cardW - MARGIN;
    }
    leftPx = Math.max(4, leftPx);

    card.style.left = leftPx + 'px';
    card.style.top  = topY + 'px';
    card.style.opacity = '1';
  }

  // ── Plugin ─────────────────────────────────────────────────────────────────

  const SharedCrosshairPlugin = {
    id: 'sharedCrosshair',

    // ── afterInit: attach pointer/touch listeners ─────────────────────────
    afterInit(chart) {
      if (!chart || !chart.config) return;
      if (chart.config.type !== 'line') return;

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
        const rect  = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const rawX  = (e.clientX - rect.left) * scaleX;

        // Clamp to the plot area
        const plotLeft  = chart.chartArea?.left  ?? 0;
        const plotRight = chart.chartArea?.right  ?? canvas.width;
        if (rawX < plotLeft || rawX > plotRight) {
          _hideOverlay(chart);
          return;
        }

        const idx = _nearestIndex(chart, rawX);
        chart._crosshairIndex = idx;
        chart.update('none'); // redraw without animation so afterDraw fires

        // Position card using the snapped X of the nearest data point
        const snappedX = _xForIndex(chart, idx);
        const dispX    = (snappedX !== null ? snappedX : rawX) / scaleX;
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

      canvas.addEventListener('pointermove', onPointerMove);
      canvas.addEventListener('pointerleave', onPointerLeave);
      canvas.addEventListener('touchmove',    onTouchMove,  { passive: false });
      canvas.addEventListener('touchend',     onTouchEnd);

      // Stash handlers so we can remove them on destroy
      chart._crosshairHandlers = {
        onPointerMove, onPointerLeave, onTouchMove, onTouchEnd,
      };
    },

    // ── afterDraw: draw the vertical line + dots ───────────────────────────
    afterDraw(chart) {
      if (!chart || !chart.config) return;
      if (chart.config.type !== 'line') return;
      const idx = chart._crosshairIndex;
      if (idx < 0) return;

      const snappedX = _xForIndex(chart, idx);
      if (snappedX === null) return;

      const ctx    = chart.ctx;
      const topY   = chart.scales.y?.top    ?? chart.chartArea?.top    ?? 0;
      const bottomY= chart.scales.y?.bottom ?? chart.chartArea?.bottom ?? chart.height;

      ctx.save();

      // Vertical hairline
      ctx.beginPath();
      ctx.moveTo(snappedX, topY);
      ctx.lineTo(snappedX, bottomY);
      ctx.lineWidth   = 1;
      ctx.strokeStyle = 'rgba(123,147,201,0.55)';
      ctx.setLineDash([]);
      ctx.stroke();

      // Dots – one per visible dataset
      chart.data.datasets.forEach((ds, di) => {
        const meta = chart.getDatasetMeta(di);
        if (meta.hidden) return;
        const pt = meta.data[idx];
        if (!pt) return;

        const color = ds.borderColor || '#7b93c9';
        // Use the first dataset's color for the outer ring stroke
        const outerColor = color;
        const innerColor = ds.backgroundColor || 'rgba(10,20,46,0.9)';

        // Outer filled ring
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 7, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(10,20,46,0.85)';
        ctx.fill();
        ctx.lineWidth   = 2.5;
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
        canvas.removeEventListener('pointermove',  h.onPointerMove);
        canvas.removeEventListener('pointerleave', h.onPointerLeave);
        canvas.removeEventListener('touchmove',    h.onTouchMove);
        canvas.removeEventListener('touchend',     h.onTouchEnd);
      }
      _removeCard(chart);
      chart._crosshairHandlers = null;
      chart._crosshairIndex    = -1;
    },
  };

  // ── shared hide helper ───────────────────────────────────────────────────
  function _hideOverlay(chart) {
    chart._crosshairIndex = -1;
    chart.update('none');
    if (chart._crosshairCard) {
      chart._crosshairCard.style.opacity = '0';
      chart._crosshairCard.style.display = 'none';
    }
  }

  // Expose globally so each chart file can reference it as
  //   plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : []
  if (typeof window !== 'undefined') {
    window.SharedCrosshairPlugin = SharedCrosshairPlugin;
  }

}());
