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
const node_child_process_1 = require("node:child_process");
const node_test_1 = require("node:test");
const client_1 = require("../client");
const pythonFinder_1 = require("../pythonFinder");
const serverProcess_1 = require("../serverProcess");
const env_1 = require("./env");
(0, node_test_1.test)("starts the hidden server, authenticates, and stops it completely", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)()]);
    try {
        const health = await env.client.health();
        assert.equal(health.ok, true);
        const bad = new client_1.AgentClient(env.client.port, "x".repeat(40));
        await assert.rejects(bad.health(), (e) => e instanceof client_1.ApiError && e.status === 401);
        assert.ok(!env.logs.join("\n").includes("DEV_AGENT_TOKEN"), "the token must not appear in logs");
        const pid = health.pid;
        await env.server.stop();
        await (0, env_1.until)(() => !(0, env_1.alive)(pid), 8000, "server process to exit");
        await assert.rejects(env.client.health());
    }
    finally {
        await env.close();
    }
});
(0, node_test_1.test)("the server exits by itself when its parent (the editor) disappears", async () => {
    const env = await env_1.Env.create([(0, env_1.PLAN)()]);
    const parent = (0, node_child_process_1.spawn)(process.execPath, ["-e", "setTimeout(() => {}, 1200)"]);
    const server = new serverProcess_1.ServerProcess();
    try {
        const python = await (0, pythonFinder_1.findPython)(env.project, env_1.PYTHON, env_1.REPO);
        // start a second server whose --parent-pid is the short-lived node process
        const { spawn: sp } = await import("node:child_process");
        const child = sp(python.command, ["-m", "dev_agent", "--root", env.project, "serve", "--parent-pid", String(parent.pid)], {
            cwd: env_1.AGENT + "/..",
            env: { ...process.env, DEV_AGENT_TOKEN: "t".repeat(40) },
            stdio: "ignore",
        });
        assert.ok(child.pid);
        await (0, env_1.until)(() => !(0, env_1.alive)(child.pid), 15000, "orphaned server to stop");
    }
    finally {
        await server.stop();
        await env.close();
    }
});
(0, node_test_1.test)("python discovery: order of candidates and a helpful error", async () => {
    assert.deepEqual((0, pythonFinder_1.candidates)("/nowhere", "C:/py/python.exe", "win32")[0], { command: "C:/py/python.exe", args: [] });
    assert.deepEqual((0, pythonFinder_1.candidates)("/nowhere", "", "win32").slice(0, 2), [
        { command: "py", args: ["-3.12"] },
        { command: "py", args: ["-3"] },
    ]);
    await assert.rejects((0, pythonFinder_1.findPython)("/nowhere", "/definitely/not/python", "/tmp"), /Set "devAgent.pythonPath"/);
});
