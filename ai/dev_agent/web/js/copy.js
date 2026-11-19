import { el } from "./dom.js";
import { icon } from "./icons.js";

// Copies text to the clipboard. The async Clipboard API first (Web UI and VS Code webview); a hidden textarea + execCommand if that is refused.
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = el("textarea", { class: "copy-buffer", readonly: "", "aria-hidden": "true" });
    area.value = text;
    document.body.append(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    area.remove();
    return ok;
  }
}

// A small copy icon. A span with role=button, so it can also sit inside a card header (a button in a button is invalid). `getText` is read when clicked.
export function copyButton(getText, label = "Copy") {
  const btn = el("span", { class: "copy-btn", role: "button", tabindex: "0", title: label, "aria-label": label, "data-act": "copy" }, icon("copy"));
  const run = async (event) => {
    event.stopPropagation();
    event.preventDefault();
    const ok = await copyText(String(getText() ?? ""));
    btn.replaceChildren(icon(ok ? "check" : "alert"));
    btn.title = ok ? "Copied" : "Copy failed";
    btn.classList.toggle("done", ok);
    setTimeout(() => {
      btn.replaceChildren(icon("copy"));
      btn.title = label;
      btn.classList.remove("done");
    }, 1500);
  };
  btn.addEventListener("click", run);
  btn.addEventListener("keydown", (event) => (event.key === "Enter" || event.key === " ") && run(event));
  return btn;
}
