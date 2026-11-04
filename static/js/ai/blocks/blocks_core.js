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
    const editable = b.status === "pending" && p.editable && window.AIBlockForm;
    const rows = editable
      ? AIBlockForm.rows(p)
      : (p.rows || [])
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
    return `<div class="ai-act-card" data-block-id="${b.id}"${editable ? " data-editable" : ""}><div class="ai-act-title">${esc(title)}</div><table class="ai-act-rows${p.record === "code_file" ? " ai-act-code" : ""}">${rows}</table><div class="ai-act-foot">${foot}</div></div>`;
  }

  // A picture made (or edited) by the generate_image tool: shown under the answer with a download button.
  function imageCard(f) {
    const src = `/api/financial-advisor/ai/attachments/${f.id}/`;
    const alt = esc(T("ai_image_alt", "Generated image"));
    return `<figure class="ai-gen-image" data-att-id="${f.id}"><a href="${src}" target="_blank" rel="noopener"><img src="${src}" alt="${alt}" loading="lazy" data-fail="${esc(T("ai_image_load_failed", "The image could not be loaded."))}" onerror="this.closest('figure').classList.add('ai-gen-image-failed'); this.alt=this.dataset.fail"></a><figcaption><a class="btn btn-sm btn-outline-secondary" href="${src}?download=1" download="${esc(f.name)}"><i class="bi bi-download"></i> ${esc(T("ai_image_download", "Download"))}</a></figcaption></figure>`;
  }

  // The pictures the user attached to a message (for editing), as small previews next to the file chips.
  function thumbs(files) {
    return files
      .filter((f) => f.kind === "image" && !f.generated)
      .map(
        (f) =>
          `<img class="ai-attach-thumb" src="/api/financial-advisor/ai/attachments/${f.id}/" alt="${esc(f.name)}" loading="lazy">`
      )
      .join("");
  }

  function repaintPending() {
    document.querySelectorAll(".ai-act-card[data-editable]").forEach((el) => {
      const b = Object.values(byMsg)
        .flat()
        .find((x) => x.id === Number(el.dataset.blockId));
      if (b && b.status === "pending") el.outerHTML = actionCard(b);
    });
  }

  function render(ctx) {
    if (ctx.role === "user" && ctx.messageId) {
      const mine = filesByMsg[ctx.messageId] || [];
      return (window.AIAttach?.chips(mine) || "") + thumbs(mine);
    }
    if (ctx.role !== "assistant" || !ctx.messageId) return "";
    const pictures = (filesByMsg[ctx.messageId] || [])
      .filter((f) => f.generated)
      .map(imageCard)
      .join("");
    return (
      pictures +
      (byMsg[ctx.messageId] || [])
        .map((b) =>
          b.kind === "action"
            ? actionCard(b)
            : b.kind === "chart"
              ? window.AIChart?.draw(b) || ""
              : ""
        )
        .join("")
    );
  }

  async function decide(id, confirm) {
    const card = document.querySelector(`.ai-act-card[data-block-id="${id}"]`);
    const edits = confirm && card?.hasAttribute("data-editable") ? AIBlockForm.collect(card) : null;
    const res = await fetch(
      `/api/financial-advisor/ai/blocks/${id}/${confirm ? "confirm" : "cancel"}/`,
      {
        method: "POST",
        headers: {
          "X-CSRFToken": window.wfGetCsrfToken?.() || "",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ edits }),
      }
    );
    const data = await res.json().catch(() => ({}));
    if (res.status === 422 && data.error) return AIBlockForm.showError(card, data.error);
    if (data.block) {
      const old = document.querySelector(`.ai-act-card[data-block-id="${id}"]`);
      if (old) old.outerHTML = actionCard(data.block);
    }
  }

  (window._aiMessageExtras = window._aiMessageExtras || []).push(render);
  return { remember, decide, repaintPending };
})();

window.AIBlocks = AIBlocks;
