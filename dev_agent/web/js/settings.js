import { get, post, request } from "./api.js";
import { clear, el } from "./dom.js";

const PROVIDERS = ["ollama", "anthropic", "openai", "gemini"];

export async function openSettings(dialog) {
  const [settings, keys] = await Promise.all([
    get("/api/settings"),
    get("/api/keys"),
  ]);
  const message = el("p", { class: "muted", role: "status" });
  const provider = el(
    "select",
    { id: "s-provider" },
    PROVIDERS.map((p) =>
      el("option", { value: p, text: p, selected: p === settings.provider }),
    ),
  );
  const model = el("input", {
    id: "s-model",
    type: "text",
    value: settings.model,
    list: "model-list",
    autocomplete: "off",
  });
  const models = el("datalist", { id: "model-list" });
  const key = el("input", {
    id: "s-key",
    type: "password",
    autocomplete: "off",
    placeholder: "paste a new API key (never shown again)",
  });
  const phrase = el("input", {
    id: "s-phrase",
    type: "password",
    autocomplete: "off",
    placeholder: "passphrase for the encrypted key file",
  });
  const note = (text, bad = false) => {
    message.textContent = text;
    message.className = bad ? "bad" : "muted";
  };
  const status = () =>
    el("span", {
      class: "muted",
      text: `key for ${provider.value}: ${{ true: "stored", false: "not stored", null: "locked" }[keys.keys[provider.value]]} (${keys.backend})`,
    });
  const keyState = el("div", {}, status());
  provider.addEventListener("change", () => keyState.replaceChildren(status()));
  const refreshModels = async () => {
    try {
      const found = await get(`/api/models?provider=${provider.value}`);
      models.replaceChildren(
        ...found.models.map((m) => el("option", { value: m })),
      );
      note(
        found.models.length
          ? `${found.models.length} models found`
          : found.note || "no models found",
      );
    } catch (error) {
      note(error.message, true);
    }
  };
  const run = (work) => async () => {
    try {
      await work();
    } catch (error) {
      note(error.message, true);
    }
  };
  const save = run(async () => {
    await request("PUT", "/api/settings", {
      values: { provider: provider.value, model: model.value.trim() },
    });
    if (phrase.value)
      await post("/api/keys/unlock", { passphrase: phrase.value });
    if (key.value)
      await request("PUT", `/api/keys/${provider.value}`, { value: key.value });
    key.value = phrase.value = "";
    Object.assign(keys, await get("/api/keys"));
    keyState.replaceChildren(status());
    note("Saved.");
  });
  const remove = run(async () => {
    await request("DELETE", `/api/keys/${provider.value}`);
    Object.assign(keys, await get("/api/keys"));
    keyState.replaceChildren(status());
    note("Key removed.");
  });
  clear(dialog).append(
    el(
      "form",
      { method: "dialog", class: "settings" },
      el("h3", { text: "Settings" }),
      el("label", { for: "s-provider", text: "Provider" }),
      provider,
      el("label", { for: "s-model", text: "Model" }),
      model,
      models,
      el("button", {
        type: "button",
        onclick: refreshModels,
        text: "List models",
      }),
      el("label", { for: "s-key", text: "API key" }),
      key,
      keyState,
      el("label", {
        for: "s-phrase",
        text: "Passphrase (only if the OS keyring is unavailable)",
      }),
      phrase,
      message,
      el(
        "div",
        { class: "row" },
        el("button", {
          type: "button",
          class: "primary",
          onclick: save,
          text: "Save",
        }),
        el("button", { type: "button", onclick: remove, text: "Remove key" }),
        el("button", { value: "close", text: "Close" }),
      ),
    ),
  );
  dialog.showModal();
}
