import { clear, el } from "./dom.js";

const GROUPS = { context: "Context", limits: "Limits", time: "Timeouts" };
const num = (v) => Number(v).toLocaleString("en-US");

// Pure: the rows of the "what changed" list for a PUT /api/settings/context answer.
export function changeLines(result) {
  const lines = result.changed.map((c) => {
    const moved = `${c.label}: ${num(c.old)} → ${num(c.new)}`;
    return c.clamped
      ? `${moved} (you asked for ${c.requested === undefined ? "a smaller window" : num(c.requested)}; kept within limits: ${c.note})`
      : moved;
  });
  const held = result.unchanged.filter((c) => c.clamped);
  return lines.concat(held.map((c) => `${c.label}: stays ${num(c.new)} (${c.note})`));
}

// Pure: only the fields whose input differs from what is saved, as numbers; null when one input is not a number.
export function pendingValues(rows) {
  const values = {};
  for (const { spec, input } of rows) {
    const text = input.value.trim().replace(/,/g, "");
    if (text === "" || !Number.isFinite(Number(text))) return null;
    if (Number(text) !== spec.value) values[spec.key] = Number(text);
  }
  return values;
}

// "Context & limits": every context-related value of the agent (coding_agent/agent_settings.json). The server validates, clamps and writes the
// file; this dialog shows exactly what it saved. Works in the Web UI and in the VS Code webview (same file, same endpoints).
export async function openContextSettings(dialog, transport, report) {
  const loaded = await transport.request("GET", "/api/settings/context");
  const rows = [];
  const message = el("p", { class: "muted", role: "status" });
  const changes = el("ul", { class: "changes", "aria-live": "polite" });
  const warnings = el("ul", { class: "warnings", role: "note" });
  const showWarnings = (list) => (
    clear(warnings),
    warnings.append(...list.map((text) => el("li", { text })))
  );
  showWarnings(loaded.warnings || []);
  const say = (text, bad = false) => (
    (message.textContent = text),
    (message.className = bad ? "bad" : "muted")
  );

  const field = (spec) => {
    const input = el("input", {
      id: `ctx-${spec.key}`,
      type: "number",
      inputmode: "numeric",
      min: spec.min,
      max: spec.max,
      step: 1,
      value: spec.value,
    });
    const row = { spec, input };
    rows.push(row);
    const reset = el("button", {
      type: "button",
      class: "link",
      "data-reset": spec.key,
      onclick: () => (input.value = spec.default),
      text: `default ${num(spec.default)}`,
    });
    return el(
      "div",
      { class: "ctx-field" },
      el("label", { for: input.id, text: `${spec.label} (${spec.unit})` }),
      input,
      el("div", { class: "muted" }, `${num(spec.min)} – ${num(spec.max)} · `, reset),
      el("div", { class: "muted help", text: spec.help })
    );
  };
  const groups = Object.entries(GROUPS).map(([group, title]) =>
    el(
      "fieldset",
      {},
      el("legend", { text: title }),
      loaded.values.filter((s) => s.group === group).map(field)
    )
  );

  async function save() {
    clear(changes);
    const values = pendingValues(rows);
    if (!values) return say("Every field needs a number.", true);
    if (!Object.keys(values).length) return say("Nothing changed.");
    try {
      const result = await transport.request("PUT", "/api/settings/context", { values });
      result.values.forEach((spec) => {
        const row = rows.find((r) => r.spec.key === spec.key);
        row.spec = spec;
        row.input.value = spec.value;
      });
      changes.append(...changeLines(result).map((text) => el("li", { text })));
      showWarnings(result.warnings || []);
      say(`Saved to ${result.file}. It applies ${result.applies}.`);
    } catch (error) {
      say(error.message, true);
    }
  }

  clear(dialog).append(
    el(
      "form",
      { method: "dialog", class: "settings ctx-settings" },
      el("h3", { text: "Context & limits" }),
      el("p", { class: "muted", text: `Saved in ${loaded.file}; it applies ${loaded.applies}.` }),
      warnings,
      groups,
      changes,
      message,
      el(
        "div",
        { class: "row" },
        el("button", {
          type: "button",
          class: "primary",
          id: "ctx-save",
          onclick: save,
          text: "Save",
        }),
        el("button", { value: "close", text: "Close" })
      )
    )
  );
  dialog.showModal();
  if (report) dialog.addEventListener("close", () => report(""), { once: true });
}
