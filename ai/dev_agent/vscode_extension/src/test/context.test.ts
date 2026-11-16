import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import { CONTEXT_KEYS } from "../bridge";
import { answers, calls } from "./vscodeMock"; // installs the fake `vscode` before the extension is loaded
import { boot } from "./boot";
import { Env, DONE, PLAN, WRITE, until } from "./env";
import { canRunBrowser, openChat } from "./page";

const settingsFile = (env: Env): any => JSON.parse(fs.readFileSync(path.join(env.project, "coding_agent", "agent_settings.json"), "utf8"));

test("the chat page reads and writes the context values through the allowlist; the file on disk changes", async () => {
  const env = await Env.create([PLAN()], false);
  const { ext, call } = await boot(env);
  try {
    const got = await call("request", { method: "GET", path: "/api/settings/context" });
    assert.equal(got.ok, true);
    assert.deepEqual(got.data.values.map((v: { key: string }) => v.key), CONTEXT_KEYS);
    assert.equal(got.data.file, "coding_agent/agent_settings.json");
    const put = await call("request", { method: "PUT", path: "/api/settings/context", body: { values: { max_fix_rounds: 7, timeout_s: 5 } } });
    assert.equal(put.ok, true);
    assert.deepEqual(put.data.changed.map((c: { key: string; new: number }) => [c.key, c.new]), [["max_fix_rounds", 7], ["timeout_s", 30]], "5 s is below the allowed minimum and is clamped");
    assert.equal(settingsFile(env).max_fix_rounds, 7);
    assert.equal((await call("request", { method: "GET", path: "/api/settings/context" })).data.values.find((v: { key: string }) => v.key === "max_fix_rounds").value, 7);
    const blocked: [string, string, unknown][] = [
      ["PUT", "/api/settings/context", { values: { model: 1 } }], // not a context value
      ["PUT", "/api/settings/context", { values: { timeout_s: "60" } }], // not a number
      ["PUT", "/api/settings/context", { values: { timeout_s: null } }],
      ["PUT", "/api/settings/context", { values: {} }],
      ["PUT", "/api/settings/context", {}],
      ["POST", "/api/settings/context", { values: { timeout_s: 60 } }],
      ["DELETE", "/api/settings/context", undefined],
      ["GET", "/api/settings/context/x", undefined],
    ];
    for (const [method, p, body] of blocked) {
      const r = await call("request", { method, path: p, body });
      assert.equal(r.ok, false, `${method} ${p} ${JSON.stringify(body)}`);
      assert.equal(r.error.code, "blocked");
    }
    assert.equal(settingsFile(env).timeout_s, 30, "nothing blocked reached the file");
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("the command palette and the menu open Context & limits in the page, also when the page was not loaded yet", async () => {
  const env = await Env.create([PLAN()], false);
  const { ext, out, call, send } = await boot(env);
  try {
    const seen = () => out.filter((m) => m.type === "command").map((m) => m.name);
    await calls.commands.get("devAgent.contextSettings")?.();
    assert.deepEqual(seen(), [], "queued until the page says it is ready");
    send({ type: "ready" });
    await until(() => seen().length === 1, 5000, "queued command");
    await calls.commands.get("devAgent.contextSettings")?.();
    assert.deepEqual(seen(), ["contextSettings", "contextSettings"], "posted at once when the page is ready");
    answers.pick.push("Context & limits…");
    assert.equal((await call("menu")).ok, true);
    assert.deepEqual(calls.executed.at(-1), ["devAgent.contextSettings"]);
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("a task streams `context` events (real counts or the agent's estimate) and never `trace` events to the page", async () => {
  const env = await Env.create([PLAN(), WRITE, DONE], false);
  const { ext, out, call } = await boot(env);
  try {
    const { data } = await call("submit", { goal: "add more" });
    await call("subscribe", { taskId: data.id });
    await until(() => out.some((m) => m.type === "event" && m.event.type === "status" && m.event.status === "awaiting_approval"), 30000, "plan");
    const events = out.filter((m) => m.type === "event").map((m) => m.event);
    const context = events.filter((e) => e.type === "context");
    assert.ok(context.length >= 1 && context.every((e) => e.window === 150000 && e.limit === 122000 && e.used > 0 && e.percent > 0), "a reading after every model call");
    assert.ok(context.every((e) => e.source === "estimate" && e.reported.input_tokens === 10), "the fake model reports 10 tokens: far too few, so the estimate is shown");
    assert.ok(!events.some((e) => e.type === "trace"), "the full trajectory stays in events.jsonl, not in the live feed");
    assert.deepEqual(events.map((e) => e.seq), events.map((_, i) => i + 1), "the feed numbering has no gaps");
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("the meter and the Context & limits page in the real chat UI under the webview CSP", { skip: !canRunBrowser }, async () => {
  const env = await Env.create([PLAN(), WRITE, DONE]);
  const chat = await openChat(env);
  const { page, problems } = chat;
  try {
    assert.match(await page.innerText("#context-meter"), /waiting for the first model call/);
    await page.fill("#goal", "add more");
    await page.click("#send-btn");
    await page.waitForSelector("[data-act=approve]", { timeout: 30000 });
    await page.waitForSelector("#context-meter .meter-percent:not(:empty)");
    const text = await page.innerText("#context-meter");
    assert.match(text, /~[\d.k]+ \/ 150k/);
    assert.match(text, /~\d+(\.\d)?%/);
    assert.match(await page.getAttribute("#context-meter", "title"), /Context: ~[\d,]+ of 150,000 tokens[\s\S]*estimated by the agent/);
    assert.ok(/lvl-ok/.test((await page.getAttribute("#context-meter", "class")) ?? ""));
    await chat.toPage({ type: "command", name: "contextSettings" }); // what the VS Code command does
    await page.waitForSelector("#ctx-max_fix_rounds");
    assert.equal(await page.inputValue("#ctx-max_fix_rounds"), "12");
    await page.fill("#ctx-max_fix_rounds", "7");
    await page.fill("#ctx-reserve_tokens", "140000");
    await page.click("#ctx-save");
    await page.waitForSelector(".ctx-settings .changes li");
    assert.match(await page.innerText(".ctx-settings .changes"), /Max fix rounds: 12 → 7/);
    assert.match(await page.innerText(".ctx-settings .warnings"), /Only 10,000 of 150,000 tokens/);
    assert.match(await page.innerText(".ctx-settings [role=status]"), /Saved to coding_agent\/agent_settings.json/);
    assert.deepEqual([settingsFile(env).max_fix_rounds, settingsFile(env).reserve_tokens], [7, 140000]);
    assert.deepEqual(problems.filter((p) => !/favicon|api\/health/.test(p)), [], "no console errors or CSP violations");
  } finally {
    await chat.close();
    await env.close();
  }
});
