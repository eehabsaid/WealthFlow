import { post } from "./api.js";
import { clear, el } from "./dom.js";

// Pending approvals from the engine (protected files, commands that need the owner). The first answer wins, from any interface.
export function renderApprovals(box, pending, onAnswered) {
  const key = pending.map((p) => p.id).join(",");
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  clear(box);
  for (const item of pending) {
    const answer = async (approve) => {
      try {
        await post(`/api/approvals/${item.id}`, { approve });
      } finally {
        onAnswered();
      }
    };
    box.append(
      el(
        "section",
        { class: "card approval" },
        el("h3", { text: `Approval needed (${item.kind})` }),
        el("pre", { class: "wrap", text: item.message }),
        el(
          "div",
          { class: "row" },
          el("button", {
            type: "button",
            class: "primary",
            onclick: () => answer(true),
            text: "Approve",
          }),
          el("button", {
            type: "button",
            class: "danger",
            onclick: () => answer(false),
            text: "Deny",
          }),
        ),
      ),
    );
  }
}
