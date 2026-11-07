import { el } from "./dom.js";

// Renders a unified diff as lines; text only, colours come from CSS classes.
export function renderDiff(info) {
  const head = el(
    "div",
    { class: "diff-head" },
    el("strong", { text: info.path }),
    el("span", { class: "pill", text: info.state }),
    info.renamed_from
      ? el("span", {
          class: "muted",
          text: `renamed from ${info.renamed_from}`,
        })
      : null,
    !info.known_original
      ? el("span", { class: "muted", text: "original content not recorded" })
      : null,
    info.truncated
      ? el("span", { class: "muted", text: "large file: diff truncated" })
      : null,
  );
  if (info.binary)
    return el(
      "div",
      { class: "diff" },
      head,
      el("p", { class: "muted", text: "Binary file: no text diff." }),
    );
  if (!info.diff)
    return el(
      "div",
      { class: "diff" },
      head,
      el("p", { class: "muted", text: info.detail || "No textual changes." }),
    );
  const body = el("pre", { class: "diff-body" });
  for (const line of info.diff.split("\n")) {
    let kind = "ctx";
    if (line.startsWith("+++") || line.startsWith("---")) kind = "meta";
    else if (line.startsWith("@@")) kind = "hunk";
    else if (line.startsWith("+")) kind = "add";
    else if (line.startsWith("-")) kind = "del";
    body.append(el("span", { class: `ln ${kind}`, text: line }), "\n");
  }
  return el("div", { class: "diff" }, head, body);
}
