import * as assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { test } from "node:test";
import { AgentClient, ApiError } from "../client";
import { candidates, findPython } from "../pythonFinder";
import { ServerProcess } from "../serverProcess";
import { AGENT, alive, Env, PLAN, PYTHON, REPO, until } from "./env";

test("starts the hidden server, authenticates, and stops it completely", async () => {
  const env = await Env.create([PLAN()]);
  try {
    const health = await env.client.health();
    assert.equal(health.ok, true);
    const bad = new AgentClient(env.client.port, "x".repeat(40));
    await assert.rejects(bad.health(), (e: unknown) => e instanceof ApiError && e.status === 401);
    assert.ok(!env.logs.join("\n").includes("DEV_AGENT_TOKEN"), "the token must not appear in logs");
    const pid = health.pid;
    await env.server.stop();
    await until(() => !alive(pid), 8000, "server process to exit");
    await assert.rejects(env.client.health());
  } finally {
    await env.close();
  }
});

test("the server exits by itself when its parent (the editor) disappears", async () => {
  const env = await Env.create([PLAN()]);
  const parent = spawn(process.execPath, ["-e", "setTimeout(() => {}, 1200)"]);
  const server = new ServerProcess();
  try {
    const python = await findPython(env.project, PYTHON, REPO);
    // start a second server whose --parent-pid is the short-lived node process
    const { spawn: sp } = await import("node:child_process");
    const child = sp(python.command, ["-m", "ai.dev_agent", "--root", env.project, "serve", "--parent-pid", String(parent.pid)], {
      cwd: AGENT + "/..",
      env: { ...process.env, DEV_AGENT_TOKEN: "t".repeat(40) },
      stdio: "ignore",
    });
    assert.ok(child.pid);
    await until(() => !alive(child.pid as number), 15000, "orphaned server to stop");
  } finally {
    await server.stop();
    await env.close();
  }
});

test("python discovery: order of candidates and a helpful error", async () => {
  assert.deepEqual(candidates("/nowhere", "C:/py/python.exe", "win32")[0], { command: "C:/py/python.exe", args: [] });
  assert.deepEqual(candidates("/nowhere", "", "win32").slice(0, 2), [
    { command: "py", args: ["-3.12"] },
    { command: "py", args: ["-3"] },
  ]);
  await assert.rejects(findPython("/nowhere", "/definitely/not/python", "/tmp"), /Set "devAgent.pythonPath"/);
});
