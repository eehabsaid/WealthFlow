import { get } from "./api.js";
import { clear, el } from "./dom.js";
import { renderDiff } from "./diff.js";

export async function renderFiles(box, taskId) {
  const { files } = await get(`/api/tasks/${taskId}/files`);
  clear(box);
  if (!files.length)
    return box.append(el("p", { class: "muted", text: "No files changed." }));
  const view = el("div", { class: "diff-view" });
  const open = async (path) => {
    clear(view);
    try {
      view.append(
        renderDiff(
          await get(
            `/api/tasks/${taskId}/diff?path=${encodeURIComponent(path)}`,
          ),
        ),
      );
    } catch (error) {
      view.append(el("p", { class: "bad", text: error.message }));
    }
  };
  box.append(
    el(
      "ul",
      { class: "files" },
      files.map((f) =>
        el(
          "li",
          {},
          el("button", {
            type: "button",
            class: "link",
            onclick: () => open(f.path),
            text: f.path,
          }),
          el("span", { class: `pill s-${f.state}`, text: f.state }),
        ),
      ),
    ),
    view,
  );
  if (files.length === 1) open(files[0].path);
}
