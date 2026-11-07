import { el } from "./dom.js";

// One readable row per engine event. Raw model text is never shown here, only the engine's own short summaries.
function describe(event) {
  switch (event.type) {
    case "phase":
      return ["phase", `Phase: ${event.phase || event.name || ""}`];
    case "package":
      return [
        "package",
        `Package ${event.id}: ${event.title || ""} (${event.status})`,
      ];
    case "tool":
      return [
        event.ok ? "tool" : "bad",
        `${event.ok ? "ok" : "ERR"} ${event.name}${event.summary ? ` - ${event.summary}` : ""}`,
      ];
    case "command":
      return [
        event.status === "PASSED" ? "tool" : "bad",
        `ran ${event.command} -> ${event.status}${event.duration_s !== undefined ? ` (${event.duration_s}s)` : ""}`,
      ];
    case "verify":
      return [
        event.overall === "VERIFIED" ? "tool" : "bad",
        `Checks (${event.label}): ${event.overall}`,
      ];
    case "status":
      return [
        "phase",
        `Status: ${event.status}${event.reason ? ` - ${event.reason}` : ""}`,
      ];
    case "approval_request":
      return ["warn", `Approval needed: ${event.message}`];
    case "approval_result":
      return ["phase", `Approval ${event.approved ? "granted" : "denied"}`];
    case "invalid_reply":
      return ["bad", "The model sent a reply that was not valid protocol JSON"];
    case "error":
      return ["bad", `Error: ${event.message || ""}`];
    case "done":
      return ["phase", `Finished: ${event.status || ""}`];
    default:
      return null;
  }
}

export function row(event) {
  const found = describe(event);
  if (!found) return null;
  return el(
    "li",
    { class: `ev ${found[0]}`, "data-seq": event.seq },
    el("span", { class: "seq", text: String(event.seq) }),
    el("span", { text: found[1] }),
  );
}
