"use strict";

function setBreadcrumb(title) {
  const bc = document.getElementById("breadcrumb");
  if (bc) bc.textContent = title;
}

// Legacy translation alias used by some modules

function translate(key) {
  const lang = localStorage.getItem("lang") || "en";
  return window.translations?.[lang]?.[key] || key;
}

// ════════════════════════════════════════════════════════════════════════════
// THEME TOGGLE
// ════════════════════════════════════════════════════════════════════════════

function renderTabsShell(containerId, tabButtonsHtml) {
  return `
        <div class="wf-tabs-shell">
            <div class="wf-tabs-row" id="${containerId}" role="tablist">
                ${tabButtonsHtml}
            </div>
        </div>
    `;
}

function initTabsWithMoreMenu(options = {}) {
  const containerId = options.containerId;
  if (!containerId) return;

  const tablist = document.getElementById(containerId);
  if (!tablist) return;

  const visibleCount = Number.isInteger(options.visibleCount) ? options.visibleCount : 4;
  const tabSelector = options.tabSelector || ".wf-tab, .settings-tab, .financial-advisor-tab";
  const activeClass = options.activeClass || "active";

  const originalTabs = Array.from(tablist.querySelectorAll(tabSelector)).filter((el) => {
    const parent = el.parentElement;
    return !parent || !parent.classList.contains("wf-more-menu");
  });

  if (!originalTabs.length) {
    return;
  }

  if (tablist.__wfMoreAbortController) {
    tablist.__wfMoreAbortController.abort();
  }

  const mainTabs = originalTabs.slice(0, visibleCount);
  const hiddenTabs = originalTabs.slice(visibleCount);

  tablist.innerHTML = "";
  tablist.classList.add("wf-tabs-row");

  const mainWrap = document.createElement("div");
  mainWrap.className = "wf-main-tabs";
  mainTabs.forEach((tab) => {
    tab.classList.add("wf-tab");
    mainWrap.appendChild(tab);
  });
  tablist.appendChild(mainWrap);

  if (!hiddenTabs.length) {
    return;
  }

  const moreWrap = document.createElement("div");
  moreWrap.className = "wf-more-wrap";

  const moreBtn = document.createElement("button");
  moreBtn.type = "button";
  moreBtn.className = "wf-tab wf-more-toggle";
  moreBtn.setAttribute("aria-haspopup", "true");
  moreBtn.setAttribute("aria-expanded", "false");
  moreBtn.innerHTML = `
        <span>${options.moreLabel || (typeof t === "function" ? t("financial_advisor_tab_more", "More") : "More")}</span>
        <i class="bi bi-chevron-down wf-more-icon"></i>
    `;

  const moreMenu = document.createElement("div");
  moreMenu.className = "wf-more-menu";
  moreMenu.setAttribute("role", "menu");

  hiddenTabs.forEach((tab) => {
    tab.classList.add("wf-dropdown-item");
    tab.classList.remove("wf-tab");
    moreMenu.appendChild(tab);
  });

  moreWrap.appendChild(moreBtn);
  moreWrap.appendChild(moreMenu);
  tablist.appendChild(moreWrap);

  const closeMoreMenu = () => {
    moreWrap.classList.remove("open");
    moreBtn.setAttribute("aria-expanded", "false");
  };

  const positionMoreMenu = () => {
    moreMenu.classList.remove("align-right", "align-left");
    const rect = moreMenu.getBoundingClientRect();
    const viewportPadding = 12;

    if (rect.right > window.innerWidth - viewportPadding) {
      moreMenu.classList.add("align-right");
      return;
    }

    if (rect.left < viewportPadding) {
      moreMenu.classList.add("align-left");
    }
  };

  const openMoreMenu = () => {
    moreWrap.classList.add("open");
    moreBtn.setAttribute("aria-expanded", "true");
    window.requestAnimationFrame(positionMoreMenu);
  };

  const syncMoreActiveState = () => {
    const hasHiddenActive = hiddenTabs.some((tab) => tab.classList.contains(activeClass));
    moreWrap.classList.toggle("active", hasHiddenActive);
    moreBtn.classList.toggle(activeClass, hasHiddenActive);
  };

  const abortController = new AbortController();
  tablist.__wfMoreAbortController = abortController;
  const signal = abortController.signal;

  moreBtn.addEventListener(
    "click",
    (event) => {
      event.stopPropagation();
      if (moreWrap.classList.contains("open")) {
        closeMoreMenu();
      } else {
        openMoreMenu();
      }
    },
    { signal }
  );

  document.addEventListener(
    "click",
    (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!moreWrap.contains(target)) {
        closeMoreMenu();
      }
    },
    { signal }
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Escape") {
        closeMoreMenu();
      }
    },
    { signal }
  );

  window.addEventListener(
    "resize",
    () => {
      if (moreWrap.classList.contains("open")) {
        positionMoreMenu();
      }
    },
    { signal }
  );

  tablist.addEventListener(
    "shown.bs.tab",
    () => {
      window.setTimeout(syncMoreActiveState, 0);
    },
    { signal }
  );

  moreMenu.querySelectorAll("button").forEach((menuItem) => {
    menuItem.addEventListener(
      "click",
      () => {
        closeMoreMenu();
        window.setTimeout(syncMoreActiveState, 0);
      },
      { signal }
    );
  });

  tablist.querySelectorAll("button").forEach((tab) => {
    tab.addEventListener(
      "click",
      () => {
        window.setTimeout(syncMoreActiveState, 0);
      },
      { signal }
    );
  });

  syncMoreActiveState();
}

// ════════════════════════════════════════════════════════════════════════════
// COLLAPSIBLE TABLES
// Auto-discovers every .data-table whose <tbody> has more than ROW_LIMIT rows
// and attaches an expand / collapse toggle button beneath the wrapping card.
// Called automatically from applyTranslations() so no individual file needs
// to be touched.
// ════════════════════════════════════════════════════════════════════════════

const _COLLAPSIBLE_ROW_LIMIT = 5;
const _COLLAPSIBLE_ATTR = "data-collapsible-init";

function initCollapsibleTables() {
  document.querySelectorAll(`table.data-table:not([${_COLLAPSIBLE_ATTR}])`).forEach((table) => {
    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    const allRows = Array.from(tbody.querySelectorAll("tr"));
    if (allRows.length <= _COLLAPSIBLE_ROW_LIMIT) return;

    // Mark so we never double-init
    table.setAttribute(_COLLAPSIBLE_ATTR, "1");

    // Hide rows beyond the limit
    allRows.slice(_COLLAPSIBLE_ROW_LIMIT).forEach((r) => {
      r.classList.add("wf-collapsible-hidden");
      r.style.display = "none";
    });

    // Resolve translated label immediately using t() — applyTranslations()
    // has already finished by the time this function runs, so data-i18n-key
    // attributes would never be processed. We fill the text synchronously.
    const _fillLabel = (span, key, count) => {
      let text = typeof t === "function" ? t(key, key) : key;
      if (count !== undefined) {
        const countStr = typeof fmtInt === "function" ? fmtInt(count) : String(count);
        text = text.replace("{count}", countStr);
      }
      span.textContent = text;
      // Keep data attributes so language-change re-runs of applyTranslations() also work
      span.setAttribute("data-i18n-key", key);
      if (count !== undefined) {
        span.setAttribute("data-i18n-params", JSON.stringify({ count }));
      } else {
        span.removeAttribute("data-i18n-params");
      }
    };

    // Find the insertion point: the .table-container wrapper (or direct parent)
    const tableContainer = table.closest(".table-container") || table.parentElement;
    if (!tableContainer) return;

    // Build the toggle button
    const btn = document.createElement("div");
    btn.className = "wf-table-toggle-btn";
    btn.style.cssText = [
      "border-top:1px solid var(--border-color)",
      "cursor:pointer",
      "text-align:center",
      "padding:11px 16px",
    ].join(";");

    const span = document.createElement("span");
    span.style.cssText = "color:var(--accent-primary,#0d6efd);font-weight:600;font-size:14px;";
    _fillLabel(span, "show_all_rows", allRows.length);
    btn.appendChild(span);

    // Toggle logic
    btn.addEventListener("click", () => {
      const showing = btn.getAttribute("data-showing") === "true";
      allRows.slice(_COLLAPSIBLE_ROW_LIMIT).forEach((r) => {
        r.style.display = showing ? "none" : "table-row";
      });
      btn.setAttribute("data-showing", String(!showing));
      if (showing) {
        _fillLabel(span, "show_all_rows", allRows.length);
      } else {
        _fillLabel(span, "show_less_rows");
      }
    });

    // Insert immediately after the table-container (still inside the card wrapper)
    tableContainer.insertAdjacentElement("afterend", btn);
  });
}

// Reusable Collapsible Card Helpers
function initCollapsibleCard(card, containerSelector, onToggle = null) {
  const header = card.querySelector(".item-header");
  if (!header) return;

  header.addEventListener("click", (e) => {
    // If clicking on inputs, select, textarea, or remove button, do not toggle
    if (
      e.target.closest(".item-remove-btn") ||
      e.target.closest("input") ||
      e.target.closest("select") ||
      e.target.closest("textarea")
    ) {
      return;
    }
    toggleCollapsibleCard(card, containerSelector);
    if (onToggle) onToggle(card);
  });
}

function toggleCollapsibleCard(card, containerSelector, forceExpand = null) {
  const container = containerSelector ? card.closest(containerSelector) : card.parentElement;
  if (!container) return;

  const body = card.querySelector(".item-body");
  const chevron = card.querySelector(".item-chevron");
  const isExpanded = forceExpand !== null ? forceExpand : !card.classList.contains("open");

  if (isExpanded) {
    // Collapse all other cards in the same container (accordion behavior)
    container.querySelectorAll(".item-card").forEach((otherCard) => {
      if (otherCard !== card) {
        otherCard.classList.remove("open");
        const b = otherCard.querySelector(".item-body");
        if (b) b.style.display = "none";
        const c = otherCard.querySelector(".item-chevron");
        if (c) c.style.transform = "";
      }
    });

    card.classList.add("open");
    if (body) body.style.display = "block";
    if (chevron) chevron.style.transform = "rotate(90deg)";
  } else {
    card.classList.remove("open");
    if (body) body.style.display = "none";
    if (chevron) chevron.style.transform = "";
  }
}
