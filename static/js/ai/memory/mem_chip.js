/**
 * WealthFlow AI Workspace - "Saved memory" chip
 * The AI updates its memory in the background after a reply. After each answer the page asks, a few times,
 * whether a note was saved or changed since that reply; if so, a small chip appears under the chat.
 * Clicking the chip opens the AI Memory page. Depends on: mem_modal.js
 */

"use strict";

window.AIMemChip = window.AIMemChip || { timer: null };

window.AIMemChip.POLL_MS = 6000;
window.AIMemChip.MAX_POLLS = 100;

window.AIMemChip.clear = function () {
  if (window.AIMemChip.timer) clearTimeout(window.AIMemChip.timer);
  window.AIMemChip.timer = null;
  document.getElementById("ai-mem-chip")?.remove();
};

window.AIMemChip.show = function () {
  const host = document.getElementById("ai-ws-messages");
  if (!host || document.getElementById("ai-mem-chip")) return;
  const label = window.AIMem.t("ai_mem_saved_chip", "Saved memory");
  const chip = document.createElement("div");
  chip.id = "ai-mem-chip";
  chip.className = "text-center my-2";
  chip.innerHTML = `<button type="button" class="btn btn-sm btn-outline-success rounded-pill py-0 px-3" style="font-size:0.75rem;" onclick="openAIMemoryModal()"><i class="bi bi-journal-check me-1"></i><span data-i18n="ai_mem_saved_chip">${window.AIMem.esc(label)}</span></button>`;
  host.appendChild(chip);
  host.scrollTop = host.scrollHeight;
};

window.AIMemChip.watch = function (since) {
  window.AIMemChip.clear();
  if (!since) return;
  let polls = 0;
  const tick = async () => {
    polls += 1;
    try {
      const res = await fetch(
        `/api/financial-advisor/ai/memory/?since=${encodeURIComponent(since)}`
      );
      if (res.ok && ((await res.json()).items || []).length > 0) {
        window.AIMemChip.show();
        return;
      }
    } catch (_e) {
      // memory is best-effort: a failed poll just means no chip
    }
    if (polls < window.AIMemChip.MAX_POLLS)
      window.AIMemChip.timer = setTimeout(tick, window.AIMemChip.POLL_MS);
  };
  window.AIMemChip.timer = setTimeout(tick, window.AIMemChip.POLL_MS);
};
