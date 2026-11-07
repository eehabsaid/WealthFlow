import { card } from "./card.js";
import { clock, el } from "./dom.js";

// How the task ended. The honest wording comes from the engine: VERIFIED only when every applicable check ran and passed.
export function finalCard(ui, task, lastVerify, actions) {
  const clk = clock(task.updated);
  const stamp = el("span", { class: "stamp", text: clk });
  const report = el("button", {
    type: "button",
    class: "link",
    "data-act": "report",
    onclick: actions.report,
    text: "Show full report",
  });
  const checks = lastVerify ? `Checks: ${lastVerify.overall}` : "No checks ran";
  const summary = (task.agent_summaries || [])
    .filter((s) => !s.fix)
    .map((s) => s.text)
    .join("\n");
  if (task.status === "answered")
    return card(ui, {
      key: "final",
      cls: "final",
      iconName: "check",
      iconCls: "good",
      title: "Answer",
      right: stamp,
      body: el("pre", { class: "wrap", text: task.answer || "" }),
      open: true,
    });
  if (task.status === "completed")
    return card(ui, {
      key: "final",
      cls: `final ${lastVerify && lastVerify.overall === "VERIFIED" ? "ok" : "attention"}`,
      iconName: "check",
      iconCls: "good",
      title: "Task completed",
      sub: checks,
      right: stamp,
      body: [el("pre", { class: "wrap", text: summary || "Done." }), report],
      open: true,
    });
  if (task.status === "rejected")
    return card(ui, {
      key: "final",
      cls: "final",
      iconName: "x",
      iconCls: "muted",
      title: "Plan rejected",
      sub: "nothing was changed",
      right: stamp,
      body: el("p", { text: task.stop_reason }),
      open: false,
    });
  if (task.status === "stopped")
    return card(ui, {
      key: "final",
      cls: "final bad",
      iconName: "alert",
      iconCls: "bad",
      title: "Task stopped",
      sub: task.stop_reason,
      right: stamp,
      body: [el("pre", { class: "wrap", text: task.stop_reason || "Stopped." }), report],
      open: true,
    });
  return null;
}
