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
const env_1 = require("./env");
(0, node_test_1.test)("plan -> approve -> run -> files, diff sources, events, through the client and store", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)(), env_1.WRITE, env_1.DONE]);
    try {
        const ready = [];
        env.store.onPlanReady = (t) => ready.push(t);
        env.store.start(300);
        const id = await env.client.startTask("add more");
        env.store.expect(id);
        env.store.select(id);
        await (0, env_1.until)(() => env.store.task?.status === "awaiting_approval", 15000, "plan");
        await (0, env_1.until)(() => ready.length === 1, 5000, "plan-ready callback");
        assert.equal(env.store.task?.plan?.summary, "test plan");
        await env.client.approvePlan(id);
        await (0, env_1.until)(() => env.store.task?.status === "completed", 20000, "completion");
        assert.deepEqual(env.store.files.map((f) => [f.path, f.state]), [["app/more.py", "written"]]);
        assert.equal(await env.client.fileText(id, "app/more.py", "current"), "X = 1\n");
        await assert.rejects(env.client.fileText(id, "app/more.py", "original"), /not found|no original/i);
        const kinds = env.store.events.map((e) => e.type);
        assert.ok(kinds.includes("package") && kinds.includes("verify") && kinds[kinds.length - 1] === "done");
        assert.deepEqual(env.store.events.map((e) => e.seq), env.store.events.map((_, i) => i + 1), "no gaps, no repeats");
        assert.match(await env.client.report(id), /Status: COMPLETED/);
        await (0, env_1.until)(() => env.store.state?.busy === false, 5000, "idle");
    }
    finally {
        await env.close();
    }
});
(0, node_test_1.test)("event stream resumes after a given sequence number", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)()]);
    try {
        const id = await env.client.startTask("t");
        await (0, env_1.until)(async () => (await env.client.task(id)).status === "awaiting_approval", 15000, "plan");
        const got = [];
        const sub = env.client.subscribe(id, 2, (e) => got.push(e));
        await (0, env_1.until)(() => got.length > 0, 5000, "events");
        sub.close();
        assert.equal(got[0].seq, 3);
    }
    finally {
        await env.close();
    }
});
(0, node_test_1.test)("Stop over the API kills the running command's whole tree", async () => {
    const slow = (0, env_1.reply)({ tool: "run_command", args: { command: "python -m pytest -q -p no:cacheprovider tests/test_slow.py", reason: "slow" } });
    const env = await env_1.Env.create([(0, env_1.PLAN)({ files_add: [], files_edit: ["app/calc.py"] }), slow, env_1.DONE]);
    try {
        const id = await env.client.startTask("t");
        await (0, env_1.until)(async () => (await env.client.task(id)).status === "awaiting_approval", 15000, "plan");
        await env.client.approvePlan(id);
        await (0, env_1.until)(async () => (await env.client.state()).busy, 5000, "busy");
        await new Promise((r) => setTimeout(r, 1500));
        const started = Date.now();
        assert.equal(await env.client.stop(), true);
        await (0, env_1.until)(async () => !(await env.client.state()).busy, 15000, "idle after stop");
        assert.ok(Date.now() - started < 12000);
        const task = await env.client.task(id);
        assert.equal(task.status, "stopped");
        assert.match(task.stop_reason, /stopped by user/);
    }
    finally {
        await env.close();
    }
});
