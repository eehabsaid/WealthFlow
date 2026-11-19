import { clear, el } from "./dom.js";

const GROUPS = {
  approvals: ["Approvals", "On = the agent asks you first. Off = it goes ahead on its own. Secret files, git writes, migrations and destructive commands stay blocked or asked either way."],
  speed: ["Speed and flexibility", "Make small tasks faster."],
};

// Pure: the one-line answer shown after a switch was saved.
export function savedLine(result) {
  const c = result.changed[0];
  return c ? `${c.label}: ${c.new ? "on" : "off"}. Saved in ${result.file}; it applies ${result.applies}.` : "Nothing changed.";
}

// "Behavior": the on/off switches of coding_agent/agent_settings.json (approvals, deep search, quick mode, lighter verification). A switch is saved as soon as
// you click it. Works in the Web UI and in the VS Code webview (same endpoints).
export async function openBehaviorSettings(dialog, transport, report) {
  const loaded = await transport.request("GET", "/api/settings/behavior");
  const message = el("p", { class: "muted", role: "status" });
  const say = (text, bad = false) => ((message.textContent = text), (message.className = bad ? "bad" : "muted"));

  const row = (spec) => {
    const box = el("input", { type: "checkbox", id: `bh-${spec.key}`, checked: spec.value, "data-key": spec.key });
    box.addEventListener("change", async () => {
      try {
        const result = await transport.request("PUT", "/api/settings/behavior", { values: { [spec.key]: box.checked } });
        say(savedLine(result));
      } catch (error) {
        box.checked = !box.checked;
        say(error.message, true);
      }
    });
    return el(
      "div",
      { class: "ctx-field switch" },
      el("label", { for: box.id }, box, ` ${spec.label}`),
      el("div", { class: "muted help", text: spec.help })
    );
  };

  const groups = Object.entries(GROUPS).map(([group, [title, intro]]) =>
    el("fieldset", {}, el("legend", { text: title }), el("p", { class: "muted help", text: intro }), loaded.values.filter((s) => s.group === group).map(row))
  );
  clear(dialog).append(
    el(
      "form",
      { method: "dialog", class: "settings ctx-settings behavior-settings" },
      el("h3", { text: "Behavior" }),
      el("p", { class: "muted", text: `Saved in ${loaded.file}; it applies ${loaded.applies}.` }),
      groups,
      message,
      el("div", { class: "row" }, el("button", { value: "close", text: "Close" }))
    )
  );
  dialog.showModal();
  if (report) dialog.addEventListener("close", () => report(""), { once: true });
}
