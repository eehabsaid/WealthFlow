import { card } from "./card.js";
import { renderDiff } from "./diffview.js";
import { clear, el } from "./dom.js";

const count = (n, sign) => (n === null || n === undefined ? "" : `${sign}${n}`);

// Changed files with +/- counts. "View diff" opens VS Code's native diff editor there, or an inline diff in the browser.
export function filesCard(ui, task, files, transport, onError) {
  const view = el("div", { class: "diff-view" });
  const show = async (path) => {
    try {
      if (transport.openDiff) return await transport.openDiff(task.id, path);
      clear(view).append(
        renderDiff(
          await transport.request(
            "GET",
            `/api/tasks/${task.id}/diff?path=${encodeURIComponent(path)}`
          )
        )
      );
    } catch (error) {
      onError(error);
    }
  };
  const added = files.reduce((n, f) => n + (f.added || 0), 0);
  const removed = files.reduce((n, f) => n + (f.removed || 0), 0);
  return card(ui, {
    key: "files",
    iconName: "file",
    title: `Changed files (${files.length})`,
    sub: `${count(added, "+")} ${count(removed, "−")}`.trim(),
    body: [
      el(
        "ul",
        { class: "files-list" },
        files.map((f) =>
          el(
            "li",
            {},
            el("span", { class: "path", title: f.detail || f.path, text: f.path }),
            f.added !== null && f.added !== undefined
              ? el("span", { class: "plus", text: count(f.added, "+") })
              : null,
            f.removed !== null && f.removed !== undefined
              ? el("span", { class: "minus", text: count(f.removed, "−") })
              : null,
            el("span", { class: `pill s-${f.state}`, text: f.state }),
            el("button", {
              type: "button",
              "data-act": "diff",
              onclick: () => show(f.path),
              text: "View diff",
            })
          )
        )
      ),
      view,
    ],
    open: true,
  });
}
