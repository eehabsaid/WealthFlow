import { clear, el } from "./dom.js";

const PROVIDERS = ["ollama", "anthropic", "openai", "gemini"];

// Web UI only: provider, model and API keys. A key goes from this page straight to the local server and into the OS keyring; it is never shown
// again. (The VS Code view never has a key field: the extension asks for keys with its own native input box.)
export async function openSettings(dialog, transport, report, focus) {
  const get = (path) => transport.request("GET", path);
  const [settings, keys] = await Promise.all([get("/api/settings"), get("/api/keys")]);
  const provider = el(
    "select",
    { id: "s-provider" },
    PROVIDERS.map((p) =>
      el("option", { value: p, text: p, selected: p === (focus || settings.provider) })
    )
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
  const message = el("p", { class: "muted", role: "status" });
  const keyState = el("div", { class: "muted" });
  const note = (text, bad = false) => (
    (message.textContent = text),
    (message.className = bad ? "bad" : "muted")
  );
  const showKey = () =>
    (keyState.textContent = `key for ${provider.value}: ${{ true: "stored", false: "not stored", null: "locked" }[keys.keys[provider.value]]} (${keys.backend})`);
  const run = (work) => async () => {
    try {
      await work();
    } catch (error) {
      note(error.message, true);
    }
  };
  provider.addEventListener("change", showKey);
  const list = run(async () => {
    const found = await get(`/api/models?provider=${provider.value}`);
    models.replaceChildren(...found.models.map((m) => el("option", { value: m })));
    note(
      found.models.length ? `${found.models.length} models found` : found.note || "no models found"
    );
  });
  const save = run(async () => {
    await transport.request("PUT", "/api/settings", {
      values: { provider: provider.value, model: model.value.trim() },
    });
    if (phrase.value)
      await transport.request("POST", "/api/keys/unlock", { passphrase: phrase.value });
    if (key.value)
      await transport.request("PUT", `/api/keys/${provider.value}`, { value: key.value });
    key.value = phrase.value = "";
    Object.assign(keys, await get("/api/keys"));
    showKey();
    note("Saved.");
  });
  const remove = run(async () => {
    await transport.request("DELETE", `/api/keys/${provider.value}`);
    Object.assign(keys, await get("/api/keys"));
    showKey();
    note("Key removed.");
  });
  showKey();
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
      el("button", { type: "button", onclick: list, text: "List models" }),
      el("label", { for: "s-key", text: "API key" }),
      key,
      keyState,
      el("label", { for: "s-phrase", text: "Passphrase (only if the OS keyring is unavailable)" }),
      phrase,
      message,
      el(
        "div",
        { class: "row" },
        el("button", { type: "button", class: "primary", onclick: save, text: "Save" }),
        el("button", { type: "button", onclick: remove, text: "Remove key" }),
        el("button", { value: "close", text: "Close" })
      )
    )
  );
  dialog.showModal();
  if (report) dialog.addEventListener("close", () => report(""), { once: true });
}
