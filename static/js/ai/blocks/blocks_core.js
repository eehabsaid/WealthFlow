"use strict";

/**
 * AI Workspace — blocks under an answer: action cards (confirm / cancel) and charts.
 * Cards come from the server (AIChatBlock); the page only draws them and posts the user's decision.
 * Depends on: ai_core.js, ai_messages.js (extension hook), blocks_chart.js
 */

const AIBlocks = (() => {
  const byMsg = {};
  const filesByMsg = {};
  const esc = (t) => (typeof _escapeHtml === "function" ? _escapeHtml(t) : String(t));
  const T = (k, d) => _aiT(k, d);

  function remember(msg) {
    if (msg && msg.id) {
      byMsg[msg.id] = msg.blocks || [];
      filesByMsg[msg.id] = msg.attachments || [];
    }
  }

  function actionCard(b) {
    const p = b.payload || {};
    const rows = (p.rows || [])
      .map((r) =>
        "after" in r
          ? `<tr><th>${esc(r.label)}</th><td><s>${esc(r.before)}</s> → <b>${esc(r.after)}</b></td></tr>`
          : `<tr><th>${esc(r.label)}</th><td>${esc(r.value)}</td></tr>`
      )
      .join("");
    const title = `${T("ai_act_op_" + p.op, p.op)}: ${T("ai_act_rec_" + p.record, p.record)}`;
    let foot;
    if (b.status === "pending") {
      foot = `<button type="button" class="btn btn-sm ${p.op === "delete" ? "btn-danger" : "btn-primary"}" onclick="AIBlocks.decide(${b.id}, true)">${esc(T("ai_act_confirm", "Confirm"))}</button>
              <button type="button" class="btn btn-sm btn-outline-secondary" onclick="AIBlocks.decide(${b.id}, false)">${esc(T("ai_mem_cancel", "Cancel"))}</button>`;
    } else {
      foot = `<span class="small ai-act-status-${b.status}">${esc(T("ai_act_status_" + b.status, b.status))}${b.result ? " — " + esc(b.result) : ""}</span>`;
    }
    return `<div class="ai-act-card" data-block-id="${b.id}"><div class="ai-act-title">${esc(title)}</div><table class="ai-act-rows">${rows}</table><div class="ai-act-foot">${foot}</div></div>`;
  }

  function render(ctx) {
    if (ctx.role === "user" && ctx.messageId)
      return window.AIAttach?.chips(filesByMsg[ctx.messageId] || []) || "";
    if (ctx.role !== "assistant" || !ctx.messageId) return "";
    return (byMsg[ctx.messageId] || [])
      .map((b) =>
        b.kind === "action"
          ? actionCard(b)
          : b.kind === "chart"
            ? window.AIChart?.draw(b) || ""
            : ""
      )
      .join("");
  }

  async function decide(id, confirm) {
    const res = await fetch(
      `/api/financial-advisor/ai/blocks/${id}/${confirm ? "confirm" : "cancel"}/`,
      {
        method: "POST",
        headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
      }
    );
    const data = await res.json().catch(() => ({}));
    if (data.block) {
      const old = document.querySelector(`.ai-act-card[data-block-id="${id}"]`);
      if (old) old.outerHTML = actionCard(data.block);
    }
  }

  (window._aiMessageExtras = window._aiMessageExtras || []).push(render);
  return { remember, decide };
})();

window.AIBlocks = AIBlocks;
