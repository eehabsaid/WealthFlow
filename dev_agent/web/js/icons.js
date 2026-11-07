// Small stroke icons (24x24 grid), drawn as inline SVG so they follow the text colour and need no files.
const NS = "http://www.w3.org/2000/svg";
const ICONS = {
  paperclip: [
    [
      "path",
      {
        d: "M21.4 11 12.2 20.2a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.9-2.9l8.5-8.5",
      },
    ],
  ],
  image: [
    ["rect", { x: 3, y: 3, width: 18, height: 18, rx: 2 }],
    ["circle", { cx: 8.5, cy: 8.5, r: 1.5 }],
    ["path", { d: "m21 15-5-5L5 21" }],
  ],
  send: [
    ["path", { d: "M22 2 11 13" }],
    ["path", { d: "M22 2 15 22l-4-9-9-4z" }],
  ],
  stop: [["rect", { x: 6, y: 6, width: 12, height: 12, rx: 1 }]],
  history: [
    ["circle", { cx: 12, cy: 12, r: 9 }],
    ["path", { d: "M12 7v5l3 2" }],
  ],
  plus: [["path", { d: "M12 5v14M5 12h14" }]],
  sliders: [
    ["path", { d: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" }],
  ],
  check: [["path", { d: "m20 6-11 11-5-5" }]],
  x: [["path", { d: "M18 6 6 18M6 6l12 12" }]],
  chevron: [["path", { d: "m6 9 6 6 6-6" }]],
  file: [
    ["path", { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" }],
    ["path", { d: "M14 2v6h6" }],
  ],
  wrench: [
    [
      "path",
      {
        d: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z",
      },
    ],
  ],
  terminal: [["path", { d: "m4 17 6-6-6-6M12 19h8" }]],
  alert: [
    ["circle", { cx: 12, cy: 12, r: 10 }],
    ["path", { d: "M12 8v4M12 16h.01" }],
  ],
  circle: [["circle", { cx: 12, cy: 12, r: 9 }]],
  spinner: [["path", { d: "M21 12a9 9 0 1 1-6.2-8.6" }]],
  bot: [
    ["rect", { x: 4, y: 8, width: 16, height: 12, rx: 3 }],
    ["path", { d: "M12 4v4M9 14h.01M15 14h.01" }],
  ],
  user: [
    ["circle", { cx: 12, cy: 8, r: 4 }],
    ["path", { d: "M4 21a8 8 0 0 1 16 0" }],
  ],
};

export function icon(name, extra = "") {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute(
    "class",
    `icon-svg ${name === "stop" ? "solid " : ""}${name === "spinner" ? "spin " : ""}${extra}`.trim()
  );
  svg.setAttribute("aria-hidden", "true");
  for (const [tag, attrs] of ICONS[name] || []) {
    const part = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) part.setAttribute(key, String(value));
    svg.append(part);
  }
  return svg;
}
