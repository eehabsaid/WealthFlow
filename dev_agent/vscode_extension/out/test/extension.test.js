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
const node_test_1 = require("node:test");
const vscodeMock_1 = require("./vscodeMock"); // must be imported before the extension: it installs the fake `vscode`
const env_1 = require("./env");
// Activate the extension against a project and wait until its hidden server is up; fail fast (with the reason) if it goes offline instead.
async function boot(ext, env) {
    vscodeMock_1.state.folder = env.project;
    vscodeMock_1.config.pythonPath = env_1.PYTHON;
    vscodeMock_1.config.agentPath = env_1.REPO;
    vscodeMock_1.calls.contexts.delete("devAgent.connected");
    ext.activate({ subscriptions: [] });
    await (0, env_1.until)(() => {
        if (/offline/.test(vscodeMock_1.state.statusItem.text))
            throw new Error(`the extension went offline: ${String(vscodeMock_1.state.statusItem.tooltip)}`);
        return vscodeMock_1.calls.contexts.get("devAgent.connected") === true;
    }, 30000, "server to start");
}
(0, node_test_1.test)("the whole extension against a real agent server: start, task, plan dialog, run, tree views, diff, stop on deactivate", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)(), env_1.WRITE, env_1.DONE], false);
    const ext = require("../extension");
    try {
        vscodeMock_1.answers.info.push("Approve and run"); // the plan-ready modal
        await boot(ext, env);
        assert.match(vscodeMock_1.state.statusItem.text, /dev_agent/);
        vscodeMock_1.answers.input.push("add more");
        await vscodeMock_1.calls.commands.get("devAgent.newTask")?.();
        const tasks = vscodeMock_1.calls.trees.get("devAgent.tasks");
        const row = await (0, env_1.until)(() => tasks.getChildren()[0], 10000, "task row");
        assert.equal(tasks.getTreeItem(row).command.command, "devAgent.selectTask");
        await vscodeMock_1.calls.commands.get("devAgent.selectTask")?.(row.id);
        await (0, env_1.until)(() => vscodeMock_1.calls.infos.length > 0, 20000, "plan-ready dialog");
        assert.equal(vscodeMock_1.calls.infos[0][0], "The plan is ready for your review");
        assert.match(vscodeMock_1.calls.infos[0][1].detail, /Add: app\/more\.py/);
        assert.equal(vscodeMock_1.calls.infos[0][1].modal, true);
        const files = vscodeMock_1.calls.trees.get("devAgent.files");
        await (0, env_1.until)(() => files.getChildren().length === 1, 25000, "changed file after the run");
        assert.equal(files.getTreeItem(files.getChildren()[0]).description, "written");
        const plan = vscodeMock_1.calls.trees.get("devAgent.plan");
        assert.ok(plan.getChildren().some((n) => n.label.startsWith("Add")));
        const progress = vscodeMock_1.calls.trees.get("devAgent.progress");
        const labels = () => progress.getChildren().map((r) => r.label);
        await (0, env_1.until)(() => labels().some((l) => l.startsWith("Finished: completed")), 15000, "the finished row");
        assert.ok(progress.getChildren().some((r) => (r.children?.length ?? 0) > 0), "tool calls are grouped under their package");
        await vscodeMock_1.calls.commands.get("devAgent.openDiff")?.("app/more.py");
        const diff = vscodeMock_1.calls.executed.find((c) => c[0] === "vscode.diff");
        assert.ok(diff, "native diff editor must be opened");
        assert.equal(diff[1].path, `/original/${row.id}/app/more.py`);
        const content = await vscodeMock_1.calls.providers.get("devagent").provideTextDocumentContent(diff[1]);
        assert.equal(content, "", "a file created by the task has an empty original side");
        assert.deepEqual(vscodeMock_1.calls.errors, []);
    }
    finally {
        await ext.deactivate();
        await env.close();
    }
});
(0, node_test_1.test)("a protected-file approval shows a modal and the answer reaches the engine", async () => {
    const read = JSON.stringify({ tool: "read_file", args: { path: "app/money.py" } });
    const change = JSON.stringify({ tool: "edit_files", args: { edits: [{ path: "app/money.py", replacements: [{ old: "1", new: "2" }] }] } });
    const env = await env_1.Env.create([(0, env_1.PLAN)({ files_add: [], files_edit: ["app/money.py"], steps: [{ title: "x", files: ["app/money.py"] }] }), read, change, env_1.DONE], false);
    const ext = require("../extension");
    try {
        vscodeMock_1.answers.info.push("Approve and run");
        vscodeMock_1.answers.warning.push("Deny");
        await boot(ext, env);
        vscodeMock_1.answers.input.push("change balance");
        await vscodeMock_1.calls.commands.get("devAgent.newTask")?.();
        const warn = await (0, env_1.until)(() => vscodeMock_1.calls.warnings.find((w) => String(w[0]).includes("approval")), 30000, "approval modal");
        assert.equal(warn[1].modal, true);
        assert.match(warn[1].detail, /PROTECTED/);
        assert.deepEqual(warn.slice(2), ["Approve", "Deny"]);
        await (0, env_1.until)(() => vscodeMock_1.calls.trees.get("devAgent.tasks").getChildren()[0]?.status === "completed" || vscodeMock_1.calls.trees.get("devAgent.tasks").getChildren()[0]?.status === "stopped", 30000, "task end");
        const fs = require("node:fs");
        assert.equal(fs.readFileSync(`${env.project}/app/money.py`, "utf8"), "BALANCE = 1\n", "denied: the protected file is untouched");
    }
    finally {
        await ext.deactivate();
        await env.close();
    }
});
(0, node_test_1.test)("deactivate stops the hidden server process", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)()], false);
    const ext = require("../extension");
    try {
        await boot(ext, env);
        const { execFileSync } = require("node:child_process");
        const before = execFileSync("pgrep", ["-f", `dev_agent --root ${env.project} serve`]).toString().trim().split("\n").map(Number);
        assert.ok(before.length >= 1);
        await ext.deactivate();
        await (0, env_1.until)(() => before.every((pid) => !(0, env_1.alive)(pid)), 10000, "server to be gone");
    }
    finally {
        await env.close();
    }
});
