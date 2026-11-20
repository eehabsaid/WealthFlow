"use strict";

// Design-system helpers (script-global). Charts and inline styles read the
// semantic CSS tokens instead of hardcoding hex values, so both themes stay
// consistent. Tokens live in static/css/design/tokens.css.

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback || "";
}

function isLightTheme() {
  return document.documentElement.getAttribute("data-theme") === "light";
}

function chartPalette() {
  const out = [];
  for (let i = 1; i <= 8; i++) out.push(cssVar(`--chart-${i}`, "#4f46e5"));
  return out;
}

// Axis/legend/grid colors for Chart.js, following the active theme.
function chartTheme() {
  return {
    text: cssVar("--text-secondary", "#7b93c9"),
    grid: cssVar("--chart-grid", "rgb(30 58 110 / 27%)"),
    border: cssVar("--border-color", "#1e3a6e"),
  };
}

function _hexToRgb(hex) {
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h.replace(/./g, "$&$&");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}

function _luminance(rgb) {
  const [r, g, b] = rgb.map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function _mix(rgb, target, amount) {
  return rgb.map((v, i) => Math.round(v + (target[i] - v) * amount));
}

// User-chosen data colors (e.g. a company color) can be near-black on the dark
// theme or near-white on the light one and then disappear. Keep the hue, but
// nudge lightness until the color is visible against the active background.
function readableChartColor(hex, fallback) {
  const rgb = _hexToRgb(hex);
  if (!rgb) return fallback || chartPalette()[0];
  const light = isLightTheme();
  let out = rgb;
  for (let i = 0; i < 12; i++) {
    const lum = _luminance(out);
    if (!light && lum < 0.12) out = _mix(out, [255, 255, 255], 0.18);
    else if (light && lum > 0.7) out = _mix(out, [0, 0, 0], 0.18);
    else break;
  }
  return `#${out.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}
