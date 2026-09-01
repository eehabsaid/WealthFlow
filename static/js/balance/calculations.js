"use strict";

function renderAllocationBar(labelKey, value, total) {
  const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;

  // Normalize key to lowercase for insensitive lookup
  const lookupKey = labelKey.toLowerCase();
  let finalKey = labelKey;
  let translatedText = t(labelKey, labelKey); // Default fallback

  // Find the actual case-sensitive key used inside the JSON translation dictionary
  if (_t) {
    const matchedKey = Object.keys(_t).find((k) => k.toLowerCase() === lookupKey);
    if (matchedKey) {
      finalKey = matchedKey;
      translatedText = _t[matchedKey];
    }
  }

  return `
        <div style="margin-top:14px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;">
                <span data-i18n="${finalKey}">${translatedText}</span>
                <span>${pct}%</span>
            </div>
            <div style="height:12px;background:var(--bg-tertiary);border-radius:999px;overflow:hidden;">
                <div style="width:${pct}%;height:100%;background:var(--accent-primary);"></div>
            </div>
        </div>
    `;
}
