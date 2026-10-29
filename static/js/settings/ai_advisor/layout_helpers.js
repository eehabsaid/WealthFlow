"use strict";
// AI Advisor settings: small HTML builders shared by every group (card, row, toggle, select, number field).
// Layout only: ids, data-i18n keys and values are supplied by the callers, so saving never changes.

window.AIA = window.AIA || {};
window.AIA.ui = {};

window.AIA.ui.text = function (key, fallback, cls) {
  return `<span class="${cls}" data-i18n="${key}">${t(key, fallback)}</span>`;
};

// One setting: label + help on the start side, the control on the end side (stacked on narrow screens).
window.AIA.ui.row = function (o) {
  const help = o.helpKey
    ? `<div class="aia-help" data-i18n="${o.helpKey}">${t(o.helpKey, o.help)}</div>`
    : "";
  const title = o.helpKey ? ` title="${escapeHtml(t(o.helpKey, o.help))}"` : "";
  return `
    <div class="aia-row${o.toggle ? " aia-row-toggle" : ""}${o.wide ? " aia-row-wide" : ""}"${title}>
      <div class="aia-row-text">
        <label class="aia-label" for="${o.id}" data-i18n="${o.labelKey}">${t(o.labelKey, o.label)}</label>${help}
      </div>
      <div class="aia-row-control">${o.control}</div>
    </div>`;
};

window.AIA.ui.switchControl = function (id, checked) {
  return `<div class="form-check form-switch aia-switch"><input class="form-check-input" type="checkbox" id="${id}" ${checked ? "checked" : ""}></div>`;
};

window.AIA.ui.selectControl = function (id, optionsHtml) {
  return `<select class="form-select" id="${id}">${optionsHtml}</select>`;
};

window.AIA.ui.toggleRow = function (o) {
  return window.AIA.ui.row({
    ...o,
    toggle: true,
    control: window.AIA.ui.switchControl(o.id, o.checked),
  });
};

window.AIA.ui.selectRow = function (o) {
  return window.AIA.ui.row({ ...o, control: window.AIA.ui.selectControl(o.id, o.options) });
};

// A number input with its label above and its help below, laid out in a grid with its siblings.
window.AIA.ui.numberField = function (o) {
  const help = o.helpKey
    ? `<div class="aia-help" data-i18n="${o.helpKey}">${t(o.helpKey, o.help)}</div>`
    : "";
  const attrs = [
    o.min !== undefined ? `min="${o.min}"` : "",
    o.max !== undefined ? `max="${o.max}"` : "",
    o.step !== undefined ? `step="${o.step}"` : "",
  ].join(" ");
  return `
    <div class="aia-field">
      <label class="aia-label" for="${o.id}" data-i18n="${o.labelKey}">${t(o.labelKey, o.label)}</label>
      <input type="number" class="form-control" id="${o.id}" ${attrs} value="${o.value}">${help}
    </div>`;
};

window.AIA.ui.grid = function (fieldsHtml, columns) {
  return `<div class="aia-grid aia-grid-${columns}">${fieldsHtml}</div>`;
};

// A group: icon + title + one-line description (+ optional badge), then its rows.
window.AIA.ui.card = function (o) {
  const badge = o.badge ? `<span class="aia-badge">${escapeHtml(o.badge)}</span>` : "";
  return `
    <section class="aia-card" id="aiaGroup-${o.id}" data-aia-group="${o.id}">
      <header class="aia-card-head">
        <span class="aia-card-icon"><i class="bi ${o.icon}"></i></span>
        <div class="aia-card-title">
          <h2 data-i18n="${o.titleKey}">${t(o.titleKey, o.title)}</h2>
          <p data-i18n="${o.descKey}">${t(o.descKey, o.desc)}</p>
        </div>${badge}
      </header>
      <div class="aia-card-body">${o.body}</div>
    </section>`;
};

// A group's title and icon, used by the card header and the section chips.
window.AIA.ui.GROUPS = [
  [
    "provider",
    "bi-gear",
    "ai_grp_provider",
    "Provider and model",
    "Which AI runs the advisor and how it is called.",
  ],
  [
    "safety",
    "bi-shield-check",
    "ai_grp_safety",
    "Permissions and safety",
    "What the AI may touch and how its answers are checked.",
  ],
  [
    "domains",
    "bi-chat-square-text",
    "ai_grp_domains",
    "Chat domains",
    "Which kinds of questions the AI workspace accepts.",
  ],
  [
    "routing",
    "bi-signpost-split",
    "ai_grp_routing",
    "Answers and routing",
    "How a question is answered before and during an AI run.",
  ],
  [
    "agent",
    "bi-stopwatch",
    "ai_grp_agent",
    "Agent limits",
    "Ceilings for each question asked in Agent mode.",
  ],
  [
    "docs",
    "bi-file-earmark-text",
    "ai_grp_docs",
    "Documents",
    "Long documents such as the user guide, written one screen at a time.",
  ],
  [
    "files",
    "bi-download",
    "ai_grp_files",
    "File generation",
    "Excel, Word, PDF, CSV and code files built from your data.",
  ],
  [
    "speech",
    "bi-mic",
    "ai_grp_speech",
    "Speech (STT / TTS)",
    "Optional speech services, configured independently from text AI.",
  ],
  ["diag", "bi-bug", "ai_grp_diag", "Diagnostics", "For troubleshooting only."],
];

window.AIA.ui.chips = function () {
  const items = window.AIA.ui.GROUPS.map(
    ([id, , key, fallback], i) =>
      `<button type="button" class="aia-chip${i === 0 ? " active" : ""}" data-aia-target="${id}" data-i18n="${key}">${t(key, fallback)}</button>`
  ).join("");
  return `<nav class="aia-chips" id="aiaChips" aria-label="${escapeHtml(t("ai_grp_nav", "Sections"))}">${items}</nav>`;
};

// Chip click scrolls to its card (no hash change: the hash is the app's router); the chip of the card in view is highlighted.
window.AIA.ui.wireChips = function () {
  const chips = document.getElementById("aiaChips");
  if (!chips) return;
  const mark = (id) =>
    chips
      .querySelectorAll(".aia-chip")
      .forEach((c) => c.classList.toggle("active", c.dataset.aiaTarget === id));
  chips.addEventListener("click", (e) => {
    const chip = e.target.closest(".aia-chip");
    const card = chip && document.getElementById(`aiaGroup-${chip.dataset.aiaTarget}`);
    if (!card) return;
    mark(chip.dataset.aiaTarget);
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  if (typeof IntersectionObserver !== "function") return;
  const seen = new IntersectionObserver(
    (entries) => {
      const top = entries
        .filter((en) => en.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (top) mark(top.target.dataset.aiaGroup);
    },
    { rootMargin: "-120px 0px -65% 0px" }
  );
  document.querySelectorAll(".aia-card").forEach((card) => seen.observe(card));
};
