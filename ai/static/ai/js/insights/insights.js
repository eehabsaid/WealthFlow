"use strict";

/**
 * Proactive insights: facts the server computed from the user's own data, shown as welcome cards in the AI workspace
 * and as a bell in the top bar. The sentences come from translations; the numbers come from the server.
 */

const AIInsights = (() => {
  const esc = (t) => (typeof _escapeHtml === "function" ? _escapeHtml(t) : String(t));
  const ICON = {
    warn: "bi-exclamation-triangle-fill text-warning",
    info: "bi-info-circle-fill text-primary",
  };
  const FALLBACK = {
    budget_exceeded: "Budget {budget_name} is over its limit ({percent_used}% used).",
    budget_threshold: "Budget {budget_name} reached {percent_used}% of its limit.",
    recurring_due_soon: "{recurring_name} is due on {next_run_date}.",
    recurring_overdue: "{recurring_name} was due on {next_run_date} and has not run.",
    salary_unpaid: "Salary from {company} for {month} {year} is not marked paid yet.",
    month_vs_last:
      "Spending so far this month is {this_month} {currency}, {change_percent}% versus the same days last month ({last_month} {currency}).",
  };
  let cache = [];

  function sentence(i) {
    const text = _aiT("ai_insight_" + i.type, FALLBACK[i.type] || i.type);
    return text.replace(/\{(\w+)\}/g, (_m, k) =>
      i.params && i.params[k] !== undefined ? i.params[k] : ""
    );
  }

  const line = (i) =>
    `<div class="ai-insight-item"><i class="bi ${ICON[i.severity] || ICON.info}"></i> <span>${esc(sentence(i))}</span></div>`;

  async function load() {
    try {
      const res = await fetch("/api/financial-advisor/ai/insights/");
      cache = res.ok ? (await res.json()).insights || [] : [];
    } catch (_e) {
      cache = [];
    }
    return cache;
  }

  async function paintWelcome() {
    const box = document.getElementById("ai-ws-insights");
    if (!box) return;
    const list = await load();
    box.innerHTML = list.length
      ? `<div class="ai-ws-suggestions-title">${esc(_aiT("ai_insights_title", "Worth your attention"))}</div>${list.map(line).join("")}`
      : "";
  }

  async function paintBell() {
    const btn = document.getElementById("ai-insight-bell");
    if (!btn) return;
    const list = await load();
    const warn = list.filter((i) => i.severity === "warn").length;
    btn.hidden = !list.length;
    btn.querySelector(".ai-insight-count").textContent = warn || "";
    btn.dataset.bsContent = list.map(line).join("");
    if (window.bootstrap?.Popover) {
      window.bootstrap.Popover.getInstance(btn)?.dispose();
      new window.bootstrap.Popover(btn, {
        html: true,
        trigger: "focus",
        placement: "bottom",
        sanitize: false,
        content: btn.dataset.bsContent,
      });
    }
  }

  return { paintWelcome, paintBell };
})();

window.AIInsights = AIInsights;

setTimeout(() => window.AIInsights.paintBell(), 0);
