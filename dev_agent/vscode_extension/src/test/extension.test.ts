import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import { calls, config, state } from "./vscodeMock"; // must be imported before the extension: it installs the fake `vscode`
import { Env, DONE, PLAN, PYTHON, REPO, WRITE, alive, until } from "./env";

type Ext = typeof import("../extension");
type Res = { type: string; id?: number; ok?: boolean; data?: any; error?: any; event?: any };

// Activate the extension, open its chat view like VS Code would, and give back a function that makes the same calls the webview page makes.
async function boot(env: Env) {
  const ext = require("../extension") as Ext;
  state.folder = env.project;
  config.pythonPath = PYTHON;
  config.agentPath = REPO;
  const context = { subscriptions: [] as { dispose(): unknown }[], extensionUri: { path: "/ext", scheme: "file", fsPath: "/ext" } };
  ext.activate(context as never);
  await until(() => calls.contexts.get("devAgent.connected") === true || (/offline/.test(state.statusItem.text) && (() => { throw new Error(`offline: ${String(state.statusItem.tooltip)}`); })()), 30000, "server to start");
  const out: Res[] = [];
  let receive: (m: unknown) => void = () => undefined;
  const view = {
    visible: true,
    webview: { options: {} as any, html: "", cspSource: "vscode-webview://x", asWebviewUri: (u: any) => u, postMessage: async (m: Res) => void out.push(m), onDidReceiveMessage: (fn: (m: unknown) => void) => void (receive = fn) },
    onDidDispose: () => undefined,
  };
  calls.views.get("devAgent.chat").resolveWebviewView(view);
  let n = 0;
  const call = async (name: string, args: Record<string, unknown> = {}): Promise<Res> => {
    const id = ++n;
    receive({ type: "call", id, name, args });
    return until(() => out.find((m) => m.type === "res" && m.id === id), 20000, `reply to ${name}`);
  };
  // like VS Code on shutdown: deactivate(), then dispose everything the extension registered
  const closing = { deactivate: async () => (await ext.deactivate(), context.subscriptions.forEach((d) => void d.dispose())) };
  return { ext: closing, view, out, call };
}

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
    const { execFileSync } = require("node:child_process") as typeof import("node:child_process");
    const before = execFileSync("pgrep", ["-f", `dev_agent --root ${env.project} serve`]).toString().trim().split("\n").map(Number);
    assert.ok(before.length >= 1);
    assert.equal((await call("request", { method: "POST", path: "/api/stop", body: {} })).ok, true);
    await calls.commands.get("devAgent.stop")?.();
    await ext.deactivate();
    await until(() => before.every((pid) => !alive(pid)), 10000, "server to be gone");
  } finally {
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
    const pid = Number((require("node:child_process") as typeof import("node:child_process")).execFileSync("pgrep", ["-f", `dev_agent --root ${env.project} serve`]).toString().trim().split("\n")[0]);
    const token = /DEV_AGENT_TOKEN=([^\0]+)/.exec(fs.readFileSync(`/proc/${pid}/environ`, "utf8"))?.[1] ?? "";
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
