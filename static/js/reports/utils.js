'use strict';

function yearOpts(current) {
  let o = "";
  for (let y = current > 2026 ? current : 2026; y >= 2020; y--)
    o += `<option value="${y}" ${y === current ? "selected" : ""}>${y}</option>`;
  return o;
}

function monthOpts(selectedMonth) {
  return MONTHS_NAMES.map((m, i) => {
    const monthValue = i + 1;
    const isSelected = monthValue === selectedMonth ? "selected" : "";
    const i18nKey = MONTH_I18N_KEYS[i];

    return `<option value="${monthValue}" ${isSelected} data-i18n="${i18nKey}">${m}</option>`;
  }).join("");
}