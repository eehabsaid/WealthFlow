import { clear, el } from "./dom.js";

const PROVIDERS = ["ollama", "anthropic", "openai", "gemini"];

// Click the model name: choose provider and model. By default the choice is saved in the shared settings (CLI, Web UI and VS Code all use it);
// "only for the next task" keeps the shared settings untouched.
export function createPicker(store, transport, report, onKeys) {
  const root = el("div", {
    class: "picker",
    hidden: true,
    role: "dialog",
    "aria-label": "Choose provider and model",
  });
  let provider = "";
  let model = "";
  let once = false;
  let models = { list: [], note: "" };
  let keys = null;

  async function load() {
    try {
      const found = await transport.request("GET", `/api/models?provider=${provider}`);
      models = { list: found.models || [], note: found.note || "" };
    } catch (error) {
      models = { list: [], note: error.message };
    }
    try {
      keys = (await transport.request("GET", "/api/keys")).keys;
    } catch (_error) {
      keys = null;
    }
    paint();
  }

  function close() {
    root.hidden = true;
  }

  async function apply() {
    model = model.trim();
    if (!model) return;
    try {
      if (once) await store.setOverride({ provider, model });
      else {
        await store.setOverride(null);
        await store.saveModel(provider, model);
      }
      close();
    } catch (error) {
      report(error);
    }
  }

  function paint() {
    const input = el("input", {
      type: "text",
      id: "model-name",
      value: model,
      placeholder: "model name",
      autocomplete: "off",
      "aria-label": "Model name",
    });
    input.addEventListener("input", () => (model = input.value));
    input.addEventListener("keydown", (event) => event.key === "Enter" && apply());
    const keyText = keys
      ? { true: "stored", false: "not stored", null: "locked" }[keys[provider]]
      : "unknown";
    clear(root).append(
      el(
        "div",
        {},
        el("h4", { text: "Provider" }),
        el(
          "div",
          { class: "seg" },
          PROVIDERS.map((p) =>
            el("button", {
              type: "button",
              class: p === provider ? "on" : "",
              "data-provider": p,
              onclick: () => ((provider = p), (model = ""), load()),
              text: p,
            })
          )
        ),
        el("h4", { text: "Model" }),
        input,
        el(
          "div",
          { class: "models" },
          models.list.map((m) =>
            el("button", {
              type: "button",
              class: m === model ? "on" : "",
              "data-model": m,
              onclick: () => ((model = m), paint()),
              text: m,
            })
          )
        ),
        models.note ? el("p", { class: "note", text: models.note }) : null,
        el(
          "p",
          { class: "note" },
          `API key for ${provider}: ${keyText} `,
          el("button", {
            type: "button",
            class: "link",
            "data-act": "key",
            onclick: () => onKeys(provider),
            text: "set or change",
          })
        ),
        el(
          "label",
          { class: "note" },
          el("input", {
            type: "checkbox",
            id: "only-task",
            checked: once,
            onchange: (e) => (once = e.target.checked),
          }),
          " Use only for the next task (do not change the shared settings)"
        ),
        el(
          "div",
          { class: "row" },
          el("button", {
            type: "button",
            class: "primary",
            "data-act": "apply",
            onclick: apply,
            text: "Apply",
          }),
          el("button", { type: "button", onclick: close, text: "Cancel" })
        )
      )
    );
  }

  return {
    root,
    toggle() {
      if (!root.hidden) return close();
      const now = store.s.override || store.s.server;
      provider = now.provider || "ollama";
      model = now.model || "";
      once = Boolean(store.s.override);
      models = { list: [], note: "" };
      root.hidden = false;
      paint();
      load();
    },
    close,
  };
}
