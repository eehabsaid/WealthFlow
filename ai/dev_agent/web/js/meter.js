import { el } from "./dom.js";
import { icon } from "./icons.js";

// The context meter under the chat box: how full the model's context is after the latest step, from the `context` events the engine writes after
// every model call (real provider counts, or the agent's own estimate marked with "~"). Nothing is shown until the first real event of a task.

export function tokens(n) {
  const v = Number(n) || 0;
  if (v >= 1e6) return `${+(v / 1e6).toFixed(1)}M`;
  if (v >= 1e4) return `${Math.round(v / 1e3)}k`;
  if (v >= 1e3) return `${+(v / 1e3).toFixed(1)}k`;
  return String(Math.round(v));
}

// Pure: everything the bar shows for one event, or null when nothing was measured yet.
export function meterModel(event) {
  if (!event || !(event.window > 0)) return null;
  const approx = event.source === "estimate";
  const mark = approx ? "~" : "";
  const rep = event.reported || {};
  const n = (v) => Number(v).toLocaleString("en-US");
  const source = approx
    ? "estimated by the agent (the provider gave no usable prompt count)"
    : `reported by the provider (prompt ${n(rep.input_tokens)} + reply ${n(rep.output_tokens)})`;
  const lines = [
    `Context: ${mark}${n(event.used)} of ${n(event.window)} tokens (${mark}${event.percent}%)`,
    `Free: ${mark}${n(event.remaining)} tokens; ${mark}${n(event.remaining_usable)} before the agent trims old steps (at ${n(event.limit)})`,
    `Source: ${source}`,
    `After ${event.phase || "phase"}, step ${event.step || 0}`,
  ];
  if (event.level !== "ok")
    lines.push(
      event.level === "critical"
        ? "Nearly full: old steps are about to be trimmed."
        : "Getting full: the agent will soon trim old steps."
    );
  return {
    level: event.level || "ok",
    bar: Math.max(0, Math.min(100, event.percent)),
    trim: Math.max(0, Math.min(100, (100 * event.limit) / event.window)),
    used: `${mark}${tokens(event.used)} / ${tokens(event.window)}`,
    percent: `${mark}${event.percent}%`,
    left: `${mark}${tokens(event.remaining)} left`,
    title: lines.join("\n"),
  };
}

export function createMeter(onSettings, onBehavior) {
  const used = el("span", { class: "meter-used" });
  const percent = el("span", { class: "meter-percent" });
  const left = el("span", { class: "meter-left" });
  const fill = el("div", { class: "meter-fill" });
  const trim = el("div", { class: "meter-trim" });
  const bar = el(
    "div",
    { class: "meter-bar", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": 100 },
    fill,
    trim
  );
  const behavior = el(
    "button",
    {
      type: "button",
      class: "icon",
      id: "behavior-settings-btn",
      title: "Behavior: approvals and speed",
      "aria-label": "Behavior: approvals and speed",
      onclick: onBehavior,
    },
    icon("shield")
  );
  const gear = el(
    "button",
    {
      type: "button",
      class: "icon",
      id: "context-settings-btn",
      title: "Context & limits",
      "aria-label": "Context & limits",
      onclick: onSettings,
    },
    icon("sliders")
  );
  const root = el(
    "div",
    { class: "meter lvl-none", id: "context-meter", role: "group", "aria-label": "Context window" },
    el("div", { class: "meter-text" }, used, percent, left, el("span", { class: "spacer" }), behavior, gear),
    bar
  );

  function show(event) {
    const m = meterModel(event);
    root.className = `meter lvl-${m ? m.level : "none"}`;
    root.title = m ? m.title : "The context meter fills in after the agent's first model call.";
    used.textContent = m ? m.used : "Context: waiting for the first model call";
    percent.textContent = m ? m.percent : "";
    left.textContent = m ? m.left : "";
    fill.style.width = `${m ? m.bar : 0}%`;
    trim.style.left = `${m ? m.trim : 100}%`;
    bar.setAttribute("aria-valuenow", String(m ? Math.round(m.bar) : 0));
  }
  show(null);
  return { root, show };
}
