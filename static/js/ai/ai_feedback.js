"use strict";

/**
 * AI Workspace — answer feedback (thumbs up / down)
 * Renders the thumbs bar under assistant answers and sends the rating to the backend.
 * Thumbs-up answers to how/where/should questions become examples for similar questions;
 * thumbs-down answers are never reused. Clicking the active thumb again clears the rating.
 * Depends on: ai_core.js (_aiT), ai_messages.js
 */

function _renderFeedbackBar(messageId, feedback) {
  const up = feedback === 1 ? " active" : "";
  const down = feedback === -1 ? " active" : "";
  return `
    <div class="ai-ws-feedback" data-msg-id="${messageId}">
      <button type="button" class="ai-ws-fb-btn ai-ws-fb-up${up}" data-rating="1"
        data-i18n-title="ai_ws_feedback_up" title="Helpful" aria-pressed="${feedback === 1}">
        <i class="bi bi-hand-thumbs-up"></i>
      </button>
      <button type="button" class="ai-ws-fb-btn ai-ws-fb-down${down}" data-rating="-1"
        data-i18n-title="ai_ws_feedback_down" title="Not helpful" aria-pressed="${feedback === -1}">
        <i class="bi bi-hand-thumbs-down"></i>
      </button>
      <span class="ai-ws-fb-error" hidden></span>
    </div>
  `;
}

async function _aiSendFeedback(button) {
  const bar = button.closest(".ai-ws-feedback");
  if (!bar || bar.dataset.busy === "1") return;
  const clicked = parseInt(button.dataset.rating, 10);
  const next = button.classList.contains("active") ? 0 : clicked;
  const errorEl = bar.querySelector(".ai-ws-fb-error");
  bar.dataset.busy = "1";
  errorEl.hidden = true;
  try {
    const res = await fetch(`/api/financial-advisor/ai/messages/${bar.dataset.msgId}/feedback/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.wfGetCsrfToken?.() || "",
      },
      body: JSON.stringify({ rating: next }),
    });
    if (!res.ok) throw new Error("feedback_failed");
    const data = await res.json();
    bar.querySelectorAll(".ai-ws-fb-btn").forEach((btn) => {
      const on = parseInt(btn.dataset.rating, 10) === data.rating;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    });
  } catch (_e) {
    errorEl.textContent = _aiT("ai_ws_feedback_error", "Could not save your feedback.");
    errorEl.hidden = false;
  } finally {
    bar.dataset.busy = "0";
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest(".ai-ws-fb-btn");
  if (button) _aiSendFeedback(button);
});

window._renderFeedbackBar = _renderFeedbackBar;
window._aiSendFeedback = _aiSendFeedback;
