"use strict";

// ── Income Analytics — drill-down drawer ──

function _incomeOpenDrawer(src, key) {
  const D = window._incomeData;
  const list = (D.records || []).filter((r) => r.source === src && r.key === key);
  if (!list.length) return;
  document.getElementById("incomeDrawerTitle").textContent =
    _incomeSourceLabel(src) + " · " + _incomeItemLabel(src, key);
  const rows = list
    .map((r) => {
      const dot =
        D.periods.length > 1
          ? `<span class="${r.period === "A" ? "income-pa" : "income-pb"}">●</span> `
          : "";
      return (
        `<tr><td>${dot}${wfEsc(r.date)}</td><td>${wfEsc(r.ref)}</td><td class="num">${_incomeFmt(r.amount)}</td></tr>`
      );
    })
    .join("");
  const total = list.reduce((a, r) => a + r.amount, 0);
  document.getElementById("incomeDrawerBody").innerHTML =
    `<table><thead><tr><th>${t("income_date", "Period")}</th><th>${t("income_ref", "Reference")}</th><th class="num">${t("income_amount", "Amount")}</th></tr></thead>` +
    `<tbody>${rows}<tr class="income-grand"><td colspan="2">${t("income_subtotal", "Subtotal")}</td><td class="num">${_incomeFmt(total)}</td></tr></tbody></table>`;
  document.getElementById("incomeDrawer").classList.add("open");
  document.getElementById("incomeDrawer").setAttribute("aria-hidden", "false");
  document.getElementById("incomeDrawerBg").classList.add("open");
}

function _incomeCloseDrawer() {
  const d = document.getElementById("incomeDrawer");
  const bg = document.getElementById("incomeDrawerBg");
  if (d) {
    d.classList.remove("open");
    d.setAttribute("aria-hidden", "true");
  }
  if (bg) bg.classList.remove("open");
}

function _incomeBindShell() {
  document.getElementById("incomeDrawerClose").onclick = _incomeCloseDrawer;
  document.getElementById("incomeDrawerBg").onclick = _incomeCloseDrawer;
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _incomeCloseDrawer();
  });
}
