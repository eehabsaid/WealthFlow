"use strict";

// ── Income Analytics — KPIs, source cards, grouped table ──

function _incomeDeltaBadge(a, b, labelKey) {
  if (b === null || b === undefined) return "";
  const p = b ? (a - b) / Math.abs(b) * 100 : null;
  if (p === null) return "";
  const cls = p > 0.05 ? "up" : p < -0.05 ? "down" : "flat";
  const arrow = p > 0.05 ? "▲" : p < -0.05 ? "▼" : "■";
  return (
    `<span class="income-delta ${cls}">${arrow} ${Math.abs(p).toFixed(1)}%</span> ` +
    `<span class="income-ks" style="display:inline">${t(labelKey, "")}</span>`
  );
}

function _incomePeriodLabel(p) {
  if (p.month) return `${_incomeMonthName(p.month)} ${p.year}`;
  return String(p.year);
}

function _incomeRenderKpis(D) {
  const P = D.periods;
  const A = P[0];
  const B = P[1] || null;
  const sa = D.stats_a;
  const ref = B ? D.grand.total_b : D.prev_period_total;
  const hero =
    `<div class="income-card income-kpi-hero">` +
    `<div class="income-kl">${t("income_total", "Total income")} · <span class="${B ? "income-pa" : ""}">${wfEsc(_incomePeriodLabel(A))}</span></div>` +
    `<div class="income-kv">${_incomeFmt(sa.total)}<small>${wfEsc(window.baseCurrencyCode ? baseCurrencyCode() : "")}</small></div>` +
    (B ? `<div class="income-ks"><span class="income-pb">${wfEsc(_incomePeriodLabel(P[1]))}</span>: ${_incomeFmt(D.grand.total_b)}</div>` : "") +
    (ref !== null && ref !== undefined ? (B ? _incomeDeltaBadge(D.grand.total_b, sa.total, "income_vs_b") : _incomeDeltaBadge(sa.total, ref, "income_vs_prev")) : "") +
    "</div>";
  const avg = sa.active_months ? sa.total / sa.active_months : 0;
  const k2 =
    `<div class="income-card"><div class="income-kl" data-i18n="income_avg">Average per month</div>` +
    `<div class="income-kv income-kv-sm">${_incomeFmt(avg)}</div>` +
    `<div class="income-ks">${sa.active_months} ${t("income_months_active", "months with income")}</div></div>`;
  const k3 =
    `<div class="income-card"><div class="income-kl" data-i18n="income_best">Best month</div>` +
    `<div class="income-kv income-kv-sm">${sa.best_month ? _incomeFmt(sa.best_month_total) : "—"}</div>` +
    `<div class="income-ks">${sa.best_month ? _incomeMonthName(sa.best_month) + " " + A.year : ""}</div></div>`;
  const srcCount = new Set((D.records || []).filter((r) => r.period === "A").map((r) => r.source)).size;
  const k4 =
    `<div class="income-card"><div class="income-kl" data-i18n="income_count">Records</div>` +
    `<div class="income-kv income-kv-sm">${sa.records}</div>` +
    `<div class="income-ks">${srcCount} / ${INCOME_SOURCE_IDS.length} ${t("income_sources", "Income sources").toLowerCase()}</div></div>`;
  return `<div class="income-kpis">${hero}${k2}${k3}${k4}</div>`;
}

function _incomeRenderSourceCards(D) {
  const S = window._incomeState;
  const sa = D.stats_a;
  const cards = (D.sources || [])
    .filter((s) => S.sources.includes(s.id))
    .map((s) => {
      const g = (D.groups || []).find((x) => x.source === s.id);
      const a = g ? g.amount_a : 0;
      const b = g ? g.amount_b : null;
      const share = sa.total ? (a / sa.total) * 100 : 0;
      let meta;
      if (b !== null && g) {
        const p = a ? ((b - a) / Math.abs(a)) * 100 : null;
        meta = p === null ? "" : (p >= 0 ? "▲ " : "▼ ") + Math.abs(p).toFixed(1) + "%";
      } else {
        meta = (g ? g.count_a : 0) + " " + t("income_records", "records");
      }
      return (
        `<div class="income-card income-src-card" data-src="${s.id}">` +
        `<div class="income-src-top"><span class="income-dot" style="width:9px;height:9px;border-radius:50%;background:${s.color}"></span>${_incomeSourceLabel(s.id)}</div>` +
        `<div class="income-src-v">${_incomeFmt(a)}</div>` +
        `<div class="income-bar"><i style="width:${share.toFixed(1)}%;background:${s.color}"></i></div>` +
        `<div class="income-src-meta"><span>${share.toFixed(1)}% ${t("income_share", "of total")}</span><span>${meta}</span></div>` +
        "</div>"
      );
    })
    .join("");
  return `<div class="income-src-cards">${cards}</div>`;
}

function _incomeDCells(a, b) {
  const d = b - a;
  const p = a ? ((b - a) / Math.abs(a)) * 100 : null;
  const c = d > 0 ? "income-d-up" : d < 0 ? "income-d-down" : "";
  return (
    `<td class="num ${c}">${d > 0 ? "+" : ""}${_incomeFmt(d)}</td>` +
    `<td class="num ${c}">${p === null ? "—" : (p > 0 ? "+" : "") + p.toFixed(1) + "%"}</td>`
  );
}

function _incomeRenderTable(D) {
  const P = D.periods;
  const cmp = !!P[1];
  const sa = D.stats_a;
  const head = cmp
    ? `<tr><th>${t("income_item", "Item")}</th><th class="num income-pa">${wfEsc(_incomePeriodLabel(P[0]))}</th><th class="num income-pb">${wfEsc(_incomePeriodLabel(P[1]))}</th><th class="num">${t("income_change", "Change")}</th><th class="num">%</th></tr>`
    : `<tr><th>${t("income_item", "Item")}</th><th class="num">${t("income_count", "Records")}</th><th class="num">${t("income_amount", "Amount")}</th><th class="num">${t("income_share", "of total")}</th></tr>`;
  let body = "";
  (D.groups || []).forEach((g) => {
    const s = (D.sources || []).find((x) => x.id === g.source);
    body +=
      `<tr class="income-grp" data-g="${g.source}"><td colspan="${cmp ? 5 : 4}"><span class="income-caret">▾</span>` +
      `<span class="income-dot" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${s ? s.color : ""};margin-inline-end:8px"></span>` +
      `${_incomeSourceLabel(g.source)}<span class="income-badge">${g.count_a + g.count_b} ${t("income_records", "records")}</span></td></tr>`;
    g.items.forEach((it) => {
      const cnt = g.source === "cert" || g.source === "bank" ? `<span class="income-badge">${it.count_a} ${t("income_postings", "postings")}</span>` : "";
      body += cmp
        ? `<tr class="income-item" data-g="${g.source}" data-k="${wfEsc(it.key)}"><td>${wfEsc(_incomeItemLabel(g.source, it.key))}</td><td class="num">${_incomeFmt(it.amount_a)}</td><td class="num">${_incomeFmt(it.amount_b)}</td>${_incomeDCells(it.amount_a, it.amount_b)}</tr>`
        : `<tr class="income-item" data-g="${g.source}" data-k="${wfEsc(it.key)}"><td>${wfEsc(_incomeItemLabel(g.source, it.key))}${cnt}</td><td class="num">${it.count_a}</td><td class="num">${_incomeFmt(it.amount_a)}</td><td class="num"><span class="income-pct">${sa.total ? (it.amount_a / sa.total * 100).toFixed(1) : "0.0"}%</span></td></tr>`;
    });
    body += cmp
      ? `<tr class="income-sub" data-g="${g.source}"><td>${t("income_subtotal", "Subtotal")} — ${_incomeSourceLabel(g.source)}</td><td class="num">${_incomeFmt(g.amount_a)}</td><td class="num">${_incomeFmt(g.amount_b)}</td>${_incomeDCells(g.amount_a, g.amount_b)}</tr>`
      : `<tr class="income-sub" data-g="${g.source}"><td>${t("income_subtotal", "Subtotal")} — ${_incomeSourceLabel(g.source)}</td><td class="num">${g.count_a}</td><td class="num">${_incomeFmt(g.amount_a)}</td><td class="num"><span class="income-pct">${sa.total ? (g.amount_a / sa.total * 100).toFixed(1) : "0.0"}%</span></td></tr>`;
  });
  body += cmp
    ? `<tr class="income-grand"><td>${t("income_grand", "Total income")}</td><td class="num">${_incomeFmt(D.grand.total_a)}</td><td class="num">${_incomeFmt(D.grand.total_b)}</td>${_incomeDCells(D.grand.total_a, D.grand.total_b)}</tr>`
    : `<tr class="income-grand"><td>${t("income_grand", "Total income")}</td><td class="num">${sa.records}</td><td class="num">${_incomeFmt(D.grand.total_a)}</td><td class="num">100%</td></tr>`;
  return (
    `<div class="income-card income-tbl-card"><div class="income-tbl-head">` +
    `<div class="income-ch-title" style="margin:0">${t("income_breakdown", "Detailed breakdown")}</div>` +
    `<span class="income-ks" style="margin:0">${wfEsc(_incomePeriodLabel(P[0]))}${cmp ? " vs " + wfEsc(_incomePeriodLabel(P[1])) : ""}</span></div>` +
    `<div class="income-tbl-wrap"><table><thead>${head}</thead><tbody>${body}</tbody></table></div></div>`
  );
}

function _incomeBindTable() {
  document.querySelectorAll(".income-grp").forEach((g) => {
    g.onclick = () => {
      g.classList.toggle("collapsed");
      const hide = g.classList.contains("collapsed");
      document.querySelectorAll(`.income-item[data-g="${g.dataset.g}"]`).forEach((r) => (r.style.display = hide ? "none" : ""));
    };
  });
  document.querySelectorAll(".income-item").forEach((r) => {
    r.onclick = () => _incomeOpenDrawer(r.dataset.g, r.dataset.k);
  });
  document.querySelectorAll(".income-src-card").forEach((c) => {
    c.onclick = () => {
      const g = document.querySelector(`.income-grp[data-g="${c.dataset.src}"]`);
      if (g) g.scrollIntoView({ behavior: "smooth", block: "center" });
    };
  });
}

function _incomeRenderContent() {
  const D = window._incomeData;
  const el = document.getElementById("incomeContent");
  if (!el) return;
  window._incomeCharts.forEach((c) => c.destroy());
  window._incomeCharts = [];
  const empty = !D.stats_a.records && !(D.stats_b && D.stats_b.records);
  if (empty) {
    el.innerHTML =
      `<div class="income-card income-empty"><div class="income-empty-ic">🗂️</div>` +
      `<div style="font-weight:700;color:var(--text-secondary)" data-i18n="income_no_data">No income recorded for this selection</div>` +
      `<div style="margin-top:4px" data-i18n="income_no_data_hint">Try another year, more months or more sources.</div></div>`;
    return;
  }
  el.innerHTML = _incomeRenderKpis(D) + _incomeRenderSourceCards(D) + _incomeChartsShell() + _incomeRenderTable(D);
  _incomeBindTable();
  _incomeDrawCharts(D);
}

function _incomeChartsShell() {
  const S = window._incomeState;
  const titles =
    S.mode === "off"
      ? [t("income_monthly", "Monthly income by source"), t("income_mix", "Income mix")]
      : S.mode === "yoy"
        ? [t("income_trend", "Month-by-month trend"), t("income_cmp_src", "Period A vs Period B by source")]
        : [t("income_cmp_src", "Period A vs Period B by source"), t("income_delta_src", "Change by source")];
  const cur = wfEsc(window.baseCurrencyCode ? baseCurrencyCode() : "");
  return (
    `<div class="income-charts">` +
    `<div class="income-card"><div class="income-ch-title">${titles[0]}<span>${cur}</span></div><div class="income-ch"><canvas id="incomeC1"></canvas></div></div>` +
    `<div class="income-card"><div class="income-ch-title">${titles[1]}<span>${cur}</span></div><div class="income-ch"><canvas id="incomeC2"></canvas></div></div>` +
    "</div>"
  );
}
