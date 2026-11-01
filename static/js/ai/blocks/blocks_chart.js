"use strict";

/**
 * AI Workspace — charts under an answer. Plain inline SVG (no library); the numbers are the server's, never the model's.
 */

const AIChart = (() => {
  const esc = (t) => (typeof _escapeHtml === "function" ? _escapeHtml(t) : String(t));
  const COLORS = ["#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#dc3545", "#20c997"];
  const W = 520;
  const H = 220;
  const PAD = { l: 52, r: 12, t: 12, b: 40 };

  function fmt(n) {
    const a = Math.abs(n);
    if (a >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (a >= 1e3) return (n / 1e3).toFixed(1) + "k";
    return String(Math.round(n * 100) / 100);
  }

  function pie(p) {
    const vals = p.series[0].values.map((v) => Math.max(0, v));
    const total = vals.reduce((a, b) => a + b, 0) || 1;
    let angle = -Math.PI / 2;
    const cx = 110;
    const cy = 110;
    const r = 95;
    const slices = vals
      .map((v, i) => {
        const a2 = angle + (v / total) * 2 * Math.PI;
        const large = a2 - angle > Math.PI ? 1 : 0;
        const d = `M${cx},${cy} L${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)} A${r},${r} 0 ${large} 1 ${cx + r * Math.cos(a2)},${cy + r * Math.sin(a2)} Z`;
        angle = a2;
        return v > 0
          ? `<path d="${d}" fill="${COLORS[i % COLORS.length]}"><title>${esc(p.labels[i])}: ${fmt(v)}</title></path>`
          : "";
      })
      .join("");
    const legend = p.labels
      .map(
        (l, i) =>
          `<div class="ai-chart-key"><i style="background:${COLORS[i % COLORS.length]}"></i>${esc(l)} <b>${fmt(vals[i])}</b> (${Math.round((vals[i] / total) * 100)}%)</div>`
      )
      .join("");
    return `<div class="ai-chart-pie"><svg viewBox="0 0 220 220" width="180" role="img" aria-label="${esc(p.title)}">${slices}</svg><div>${legend}</div></div>`;
  }

  function axes(p, body, max, min) {
    const ticks = [0, 0.5, 1]
      .map((f) => {
        const v = min + (max - min) * f;
        const y = H - PAD.b - (H - PAD.t - PAD.b) * f;
        return `<line x1="${PAD.l}" x2="${W - PAD.r}" y1="${y}" y2="${y}" stroke="currentColor" opacity=".15"/><text x="${PAD.l - 6}" y="${y + 4}" text-anchor="end" font-size="10" fill="currentColor">${fmt(v)}</text>`;
      })
      .join("");
    const step = Math.ceil(p.labels.length / 8);
    const xl = p.labels
      .map((l, i) =>
        i % step
          ? ""
          : `<text x="${PAD.l + ((W - PAD.l - PAD.r) * (i + 0.5)) / p.labels.length}" y="${H - PAD.b + 14}" text-anchor="middle" font-size="10" fill="currentColor">${esc(l)}</text>`
      )
      .join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(p.title)}">${ticks}${xl}${body}</svg>`;
  }

  function cartesian(p) {
    const all = p.series.flatMap((s) => s.values);
    const max = Math.max(0, ...all);
    const min = Math.min(0, ...all);
    const span = max - min || 1;
    const n = p.labels.length;
    const slot = (W - PAD.l - PAD.r) / n;
    const y = (v) => H - PAD.b - ((v - min) / span) * (H - PAD.t - PAD.b);
    let body = "";
    if (p.type === "bar") {
      const bw = (slot * 0.8) / p.series.length;
      p.series.forEach((s, si) =>
        s.values.forEach((v, i) => {
          const x = PAD.l + slot * i + slot * 0.1 + bw * si;
          body += `<rect x="${x}" y="${Math.min(y(v), y(0))}" width="${bw}" height="${Math.abs(y(v) - y(0))}" fill="${COLORS[si % COLORS.length]}"><title>${esc(p.labels[i])}: ${fmt(v)}</title></rect>`;
        })
      );
    } else {
      p.series.forEach((s, si) => {
        const pts = s.values.map((v, i) => `${PAD.l + slot * (i + 0.5)},${y(v)}`).join(" ");
        body += `<polyline points="${pts}" fill="none" stroke="${COLORS[si % COLORS.length]}" stroke-width="2"/>`;
        s.values.forEach((v, i) => {
          body += `<circle cx="${PAD.l + slot * (i + 0.5)}" cy="${y(v)}" r="3" fill="${COLORS[si % COLORS.length]}"><title>${esc(p.labels[i])}: ${fmt(v)}</title></circle>`;
        });
      });
    }
    const legend =
      p.series.length > 1
        ? `<div class="ai-chart-legend">${p.series.map((s, i) => `<span class="ai-chart-key"><i style="background:${COLORS[i % COLORS.length]}"></i>${esc(s.name)}</span>`).join("")}</div>`
        : "";
    return axes(p, body, max, min) + legend;
  }

  function draw(block) {
    const p = block.payload || {};
    if (!p.labels || !p.series || !p.series.length) return "";
    const inner = p.type === "pie" ? pie(p) : cartesian(p);
    const unit = p.unit ? ` <span class="text-muted">(${esc(p.unit)})</span>` : "";
    return `<div class="ai-chart-card"><div class="ai-chart-title">${esc(p.title || "")}${unit}</div>${inner}</div>`;
  }

  return { draw };
})();

window.AIChart = AIChart;
