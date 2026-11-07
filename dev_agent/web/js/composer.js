import { bytes, el } from "./dom.js";
import { icon } from "./icons.js";

const FILE_CAP = 40000; // characters per text file the engine sends in full (engine.attachments.FILE_CAP)

// The chat box: attach file / image, the model name (click to choose), Send, and Stop (active only while a task runs).
export function createComposer(store, transport, picker, report) {
  let chips = [];
  let problems = [];
  const text = el("textarea", {
    rows: 1,
    id: "goal",
    placeholder: "Describe a task for the agent…",
    "aria-label": "Task",
  });
  const chipBox = el("div", { class: "chips" });
  const hint = el("div", { class: "hint muted" });
  const ib = (name, title, onclick, extra = {}) =>
    el(
      "button",
      { type: "button", class: "icon", title, "aria-label": title, onclick, ...extra },
      icon(name)
    );
  const file = ib("paperclip", "Attach file", () => attach("file"), { id: "attach-file" });
  const image = ib("image", "Attach image", () => attach("image"), { id: "attach-image" });
  const chipLabel = el("span");
  const chip = el(
    "button",
    {
      type: "button",
      class: "model-chip",
      id: "model-chip",
      title: "Choose provider and model",
      onclick: () => picker.toggle(),
    },
    chipLabel,
    icon("chevron")
  );
  const send = el(
    "button",
    {
      type: "button",
      class: "send primary",
      id: "send-btn",
      title: "Send",
      "aria-label": "Send",
      onclick: () => submit(),
    },
    icon("send")
  );
  const stop = el(
    "button",
    {
      type: "button",
      class: "stop",
      id: "stop-btn",
      title: "Stop",
      "aria-label": "Stop",
      onclick: () => store.stopRun().catch(report),
    },
    icon("stop")
  );

  async function attach(kind) {
    try {
      const found = await transport.attach(kind);
      chips = chips.concat(found.chips);
      problems = found.rejected || [];
    } catch (error) {
      report(error);
    }
    update();
  }

  async function submit() {
    const goal = text.value.trim();
    if (!ready(goal)) return;
    try {
      await store.submit(goal);
      text.value = "";
      chips = [];
      problems = [];
      grow();
    } catch (error) {
      report(error);
    }
    update();
  }

  const s = () => store.s;
  const imagesBlocked = () => chips.some((c) => c.kind === "image") && !s().server.vision;
  const offline = () => Boolean(s().error && s().error.code === "offline");
  const ready = (goal) => Boolean(goal) && !s().server.busy && !offline() && !imagesBlocked();

  function grow() {
    text.style.height = "auto";
    text.style.height = `${Math.min(text.scrollHeight, 180)}px`;
  }

  function update() {
    const { server, override } = s();
    const now = override || server;
    chipLabel.textContent = `${now.provider || "provider"} · ${now.model || "choose a model"}${override ? " (next task)" : ""}`;
    send.disabled = !ready(text.value.trim());
    send.title = server.busy ? "A task is running" : "Send";
    stop.disabled = !server.busy;
    image.disabled = !server.vision;
    image.title = server.vision
      ? "Attach image"
      : `Images need a vision model: ${server.vision_note || "this model does not accept images"}`;
    chipBox.replaceChildren(
      ...chips.map((c) =>
        el(
          "span",
          {
            class: `chip${c.kind === "image" && !server.vision ? " problem" : ""}`,
            "data-chip": c.id,
          },
          icon(c.kind === "image" ? "image" : "paperclip"),
          el("span", { class: "name", title: c.name, text: `${c.name} · ${bytes(c.size)}` }),
          el(
            "button",
            {
              type: "button",
              class: "icon",
              title: `Remove ${c.name}`,
              "aria-label": `Remove ${c.name}`,
              onclick: () => remove(c.id),
            },
            icon("x")
          )
        )
      )
    );
    const notes = problems.map((p) => `${p.name}: ${p.reason}`);
    if (imagesBlocked())
      notes.push("Images need a vision model: remove the image or choose another model.");
    for (const c of chips)
      if (c.kind === "file" && c.chars > FILE_CAP)
        notes.push(
          `${c.name} is large: only its start and end (${FILE_CAP.toLocaleString()} characters) will be sent, marked as an excerpt.`
        );
    hint.textContent = notes.join(" ");
    hint.className = `hint ${notes.length ? "warn" : "muted"}`;
  }

  function remove(id) {
    chips = chips.filter((c) => c.id !== id);
    transport.detach(id);
    update();
  }

  text.addEventListener("input", () => (grow(), update()));
  text.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      submit();
    }
  });
  const root = el(
    "div",
    { class: "composer" },
    picker.root,
    el(
      "div",
      { class: "composer-box" },
      chipBox,
      text,
      el("div", { class: "bar" }, file, image, chip, el("span", { class: "spacer" }), send, stop)
    ),
    hint
  );
  return { root, update, focus: () => text.focus() };
}
