import * as assert from "node:assert/strict";
import { test } from "node:test";
import { answers, calls, config, state } from "./vscodeMock"; // must be imported before the extension: it installs the fake `vscode`
import { Env, DONE, PLAN, PYTHON, REPO, WRITE, alive, until } from "./env";

type Ext = typeof import("../extension");

// Activate the extension against a project and wait until its hidden server is up; fail fast (with the reason) if it goes offline instead.
async function boot(ext: Ext, env: Env): Promise<void> {
  state.folder = env.project;
  config.pythonPath = PYTHON;
  config.agentPath = REPO;
  calls.contexts.delete("devAgent.connected");
  ext.activate({ subscriptions: [] } as never);
  await until(() => {
    if (/offline/.test(state.statusItem.text)) throw new Error(`the extension went offline: ${String(state.statusItem.tooltip)}`);
    return calls.contexts.get("devAgent.connected") === true;
  }, 30000, "server to start");
}

test("the whole extension against a real agent server: start, task, plan dialog, run, tree views, diff, stop on deactivate", async () => {
  const env = await Env.create([PLAN(), WRITE, DONE], false);
  const ext = require("../extension") as typeof import("../extension");
  try {
    answers.info.push("Approve and run"); // the plan-ready modal
    await boot(ext, env);
    assert.match(state.statusItem.text, /dev_agent/);

    answers.input.push("add more");
    await calls.commands.get("devAgent.newTask")?.();
    const tasks = calls.trees.get("devAgent.tasks");
    const row = await until(() => tasks.getChildren()[0], 10000, "task row");
    assert.equal(tasks.getTreeItem(row).command.command, "devAgent.selectTask");
    await calls.commands.get("devAgent.selectTask")?.(row.id);

    await until(() => calls.infos.length > 0, 20000, "plan-ready dialog");
    assert.equal(calls.infos[0][0], "The plan is ready for your review");
    assert.match((calls.infos[0][1] as { detail: string }).detail, /Add: app\/more\.py/);
    assert.equal(calls.infos[0][1].modal, true);

    const files = calls.trees.get("devAgent.files");
    await until(() => files.getChildren().length === 1, 25000, "changed file after the run");
    assert.equal(files.getTreeItem(files.getChildren()[0]).description, "written");
    const plan = calls.trees.get("devAgent.plan");
    assert.ok(plan.getChildren().some((n: { label: string }) => n.label.startsWith("Add")));
    const progress = calls.trees.get("devAgent.progress");
    const labels = (): string[] => progress.getChildren().map((r: { label: string }) => r.label);
    await until(() => labels().some((l) => l.startsWith("Finished: completed")), 15000, "the finished row");
    assert.ok(progress.getChildren().some((r: { children?: unknown[] }) => (r.children?.length ?? 0) > 0), "tool calls are grouped under their package");

    await calls.commands.get("devAgent.openDiff")?.("app/more.py");
    const diff = calls.executed.find((c) => c[0] === "vscode.diff");
    assert.ok(diff, "native diff editor must be opened");
    assert.equal(diff[1].path, `/original/${row.id}/app/more.py`);
    const content = await calls.providers.get("devagent").provideTextDocumentContent(diff[1]);
    assert.equal(content, "", "a file created by the task has an empty original side");

    assert.deepEqual(calls.errors, []);
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("a protected-file approval shows a modal and the answer reaches the engine", async () => {
  const read = JSON.stringify({ tool: "read_file", args: { path: "app/money.py" } });
  const change = JSON.stringify({ tool: "edit_files", args: { edits: [{ path: "app/money.py", replacements: [{ old: "1", new: "2" }] }] } });
  const env = await Env.create([PLAN({ files_add: [], files_edit: ["app/money.py"], steps: [{ title: "x", files: ["app/money.py"] }] }), read, change, DONE], false);
  const ext = require("../extension") as typeof import("../extension");
  try {
    answers.info.push("Approve and run");
    answers.warning.push("Deny");
    await boot(ext, env);
    answers.input.push("change balance");
    await calls.commands.get("devAgent.newTask")?.();
    const warn = await until(() => calls.warnings.find((w) => String(w[0]).includes("approval")), 30000, "approval modal");
    assert.equal(warn[1].modal, true);
    assert.match(warn[1].detail, /PROTECTED/);
    assert.deepEqual(warn.slice(2), ["Approve", "Deny"]);
    await until(() => calls.trees.get("devAgent.tasks").getChildren()[0]?.status === "completed" || calls.trees.get("devAgent.tasks").getChildren()[0]?.status === "stopped", 30000, "task end");
    const fs = require("node:fs") as typeof import("node:fs");
    assert.equal(fs.readFileSync(`${env.project}/app/money.py`, "utf8"), "BALANCE = 1\n", "denied: the protected file is untouched");
  } finally {
    await ext.deactivate();
    await env.close();
  }
});

test("deactivate stops the hidden server process", async () => {
  const env = await Env.create([PLAN()], false);
  const ext = require("../extension") as typeof import("../extension");
  try {
    await boot(ext, env);
    const { execFileSync } = require("node:child_process") as typeof import("node:child_process");
    const before = execFileSync("pgrep", ["-f", `dev_agent --root ${env.project} serve`]).toString().trim().split("\n").map(Number);
    assert.ok(before.length >= 1);
    await ext.deactivate();
    await until(() => before.every((pid) => !alive(pid)), 10000, "server to be gone");
  } finally {
    await env.close();
  }
});
