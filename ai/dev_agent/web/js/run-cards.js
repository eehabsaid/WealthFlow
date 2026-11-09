import { card } from "./card.js";
import { el } from "./dom.js";

function rows(items) {
  return el(
    "ul",
    { class: "rows" },
    items.map((r) =>
      el(
        "li",
        { class: r.kind === "bad" ? "bad" : "" },
        el("span", { class: "k", text: r.k }),
        el("span", { class: "v", text: r.v })
      )
    )
  );
}

// Live steps and tool calls of one work package (open while it runs, closed once done).
export function workCard(ui, g) {
  const running = g.status === "running";
  const failed = g.rows.filter((r) => r.kind === "bad").length;
  return card(ui, {
    key: g.key,
    iconName: running ? "spinner" : failed ? "alert" : "wrench",
    iconCls: failed && !running ? "warn" : "",
    title: g.title,
    sub: `${g.rows.length} step${g.rows.length === 1 ? "" : "s"}${failed ? ` · ${failed} problem${failed === 1 ? "" : "s"}` : ""}`,
    body: g.rows.length ? rows(g.rows) : el("p", { class: "muted", text: "Working…" }),
    open: running,
  });
}

const VERDICT = {
  VERIFIED: ["Verification passed", "ok", "check", "good"],
  FAILED: ["Verification failed", "bad", "alert", "bad"],
};

// Check results, exactly as the engine reports them: anything that did not run is listed, never hidden.
export function verifyCard(ui, g) {
  const [title, cls, name, tone] = VERDICT[g.overall] || [
    "Not fully verified",
    "attention",
    "alert",
    "warn",
  ];
  return card(ui, {
    key: g.key,
    cls,
    iconName: name,
    iconCls: tone,
    title,
    sub:
      g.overall === "VERIFIED" ? `${g.label}: all checks successful` : `${g.label}: ${g.overall}`,
    body: rows(
      g.results.map((r) => ({
        kind: r.status === "FAILED" ? "bad" : "tool",
        k: r.step,
        v: r.status,
      }))
    ),
    open: g.overall !== "VERIFIED",
  });
}

export function errorCard(ui, g) {
  return card(ui, {
    key: g.key,
    cls: "bad",
    iconName: "alert",
    iconCls: "bad",
    title: "Error",
    sub: g.message,
    body: el("pre", { class: "wrap", text: g.message }),
    open: true,
  });
}

// A request the engine is waiting on (protected file, command that needs you). The first answer from any interface wins.
export function approvalCard(ui, item, actions) {
  return card(ui, {
    key: `approval-${item.id}`,
    cls: "attention",
    iconName: "alert",
    iconCls: "warn",
    title: "Approval needed",
    sub: item.kind,
    body: [
      el("pre", { class: "wrap", text: item.message }),
      el(
        "div",
        { class: "actions" },
        el("button", {
          type: "button",
          class: "primary",
          "data-act": "allow",
          onclick: () => actions.answer(item.id, true),
          text: "Approve",
        }),
        el("button", {
          type: "button",
          "data-act": "deny",
          onclick: () => actions.answer(item.id, false),
          text: "Deny",
        })
      ),
    ],
    open: true,
  });
}
