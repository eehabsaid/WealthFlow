import { el } from "./dom.js";
import { icon } from "./icons.js";

// One collapsible card. `ui.open` remembers which cards the user opened or closed, so a re-render never flips them back.
export function card(
  ui,
  { key, cls = "", iconName, iconCls = "", title, sub = "", right = null, body, open = false }
) {
  const isOpen = ui.open.has(key) ? ui.open.get(key) : open;
  const root = el("div", { class: `card ${cls}${isOpen ? " open" : ""}`, "data-key": key });
  const head = el(
    "button",
    {
      type: "button",
      class: "card-head",
      "aria-expanded": String(isOpen),
      onclick: () => {
        const now = !root.classList.contains("open");
        root.classList.toggle("open", now);
        head.setAttribute("aria-expanded", String(now));
        ui.open.set(key, now);
      },
    },
    iconName ? el("span", { class: iconCls }, icon(iconName)) : null,
    el("span", { class: "title", text: title }),
    el("span", { class: "sub", text: sub }),
    el("span", { class: "grow" }),
    right,
    icon("chevron", "chev")
  );
  root.append(head, el("div", { class: "card-body" }, body));
  return root;
}
