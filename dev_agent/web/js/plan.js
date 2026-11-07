import { el } from "./dom.js";

function fileGroup(label, items, cls = "") {
  if (!items || !items.length) return null;
  return el(
    "div",
    { class: "group" },
    el("h4", { text: `${label} (${items.length})` }),
    el(
      "ul",
      { class: cls },
      items.map((i) => el("li", { text: i })),
    ),
  );
}

export function renderPlan(task, actions) {
  const plan = task.plan;
  if (!plan)
    return el("p", {
      class: "muted",
      text:
        task.status === "planning"
          ? "The agent is reading the project and planning..."
          : "No plan.",
    });
  const renames = (plan.files_rename || []).map((r) => `${r.from} -> ${r.to}`);
  const buttons = [];
  if (task.status === "awaiting_approval") {
    buttons.push(
      el("button", {
        type: "button",
        class: "primary",
        onclick: actions.approve,
        text: "Approve and run",
      }),
      el("button", { type: "button", onclick: actions.reject, text: "Reject" }),
    );
  }
  if (task.status === "stopped" && task.approved_at)
    buttons.push(
      el("button", {
        type: "button",
        class: "primary",
        onclick: actions.resume,
        text: "Resume",
      }),
    );
  return el(
    "section",
    { class: "card" },
    el("h3", { text: "Plan" }),
    el("p", { text: plan.summary }),
    el(
      "ol",
      {},
      plan.steps.map((s) =>
        el(
          "li",
          {},
          el("strong", { text: s.title }),
          s.files && s.files.length
            ? el("span", { class: "muted", text: `  ${s.files.join(", ")}` })
            : null,
        ),
      ),
    ),
    fileGroup("Add", plan.files_add),
    fileGroup("Edit", plan.files_edit),
    fileGroup("DELETE", plan.files_delete, "danger-text"),
    fileGroup("RENAME", renames, "danger-text"),
    fileGroup(
      "Protected: will ask you first",
      plan.needs_owner_approval,
      "danger-text",
    ),
    fileGroup("Tests", plan.tests),
    fileGroup("Risks", plan.risks),
    el("div", { class: "row" }, buttons),
  );
}
