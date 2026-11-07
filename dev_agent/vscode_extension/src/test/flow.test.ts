import * as assert from "node:assert/strict";
import { test } from "node:test";
import type { AgentEvent, TaskDetail } from "../types";
import { DONE, Env, PLAN, reply, until, WRITE } from "./env";

test("plan -> approve -> run -> files, diff sources, events, through the client and store", async () => {
  const env = await Env.create([PLAN(), WRITE, DONE]);
  try {
    const ready: TaskDetail[] = [];
    env.store.onPlanReady = (t) => ready.push(t);
    env.store.start(300);
    const id = await env.client.startTask("add more");
    env.store.expect(id);
    env.store.select(id);
    await until(() => env.store.task?.status === "awaiting_approval", 15000, "plan");
    await until(() => ready.length === 1, 5000, "plan-ready callback");
    assert.equal(env.store.task?.plan?.summary, "test plan");
    await env.client.approvePlan(id);
    await until(() => env.store.task?.status === "completed", 20000, "completion");
    assert.deepEqual(env.store.files.map((f) => [f.path, f.state]), [["app/more.py", "written"]]);
    assert.equal(await env.client.fileText(id, "app/more.py", "current"), "X = 1\n");
    await assert.rejects(env.client.fileText(id, "app/more.py", "original"), /not found|no original/i);
    const kinds = env.store.events.map((e) => e.type);
    assert.ok(kinds.includes("package") && kinds.includes("verify") && kinds[kinds.length - 1] === "done");
    assert.deepEqual(env.store.events.map((e) => e.seq), env.store.events.map((_, i) => i + 1), "no gaps, no repeats");
    assert.match(await env.client.report(id), /Status: COMPLETED/);
    await until(() => env.store.state?.busy === false, 5000, "idle");
  } finally {
    await env.close();
  }
});

test("event stream resumes after a given sequence number", async () => {
  const env = await Env.create([PLAN()]);
  try {
    const id = await env.client.startTask("t");
    await until(async () => (await env.client.task(id)).status === "awaiting_approval", 15000, "plan");
    const got: AgentEvent[] = [];
    const sub = env.client.subscribe(id, 2, (e) => got.push(e));
    await until(() => got.length > 0, 5000, "events");
    sub.close();
    assert.equal(got[0].seq, 3);
  } finally {
    await env.close();
  }
});

test("Stop over the API kills the running command's whole tree", async () => {
  const slow = reply({ tool: "run_command", args: { command: "python -m pytest -q -p no:cacheprovider tests/test_slow.py", reason: "slow" } });
  const env = await Env.create([PLAN({ files_add: [], files_edit: ["app/calc.py"] }), slow, DONE]);
  try {
    const id = await env.client.startTask("t");
    await until(async () => (await env.client.task(id)).status === "awaiting_approval", 15000, "plan");
    await env.client.approvePlan(id);
    await until(async () => (await env.client.state()).busy, 5000, "busy");
    await new Promise((r) => setTimeout(r, 1500));
    const started = Date.now();
    assert.equal(await env.client.stop(), true);
    await until(async () => !(await env.client.state()).busy, 15000, "idle after stop");
    assert.ok(Date.now() - started < 12000);
    const task = await env.client.task(id);
    assert.equal(task.status, "stopped");
    assert.match(task.stop_reason, /stopped by user/);
  } finally {
    await env.close();
  }
});
