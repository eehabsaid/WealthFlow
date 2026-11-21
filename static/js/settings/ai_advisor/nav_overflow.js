"use strict";
// AI Advisor settings: tabs that do not fit the bar move into a "More" dropdown, like the Settings tab bar above it.
// The split is measured on the real widths, so it follows the screen, the language and the font. Tabs only move in the
// DOM (ids, data attributes and click handling stay as they are); layout only.

window.AIA = window.AIA || {};

window.AIA.ui.closeMore = function () {
  const wrap = document.querySelector(".aia-more");
  if (!wrap) return;
  wrap.classList.remove("open");
  wrap.querySelector(".aia-more-btn").setAttribute("aria-expanded", "false");
};

// "More" shows as active while the open section is one of the tabs inside it.
window.AIA.ui.syncMoreActive = function () {
  const wrap = document.querySelector(".aia-more");
  if (wrap)
    wrap
      .querySelector(".aia-more-btn")
      .classList.toggle("active", !!wrap.querySelector(".aia-chip.active"));
};

window.AIA.ui.layoutTabs = function () {
  const nav = document.getElementById("aiaChips");
  const wrap = nav && nav.querySelector(".aia-more");
  if (!wrap || !nav.clientWidth) return; // not shown (another tab is open): nothing to measure
  const menu = wrap.querySelector(".aia-more-menu");
  const chips = [...nav.querySelectorAll(".aia-chip")].sort(
    (a, b) => a.dataset.aiaIdx - b.dataset.aiaIdx
  );
  wrap.hidden = true;
  chips.forEach((chip) => nav.insertBefore(chip, wrap)); // everything back in the bar, in order, to measure
  const widths = chips.map((chip) => (chip.hidden ? 0 : chip.offsetWidth));
  if (widths.reduce((a, b) => a + b, 0) > nav.clientWidth) {
    wrap.hidden = false;
    const room = nav.clientWidth - wrap.offsetWidth;
    let used = 0;
    let full = false;
    chips.forEach((chip, i) => {
      used += widths[i];
      full = full || used > room;
      if (full && !chip.hidden) menu.appendChild(chip);
    });
  }
  if (!menu.children.length) window.AIA.ui.closeMore();
  window.AIA.ui.syncMoreActive();
};

window.AIA.ui.wireMore = function (nav) {
  const wrap = nav.querySelector(".aia-more");
  const btn = wrap.querySelector(".aia-more-btn");
  const state = window.AIA.state;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = !wrap.classList.contains("open");
    wrap.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  if (state.moreAbort) state.moreAbort.abort(); // the page re-renders after Save: drop the previous page's listeners
  state.moreAbort = new AbortController();
  const { signal } = state.moreAbort;
  document.addEventListener("click", (e) => !wrap.contains(e.target) && window.AIA.ui.closeMore(), {
    signal,
  });
  document.addEventListener("keydown", (e) => e.key === "Escape" && window.AIA.ui.closeMore(), {
    signal,
  });
  if (state.moreObserver) state.moreObserver.disconnect();
  if (typeof ResizeObserver === "function") {
    let frame = 0;
    state.moreObserver = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(window.AIA.ui.layoutTabs);
    });
    state.moreObserver.observe(nav);
  }
  window.AIA.ui.layoutTabs();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(window.AIA.ui.layoutTabs);
};
