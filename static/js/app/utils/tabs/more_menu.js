"use strict";
// Collapses overflow tabs into a "More" dropdown menu with positioning and
// active-state syncing.
// Part of the app/utils module (split from the former monolithic tabs.js,
// 200-line rule). Do not edit directly.

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
