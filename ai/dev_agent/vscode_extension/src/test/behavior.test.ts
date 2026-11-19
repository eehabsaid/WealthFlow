import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import { BEHAVIOR_KEYS } from "../bridge";
import "./vscodeMock"; // installs the fake `vscode` before the extension is loaded
import { boot } from "./boot";
import { Env, PLAN, until } from "./env";
import { canRunBrowser, openChat } from "./page";

const settingsFile = (env: Env): any => JSON.parse(fs.readFileSync(path.join(env.project, "coding_agent", "agent_settings.json"), "utf8"));

test("the Behavior switches go through the allowlist: only the known true/false values reach the file", async () => {
  const env = await Env.create([PLAN()], false);
  const { ext, call } = await boot(env);
  try {
    const got = await call("request", { method: "GET", path: "/api/settings/behavior" });
    assert.equal(got.ok, true);
    assert.deepEqual(got.data.values.map((v: { key: string }) => v.key), BEHAVIOR_KEYS);
    const put = await call("request", { method: "PUT", path: "/api/settings/behavior", body: { values: { deep_search: true, require_plan_approval: false } } });
    assert.equal(put.ok, true);
    assert.deepEqual(put.data.changed.map((c: { key: string; new: boolean }) => [c.key, c.new]), [["deep_search", true], ["require_plan_approval", false]]);
    assert.deepEqual([settingsFile(env).deep_search, settingsFile(env).require_plan_approval], [true, false]);
    const blocked: [string, string, unknown][] = [
      ["PUT", "/api/settings/behavior", { values: { model: true } }], // not a switch
      ["PUT", "/api/settings/behavior", { values: { deep_search: "true" } }], // not a boolean
      ["PUT", "/api/settings/behavior", { values: { deep_search: 1 } }],
      ["PUT", "/api/settings/behavior", { values: {} }],
      ["POST", "/api/settings/behavior", { values: { deep_search: true } }],
      ["DELETE", "/api/settings/behavior", undefined],
    ];
    for (const [method, p, body] of blocked) {
      const r = await call("request", { method, path: p, body });
      assert.equal(r.ok, false, `${method} ${p} ${JSON.stringify(body)}`);
      assert.equal(r.error.code, "blocked");
    }
    assert.equal(settingsFile(env).quick_mode, false, "nothing blocked reached the file");
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("a follow-up sent with `chat` joins the chat of the task it continues; a malformed chat id starts a new chat", async () => {
  const env = await Env.create([PLAN(), PLAN(), PLAN()], false);
  const { ext, out, call } = await boot(env);
  try {
    const first = (await call("submit", { goal: "add more" })).data.id;
    await call("subscribe", { taskId: first });
    await until(() => out.some((m) => m.type === "event" && m.event.type === "status" && m.event.status === "awaiting_approval"), 30000, "plan");
    const second = (await call("submit", { goal: "and one more thing", chat: first })).data.id;
    await until(async () => (await call("request", { method: "GET", path: `/api/tasks/${second}` })).data?.status === "awaiting_approval", 30000, "second plan");
    const rows = (await call("request", { method: "GET", path: "/api/tasks" })).data.tasks;
    assert.deepEqual(rows.filter((r: { id: string }) => [first, second].includes(r.id)).map((r: { chat: string }) => r.chat), [first, first]);
    const third = (await call("submit", { goal: "other topic", chat: "../../etc" })).data.id;
    await until(async () => (await call("request", { method: "GET", path: `/api/tasks/${third}` })).data?.status === "awaiting_approval", 30000, "third plan");
    assert.equal((await call("request", { method: "GET", path: `/api/tasks/${third}` })).data.chat_id, third);
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("the chat page keeps the open chat for a follow-up and has a Behavior page whose switches are saved", { skip: !canRunBrowser }, async () => {
  const env = await Env.create([PLAN(), PLAN()]);
  const chat = await openChat(env);
  const { page, problems } = chat;
  try {
    await page.fill("#goal", "add more");
    await page.click("#send-btn");
    await page.waitForSelector("[data-act=approve]", { timeout: 30000 });
    await page.fill("#goal", "now also this");
    await page.click("#send-btn");
    await page.waitForSelector(".task-row", { timeout: 30000 });
    assert.equal(await page.locator(".task-row").count(), 1);
    assert.match(await page.innerText(".thread"), /add more[\s\S]*now also this/, "the first message stays above the follow-up in the same thread");
    await page.click(".msg.user .copy-btn >> nth=-1"); // the copy icon under a message
    await page.waitForSelector(".msg.user .copy-btn.done", { timeout: 5000 });
    assert.equal(await page.getAttribute(".msg.user .copy-btn.done", "title"), "Copied");
    await chat.toPage({ type: "command", name: "behaviorSettings" }); // what the VS Code command does
    await page.waitForSelector("#bh-deep_search");
    assert.equal(await page.isChecked("#bh-require_plan_approval"), true);
    await page.click("#bh-deep_search");
    await page.click("#bh-require_plan_approval");
    await until(() => settingsFile(env).deep_search === true && settingsFile(env).require_plan_approval === false, 10000, "switches saved");
    assert.match(await page.innerText(".behavior-settings [role=status]"), /Saved in coding_agent\/agent_settings.json/);
    assert.deepEqual(problems.filter((p) => !/favicon|api\/health/.test(p)), [], "no console errors or CSP violations");
  } finally {
    await chat.close();
    await env.close();
  }
});
