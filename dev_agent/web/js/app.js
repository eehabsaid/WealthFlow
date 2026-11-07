import { createComposer } from "./composer.js";
import { clear, el } from "./dom.js";
import { renderHistory } from "./history.js";
import { icon } from "./icons.js";
import { createPicker } from "./picker.js";
import { openSettings } from "./settings.js";
import { createStore } from "./store.js";
import { renderThread } from "./thread.js";

// The chat UI. The same code runs as the standalone Web UI and inside the VS Code sidebar; `transport` is the only thing that differs.
export function init(transport, root) {
  const store = createStore(transport);
  const ui = { open: new Map() };
  let notice = "";
  let noticeTimer = null;

  const ib = (name, title, onclick, extra = {}) =>
    el(
      "button",
      { type: "button", class: "icon", title, "aria-label": title, onclick, ...extra },
      icon(name)
    );
  const dot = el("span", { class: "dot", id: "server-dot" });
  const bannerText = el("span", { id: "banner-text" });
  const bannerExtra = el("span");
  const banner = el(
    "div",
    { class: "banner", id: "banner", role: "alert", hidden: true },
    bannerText,
    bannerExtra,
    ib("x", "Dismiss", () => ((notice = ""), schedule()))
  );
  const thread = el("div", { class: "thread" });
  const main = el("div", { class: "main" }, thread);
  const list = el("div", { class: "list" });
  const dialog = el("dialog", { id: "dialog" });
  const drawer = el(
    "div",
    { class: "drawer", id: "history", hidden: true },
    el(
      "div",
      { class: "head" },
      el("h1", { text: "History" }),
      ib("x", "Close history", () => toggleHistory(false))
    ),
    list
  );

  function report(error) {
    notice = error && error.message ? error.message : String(error);
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => ((notice = ""), schedule()), 15000);
    schedule();
  }

  const guard = (work) => async () => {
    try {
      await work();
    } catch (error) {
      report(error);
    }
  };
  const id = () => store.s.taskId;
  const actions = {
    approve: guard(() => store.approve(id())),
    reject: guard(() => store.reject(id())),
    resume: guard(() => store.resume(id())),
    answer: (aid, approve) => guard(() => store.answer(aid, approve))(),
    report: guard(showReport),
  };

  async function showReport() {
    if (transport.openReport) return transport.openReport(id());
    const text = await transport.request("GET", `/api/tasks/${id()}/report`);
    clear(dialog).append(
      el(
        "form",
        { method: "dialog" },
        el("pre", { class: "wrap", text }),
        el("div", { class: "row" }, el("button", { text: "Close" }))
      )
    );
    dialog.showModal();
  }

  const keys = (provider) =>
    transport.keysInPage
      ? openSettings(dialog, transport, report, provider)
      : guard(() => transport.setApiKey(provider))();
  const picker = createPicker(store, transport, report, keys);
  const composer = createComposer(store, transport, picker, report);

  function toggleHistory(show = drawer.hidden) {
    drawer.hidden = !show;
    if (show) renderHistory(list, store, open);
  }

  async function open(taskId) {
    toggleHistory(false);
    await store.open(taskId);
  }

  const head = el(
    "div",
    { class: "head" },
    dot,
    el("h1", { text: "Dev Agent" }),
    ib("plus", "New chat", () => (store.newChat(), composer.focus()), { id: "new-chat" }),
    ib("history", "History", () => toggleHistory(), { id: "history-btn" }),
    ib(
      "sliders",
      "Settings",
      () =>
        transport.keysInPage
          ? openSettings(dialog, transport, report)
          : guard(() => transport.menu())(),
      { id: "settings-btn" }
    )
  );

  function paintBanner() {
    const { error, server } = store.s;
    const offline = error && error.code === "offline";
    const text =
      notice ||
      (error
        ? error.status === 401
          ? "Access token missing or wrong. Open the address printed by “python -m dev_agent serve” again."
          : error.message
        : "");
    banner.hidden = !text;
    bannerText.textContent = text;
    clear(bannerExtra);
    if (offline && transport.restart)
      bannerExtra.append(
        el("button", {
          type: "button",
          "data-act": "restart",
          onclick: guard(() => transport.restart()),
          text: "Restart server",
        })
      );
    dot.className = `dot ${error && !notice ? "off" : server.busy ? "busy" : "on"}`;
    dot.title = error
      ? "Agent server not reachable"
      : server.busy
        ? `Working: ${server.current ? server.current.phase : ""}`
        : "Agent server ready";
  }

  function paint() {
    paintBanner();
    const stick = main.scrollHeight - main.scrollTop - main.clientHeight < 80;
    const top = main.scrollTop;
    renderThread(thread, store, ui, transport, actions, report);
    main.scrollTop = stick ? main.scrollHeight : top;
    composer.update();
    if (!drawer.hidden) renderHistory(list, store, open);
  }

  let queued = false;
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => ((queued = false), paint()));
  }

  root.append(head, banner, main, composer.root, drawer, dialog);
  store.on(schedule);
  store.start();
  paint();
  return store;
}
