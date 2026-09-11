"use strict";

function _showSliderTooltip(slider, text) {
  let tooltip = document.getElementById("whatif-slider-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "whatif-slider-tooltip";
    tooltip.className = "whatif-tooltip d-none";
    document.body.appendChild(tooltip);
  }

  tooltip.innerHTML = text;
  tooltip.classList.remove("d-none");

  const rect = slider.getBoundingClientRect();
  const min = Number(slider.min) || 0;
  const max = Number(slider.max) || 100;
  const val = Number(slider.value) || 0;
  const percent = max > min ? (val - min) / (max - min) : 0;

  const thumbWidth = 16;
  const trackWidth = Math.max(0, rect.width - thumbWidth);
  const thumbOffset = percent * trackWidth + thumbWidth / 2;

  const tooltipX = rect.left + window.scrollX + thumbOffset;
  const tooltipY = rect.top + window.scrollY - 8;

  tooltip.style.left = `${tooltipX}px`;
  tooltip.style.top = `${tooltipY}px`;
}

function _hideSliderTooltip() {
  const tooltip = document.getElementById("whatif-slider-tooltip");
  if (tooltip) {
    tooltip.classList.add("d-none");
  }
}

function _money(value) {
  const num = Number(value) || 0;
  if (typeof fmtpresent === "function") {
    return fmtpresent(num);
  }
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function _fmtDelta(val, isPct = false, digits = 1) {
  if (val === null || val === undefined) return "-";
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : "";
  if (isPct) return `${sign}${num.toFixed(digits)}%`;
  if (typeof fmtpresent === "function") {
    return `${sign}${fmtpresent(num)}`;
  }
  return `${sign}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
