import { card } from "./card.js";
import { el } from "./dom.js";
import { icon } from "./icons.js";

function list(label, items, cls = "") {
  if (!items || !items.length) return null;
  return el(
    "div",
    { class: "group" },
    el("h4", { text: `${label} (${items.length})` }),
    el(
      "ul",
      { class: cls },
      items.map((i) => el("li", { text: i }))
    )
  );
}

function stepIcon(status) {
  if (status === "done") return el("span", { class: "good" }, icon("check"));
  if (status === "running") return icon("spinner");
  if (status === "stopped") return el("span", { class: "bad" }, icon("x"));
  return el("span", { class: "muted" }, icon("circle"));
}

// The plan the owner approves once. Steps show live progress through their work package.
export function planCard(ui, task, actions) {
  const plan = task.plan;
  const state = {};
  for (const pkg of task.packages || []) for (const id of pkg.steps) state[id] = pkg.status;
  const waiting = task.status === "awaiting_approval";
  const renames = (plan.files_rename || []).map((r) => `${r.from} → ${r.to}`);
  const buttons = [];
  if (waiting)
    buttons.push(
      el("button", {
        type: "button",
        class: "primary",
        "data-act": "approve",
        onclick: actions.approve,
        text: "Approve",
      }),
      el("button", {
        type: "button",
        "data-act": "reject",
        onclick: actions.reject,
        text: "Reject",
      })
    );
  if (task.status === "stopped" && task.approved_at)
    buttons.push(
      el("button", {
        type: "button",
        class: "primary",
        "data-act": "resume",
        onclick: actions.resume,
        text: "Resume",
      })
    );
  const body = [
    el("p", { text: plan.summary }),
    el(
      "ul",
      { class: "steps" },
      plan.steps.map((s) =>
        el(
          "li",
          {},
          stepIcon(state[s.id]),
          el(
            "span",
            {},
            el("span", { text: s.title }),
            s.files && s.files.length
              ? el("div", { class: "files", text: s.files.join(", ") })
              : null
          )
        )
      )
    ),
    list("Add", plan.files_add),
    list("Edit", plan.files_edit),
    list("DELETE", plan.files_delete, "danger"),
    list("RENAME", renames, "danger"),
    list("Protected: will ask you first", plan.needs_owner_approval, "danger"),
    list("Tests", plan.tests),
    list("Risks", plan.risks),
    buttons.length ? el("div", { class: "actions" }, buttons) : null,
  ];
  const title = waiting ? "Plan ready" : task.approved_at ? "Plan approved" : "Plan";
  return card(ui, {
    key: "plan",
    cls: waiting ? "attention" : "",
    iconName: waiting ? "alert" : "check",
    iconCls: waiting ? "warn" : "good",
    title,
    sub: `${plan.steps.length} step${plan.steps.length === 1 ? "" : "s"}`,
    body,
    open: waiting,
  });
}
