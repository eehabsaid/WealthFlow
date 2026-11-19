import { clear, el } from "./dom.js";
import { filesCard } from "./files-card.js";
import { finalCard } from "./final-card.js";
import { icon } from "./icons.js";
import { planCard } from "./plan-card.js";
import { approvalCard, errorCard, verifyCard, workCard } from "./run-cards.js";
import { buildGroups } from "./timeline.js";

const msg = (kind, ...kids) =>
  el(
    "div",
    { class: `msg ${kind}` },
    el(
      "span",
      { class: `avatar ${kind === "bot" ? "bot" : ""}` },
      icon(kind === "bot" ? "bot" : "user")
    ),
    el("div", { class: "body" }, kids)
  );

function empty() {
  return el(
    "div",
    { class: "empty" },
    icon("bot"),
    el("h2", { text: "What should I work on?" }),
    el("p", {
      text: "Describe a task. I will read the project, show you a plan to approve once, then make the changes and run the checks.",
    })
  );
}

function userMessage(task) {
  const chips = (task.attachments || []).map((a) =>
    el(
      "span",
      {
        class: `chip${a.omitted ? " problem" : ""}`,
        title: a.omitted
          ? `Only an excerpt was sent: ${a.omitted} of ${a.chars} characters omitted`
          : a.name,
      },
      icon(a.kind === "image" ? "image" : "paperclip"),
      el("span", { class: "name", text: a.name + (a.omitted ? " (excerpt)" : "") })
    )
  );
  return msg(
    "user",
    el("div", { class: "bubble", text: task.goal }),
    chips.length ? el("div", { class: "chips" }, chips) : null
  );
}

// The tasks that came before the open one in the same chat (oldest first), as a short row each; click one to open it in full.
function earlierTasks(s, task, actions) {
  const chat = task.chat_id || task.id;
  return s.tasks
    .filter((t) => (t.chat || t.id) === chat && t.id < task.id)
    .slice(0, 5)
    .reverse()
    .flatMap((t) => [
      msg("user", el("div", { class: "bubble", text: t.goal })),
      msg(
        "bot",
        el(
          "button",
          { type: "button", class: "task-row", onclick: () => actions.open(t.id) },
          el("span", { class: `pill s-${t.status}`, text: t.status }),
          el("span", { class: "goal", text: t.stop_reason || "Open this task" })
        )
      ),
    ]);
}

// The whole conversation for the open task, rebuilt from the store on every change. Open/closed state of cards lives in `ui.open`.
export function renderThread(root, store, ui, transport, actions, onError) {
  const { s } = store;
  clear(root);
  if (!s.taskId) return root.append(empty());
  const task = s.task;
  if (!task) return root.append(el("p", { class: "muted", text: "Loading…" }));
  const here = s.server.busy && s.server.current && s.server.current.id === task.id;
  const groups = buildGroups(s.events, here);
  const out = [];
  const worth = (g) => g.kind !== "work" || g.rows.length > 0 || g.status === "running"; // no empty "0 steps" cards
  const investigation = groups.find((g) => g.key === "plan" && worth(g));
  if (investigation) out.push(workCard(ui, investigation));
  if (task.plan) out.push(planCard(ui, task, actions));
  for (const g of groups) {
    if (g.key === "plan" || !worth(g)) continue;
    out.push(
      g.kind === "work"
        ? workCard(ui, g)
        : g.kind === "verify"
          ? verifyCard(ui, g)
          : errorCard(ui, g)
    );
  }
  if (s.files.length) out.push(filesCard(ui, task, s.files, transport, onError));
  const lastVerify = [...groups].reverse().find((g) => g.kind === "verify");
  const end = finalCard(ui, task, lastVerify, actions);
  if (end) out.push(end);
  const pending = here ? s.server.approvals : [];
  for (const a of pending) out.push(approvalCard(ui, a, actions));
  if (here && !pending.length)
    out.push(
      el(
        "div",
        { class: "thinking" },
        icon("spinner"),
        el("span", { text: s.server.current.phase || "working" })
      )
    );
  else if (!here && ["planning", "executing", "approved"].includes(task.status))
    out.push(
      el("p", {
        class: "note",
        text: `This task is not running right now (status: ${task.status}).${task.approved_at ? " Use Resume on the plan." : ""}`,
      })
    );
  const note = task.model_override
    ? el("div", {
        class: "note",
        text: `Model for this task: ${task.model_override.provider || ""} ${task.model_override.model || ""}`.trim(),
      })
    : null;
  const waiting =
    task.status === "queued"
      ? el("p", { class: "note", text: "Queued: this follow-up starts when the running task finishes." })
      : null;
  root.append(...earlierTasks(s, task, actions), userMessage(task), msg("bot", note, waiting, out));
}
