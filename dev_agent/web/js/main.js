import { ApiError, get, loadToken, post, stream } from "./api.js";
import { renderApprovals } from "./approvals.js";
import { clear, el } from "./dom.js";
import { renderFiles } from "./files.js";
import { renderPlan } from "./plan.js";
import { openSettings } from "./settings.js";
import { renderTasks } from "./tasklist.js";
import { row } from "./timeline.js";

const $ = (id) => document.getElementById(id);
const app = {
  selected: "",
  stopStream: null,
  timer: null,
  state: { busy: false, approvals: [] },
};

function banner(text) {
  $("banner").hidden = !text;
  $("banner").textContent = text || "";
}

async function guarded(work) {
  try {
    await work();
    banner("");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401)
      banner(
        'Access token missing or wrong. Open the address printed by "python -m dev_agent serve" again.',
      );
    else banner(error.message);
  }
}

async function refreshTask() {
  if (!app.selected) return;
  const id = app.selected;
  const task = await get(`/api/tasks/${id}`);
  if (id !== app.selected) return;
  const detail = $("detail");
  const log = detail.querySelector(".timeline");
  const keep = log ? log.cloneNode(true) : null;
  const files = el("div", { class: "files-box" });
  const actions = {
    approve: () =>
      guarded(async () => {
        await post(`/api/tasks/${id}/approve`);
        poll();
      }),
    reject: () =>
      guarded(async () => {
        await post(`/api/tasks/${id}/reject`);
        poll();
      }),
    resume: () =>
      guarded(async () => {
        await post(`/api/tasks/${id}/resume`);
        poll();
      }),
  };
  clear(detail).append(
    el("h2", { text: task.goal, class: "goal-title" }),
    el(
      "p",
      {},
      el("span", { class: `pill s-${task.status}`, text: task.status }),
      task.stop_reason
        ? el("span", { class: "muted", text: `  ${task.stop_reason}` })
        : null,
    ),
    task.answer
      ? el(
          "section",
          { class: "card" },
          el("h3", { text: "Answer" }),
          el("pre", { class: "wrap", text: task.answer }),
        )
      : null,
    renderPlan(task, actions),
    el(
      "section",
      { class: "card" },
      el("h3", { text: "Progress" }),
      keep || el("ul", { class: "timeline" }),
    ),
    el(
      "section",
      { class: "card" },
      el("h3", { text: "Changed files" }),
      files,
    ),
    el(
      "div",
      { class: "row" },
      el("a", {
        class: "link",
        href: "#",
        onclick: (e) => {
          e.preventDefault();
          showReport(id);
        },
        text: "Show report",
      }),
    ),
  );
  renderFiles(files, id).catch((error) =>
    files.append(el("p", { class: "bad", text: error.message })),
  );
}

async function showReport(id) {
  const text = await get(`/api/tasks/${id}/report`);
  const box = el("pre", { class: "wrap card", text });
  $("detail").append(box);
  box.scrollIntoView();
}

function select(id) {
  if (app.stopStream) app.stopStream();
  app.selected = id;
  clear($("detail")).append(el("ul", { class: "timeline" }));
  let pending = null;
  app.stopStream = stream(id, 0, (event) => {
    const li = row(event);
    const list = $("detail").querySelector(".timeline");
    if (li && list) list.append(li);
    if (["status", "done", "package", "verify", "phase"].includes(event.type)) {
      clearTimeout(pending);
      pending = setTimeout(() => guarded(refreshTask), 250);
    }
    if (event.type === "done" || event.type === "status") setTimeout(poll, 400);
  });
  guarded(refreshTask);
  poll();
}

async function poll() {
  await guarded(async () => {
    const [state, list] = await Promise.all([
      get("/api/state"),
      get("/api/tasks"),
    ]);
    app.state = state;
    $("run-state").textContent = state.busy
      ? `working: ${state.current ? state.current.phase || "running" : ""}`
      : "idle";
    $("run-state").className = `pill ${state.busy ? "s-executing" : ""}`;
    $("stop-btn").disabled = !state.busy;
    $("start-btn").disabled = state.busy;
    renderApprovals($("approvals"), state.approvals, poll);
    renderTasks($("task-list"), list.tasks, app.selected, select);
  });
}

function wire() {
  $("stop-btn").addEventListener("click", () =>
    guarded(async () => {
      await post("/api/stop");
      poll();
    }),
  );
  $("settings-btn").addEventListener("click", () =>
    guarded(() => openSettings($("settings-dialog"))),
  );
  $("new-task").addEventListener("submit", (event) => {
    event.preventDefault();
    const goal = $("goal").value.trim();
    if (!goal) return;
    guarded(async () => {
      const { id } = await post("/api/tasks", { goal });
      $("goal").value = "";
      select(id);
    });
  });
}

if (!loadToken()) {
  banner(
    'No access token. Open the address printed by "python -m dev_agent serve" (it ends with #token=...).',
  );
} else {
  wire();
  poll();
  app.timer = setInterval(poll, 2500);
}
