import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import { calls } from "./vscodeMock"; // installs the fake `vscode` before the extension is loaded
import { boot } from "./boot";
import { Env, DONE, PLAN, WRITE, alive, spawned, until } from "./env";

test("the chat view runs a whole task against a real server: plan, approve, change, native diff, report", async () => {
  const env = await Env.create([PLAN(), WRITE, DONE], false);
  const { ext, view, out, call } = await boot(env);
  try {
    assert.match(view.webview.html, /Content-Security-Policy/);
    assert.ok(!/connect-src/.test(view.webview.html), "no network permission for the page");
    assert.deepEqual(view.webview.options.localResourceRoots.map((r: any) => r.path), ["/ext/media/chat"]);
    assert.equal((await call("request", { method: "GET", path: "/api/state" })).data.busy, false);
    const { data } = await call("submit", { goal: "add more" });
    await call("subscribe", { taskId: data.id });
    await until(() => out.some((m) => m.type === "event" && m.event.type === "status" && m.event.status === "awaiting_approval"), 30000, "plan event");
    assert.equal((await call("request", { method: "POST", path: `/api/tasks/${data.id}/approve`, body: {} })).ok, true);
    await until(async () => (await call("request", { method: "GET", path: `/api/tasks/${data.id}` })).data.status === "completed", 30000, "completed");
    assert.equal(fs.readFileSync(path.join(env.project, "app/more.py"), "utf8"), "X = 1\n");
    await call("openDiff", { taskId: data.id, path: "app/more.py" });
    const diff = calls.executed.find((c) => c[0] === "vscode.diff");
    assert.ok(diff, "VS Code's native diff editor is used");
    assert.equal(diff[1].scheme, "devagent");
    const original = await calls.providers.get("devagent").provideTextDocumentContent(diff[1]);
    assert.equal(original, "", "a new file's original side is empty");
    await call("openReport", { taskId: data.id });
    assert.match(calls.docs.at(-1).content, /./);
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("Stop from the command palette reaches the engine; deactivate kills the hidden server", async () => {
  const env = await Env.create([PLAN()], false);
  const { ext, call } = await boot(env);
  try {
    const before = [spawned.at(-1)?.pid as number];     // the hidden server this extension just started
    assert.ok(before[0] && alive(before[0]));
    assert.equal((await call("request", { method: "POST", path: "/api/stop", body: {} })).ok, true);
    await calls.commands.get("devAgent.stop")?.();
    await ext.deactivate();
    await until(() => before.every((pid) => !alive(pid)), 10000, "server to be gone");
  } finally {
    await ext.deactivate();      // also when an assertion above failed: a server left running would keep the test runner from ever exiting
    await env.close();
  }
});

test("the webview can reach only the allowlist, and never sees the token or a key", async () => {
  const env = await Env.create([PLAN()], false);
  const { ext, view, out, call } = await boot(env);
  try {
    const blocked: [string, string, unknown][] = [
      ["PUT", "/api/keys/openai", { value: "sk-x" }],
      ["DELETE", "/api/keys/openai", undefined],
      ["POST", "/api/shutdown", {}],
      ["POST", "/api/tasks", { goal: "x" }],
      ["PUT", "/api/settings", { values: { project_root: "/", provider: "ollama" } }],
      ["GET", "/api/tasks/abc/file?path=.env", undefined],
      ["GET", "http://evil.example/api/state", undefined],
    ];
    for (const [method, path, body] of blocked) {
      const r = await call("request", { method, path, body });
      assert.equal(r.ok, false, `${method} ${path}`);
      assert.equal(r.error.code, "blocked");
    }
    assert.equal((await call("nonsense")).ok, false);
    assert.equal((await call("setApiKey", { provider: "bogus" })).ok, false);
    // the token lives only in the server's environment (and the host's memory): read it from the server process
    const token = spawned.at(-1)?.token ?? "";
    assert.ok(token.length >= 32, "found the server's token");
    await call("request", { method: "GET", path: "/api/keys" });
    const everything = JSON.stringify([out, view.webview.html]);
    assert.ok(!everything.includes(token), "the access token never reaches the page");
    assert.ok(!/sk-[a-z]/i.test(everything));
  } finally {
    await ext.deactivate();
    await env.close();
  }
});
