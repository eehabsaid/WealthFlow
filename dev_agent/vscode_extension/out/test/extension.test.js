"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const assert = __importStar(require("node:assert/strict"));
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const node_test_1 = require("node:test");
const vscodeMock_1 = require("./vscodeMock"); // must be imported before the extension: it installs the fake `vscode`
const env_1 = require("./env");
// Activate the extension, open its chat view like VS Code would, and give back a function that makes the same calls the webview page makes.
async function boot(env) {
    const ext = require("../extension");
    vscodeMock_1.state.folder = env.project;
    vscodeMock_1.config.pythonPath = env_1.PYTHON;
    vscodeMock_1.config.agentPath = env_1.REPO;
    const context = { subscriptions: [], extensionUri: { path: "/ext", scheme: "file", fsPath: "/ext" } };
    ext.activate(context);
    await (0, env_1.until)(() => vscodeMock_1.calls.contexts.get("devAgent.connected") === true || (/offline/.test(vscodeMock_1.state.statusItem.text) && (() => { throw new Error(`offline: ${String(vscodeMock_1.state.statusItem.tooltip)}`); })()), 30000, "server to start");
    const out = [];
    let receive = () => undefined;
    const view = {
        visible: true,
        webview: { options: {}, html: "", cspSource: "vscode-webview://x", asWebviewUri: (u) => u, postMessage: async (m) => void out.push(m), onDidReceiveMessage: (fn) => void (receive = fn) },
        onDidDispose: () => undefined,
    };
    vscodeMock_1.calls.views.get("devAgent.chat").resolveWebviewView(view);
    let n = 0;
    const call = async (name, args = {}) => {
        const id = ++n;
        receive({ type: "call", id, name, args });
        return (0, env_1.until)(() => out.find((m) => m.type === "res" && m.id === id), 20000, `reply to ${name}`);
    };
    // like VS Code on shutdown: deactivate(), then dispose everything the extension registered
    const closing = { deactivate: async () => (await ext.deactivate(), context.subscriptions.forEach((d) => void d.dispose())) };
    return { ext: closing, view, out, call };
}
(0, node_test_1.test)("the chat view runs a whole task against a real server: plan, approve, change, native diff, report", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)(), env_1.WRITE, env_1.DONE], false);
    const { ext, view, out, call } = await boot(env);
    try {
        assert.match(view.webview.html, /Content-Security-Policy/);
        assert.ok(!/connect-src/.test(view.webview.html), "no network permission for the page");
        assert.deepEqual(view.webview.options.localResourceRoots.map((r) => r.path), ["/ext/media/chat"]);
        assert.equal((await call("request", { method: "GET", path: "/api/state" })).data.busy, false);
        const { data } = await call("submit", { goal: "add more" });
        await call("subscribe", { taskId: data.id });
        await (0, env_1.until)(() => out.some((m) => m.type === "event" && m.event.type === "status" && m.event.status === "awaiting_approval"), 30000, "plan event");
        assert.equal((await call("request", { method: "POST", path: `/api/tasks/${data.id}/approve`, body: {} })).ok, true);
        await (0, env_1.until)(async () => (await call("request", { method: "GET", path: `/api/tasks/${data.id}` })).data.status === "completed", 30000, "completed");
        assert.equal(fs.readFileSync(path.join(env.project, "app/more.py"), "utf8"), "X = 1\n");
        await call("openDiff", { taskId: data.id, path: "app/more.py" });
        const diff = vscodeMock_1.calls.executed.find((c) => c[0] === "vscode.diff");
        assert.ok(diff, "VS Code's native diff editor is used");
        assert.equal(diff[1].scheme, "devagent");
        const original = await vscodeMock_1.calls.providers.get("devagent").provideTextDocumentContent(diff[1]);
        assert.equal(original, "", "a new file's original side is empty");
        await call("openReport", { taskId: data.id });
        assert.match(vscodeMock_1.calls.docs.at(-1).content, /./);
    }
    finally {
        await ext.deactivate();
        await env.close();
    }
});
(0, node_test_1.test)("Stop from the command palette reaches the engine; deactivate kills the hidden server", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)()], false);
    const { ext, call } = await boot(env);
    try {
        const { execFileSync } = require("node:child_process");
        const before = execFileSync("pgrep", ["-f", `dev_agent --root ${env.project} serve`]).toString().trim().split("\n").map(Number);
        assert.ok(before.length >= 1);
        assert.equal((await call("request", { method: "POST", path: "/api/stop", body: {} })).ok, true);
        await vscodeMock_1.calls.commands.get("devAgent.stop")?.();
        await ext.deactivate();
        await (0, env_1.until)(() => before.every((pid) => !(0, env_1.alive)(pid)), 10000, "server to be gone");
    }
    finally {
        await env.close();
    }
});
(0, node_test_1.test)("the webview can reach only the allowlist, and never sees the token or a key", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)()], false);
    const { ext, view, out, call } = await boot(env);
    try {
        const blocked = [
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
        const pid = Number(require("node:child_process").execFileSync("pgrep", ["-f", `dev_agent --root ${env.project} serve`]).toString().trim().split("\n")[0]);
        const token = /DEV_AGENT_TOKEN=([^\0]+)/.exec(fs.readFileSync(`/proc/${pid}/environ`, "utf8"))?.[1] ?? "";
        assert.ok(token.length >= 32, "found the server's token");
        await call("request", { method: "GET", path: "/api/keys" });
        const everything = JSON.stringify([out, view.webview.html]);
        assert.ok(!everything.includes(token), "the access token never reaches the page");
        assert.ok(!/sk-[a-z]/i.test(everything));
    }
    finally {
        await ext.deactivate();
        await env.close();
    }
});
