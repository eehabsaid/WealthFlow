import { clear, el, when } from "./dom.js";

// The list of earlier tasks (shared with the CLI and the other interface: it is the task ledger on disk).
export function renderHistory(list, store, onOpen) {
  const { tasks, taskId } = store.s;
  clear(list);
  if (!tasks.length) return list.append(el("p", { class: "muted", text: "No tasks yet." }));
  for (const t of tasks)
    list.append(
      el(
        "button",
        {
          type: "button",
          class: `task-row${t.id === taskId ? " active" : ""}`,
          "data-task": t.id,
          onclick: () => onOpen(t.id),
        },
        el("span", { class: "goal", text: t.goal }),
        el(
          "span",
          { class: "meta" },
          el("span", { class: `pill s-${t.status}`, text: t.status }),
          el("span", { text: when(t.updated) })
        )
      )
    );
}
