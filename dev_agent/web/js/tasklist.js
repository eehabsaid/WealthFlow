import { clear, el, when } from "./dom.js";

export function renderTasks(list, tasks, selected, onSelect) {
  clear(list);
  if (!tasks.length)
    list.append(el("li", { class: "muted", text: "No tasks yet." }));
  for (const task of tasks) {
    list.append(
      el(
        "li",
        {},
        el(
          "button",
          {
            type: "button",
            class: `task${task.id === selected ? " active" : ""}`,
            onclick: () => onSelect(task.id),
          },
          el("span", { class: "goal", text: task.goal }),
          el(
            "span",
            { class: "meta" },
            el("span", { class: `pill s-${task.status}`, text: task.status }),
            el("span", { class: "muted", text: when(task.updated) }),
          ),
        ),
      ),
    );
  }
}
