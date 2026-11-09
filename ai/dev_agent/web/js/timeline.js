// Turns the engine's event log into the cards of one run: work groups (investigation, one per work package, final checks), verification
// results and errors. Raw model text is never shown, only the engine's own short summaries.
const pretty = (name) =>
  String(name || "")
    .replace(/_/g, " ")
    .replace(/^./, (c) => c.toUpperCase());

function group(key, title) {
  return { key, kind: "work", title, status: "done", rows: [] };
}

export function buildGroups(events, running) {
  const groups = [];
  let cur = group("plan", "Investigating the project");
  const keep = (g) => groups.includes(g) || groups.push(g);
  for (const e of events) {
    switch (e.type) {
      case "package":
        if (e.status === "running") {
          cur = group(`pkg-${e.id}`, `${e.id} · ${e.title || ""}`);
          keep(cur);
        }
        break;
      case "phase":
        if (e.phase === "final checks") {
          cur = group("final", "Final checks");
          keep(cur);
        }
        break;
      case "tool":
        keep(cur);
        cur.rows.push({
          kind: e.ok ? "tool" : "bad",
          k: pretty(e.name),
          v: e.summary || e.args || "",
        });
        break;
      case "command":
        keep(cur);
        cur.rows.push({
          kind: e.status === "PASSED" ? "cmd" : "bad",
          k: "Command",
          v: `${e.command} → ${e.status}${e.duration_s !== undefined ? ` (${e.duration_s}s)` : ""}`,
        });
        break;
      case "invalid_reply":
        keep(cur);
        cur.rows.push({
          kind: "bad",
          k: "Model reply",
          v: "was not valid protocol JSON; it was asked again",
        });
        break;
      case "approval_result":
        keep(cur);
        cur.rows.push({
          kind: e.approved ? "tool" : "bad",
          k: "Approval",
          v: e.approved ? "granted" : "denied",
        });
        break;
      case "verify":
        keep(cur);
        groups.push({
          key: `verify-${e.seq}`,
          kind: "verify",
          label: e.label,
          overall: e.overall,
          results: e.results || [],
        });
        break;
      case "error":
        groups.push({ key: `error-${e.seq}`, kind: "error", message: e.message || "error" });
        break;
      default:
        break;
    }
  }
  const work = groups.filter((g) => g.kind === "work");
  const last = work[work.length - 1];
  if (last) last.status = running ? "running" : "done";
  else if (running) {
    keep(cur);
    cur.status = "running";
  }
  return groups;
}

export function attachmentEvent(events) {
  return events.find((e) => e.type === "attachments");
}
