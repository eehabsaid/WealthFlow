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
exports.Env = exports.DONE = exports.WRITE = exports.PLAN = exports.PYTHON = exports.AGENT = exports.REPO = void 0;
exports.reply = reply;
exports.until = until;
exports.alive = alive;
const node_child_process_1 = require("node:child_process");
const fs = __importStar(require("node:fs"));
const os = __importStar(require("node:os"));
const path = __importStar(require("node:path"));
const pythonFinder_1 = require("../pythonFinder");
const serverProcess_1 = require("../serverProcess");
exports.REPO = path.resolve(__dirname, "../../../..");
exports.AGENT = path.join(exports.REPO, "dev_agent");
exports.PYTHON = process.env.DEV_AGENT_TEST_PYTHON ?? "python3";
function reply(value) {
    return JSON.stringify(value);
}
const PLAN = (extra = {}) => reply({
    plan: {
        summary: "test plan",
        steps: [{ title: "go", files: ["app/more.py"] }],
        files_add: ["app/more.py"],
        files_edit: [],
        files_delete: [],
        files_rename: [],
        tests: [],
        risks: [],
        ...extra,
    },
});
exports.PLAN = PLAN;
exports.WRITE = reply({ tool: "edit_files", args: { edits: [{ path: "app/more.py", content: "X = 1\n" }] } });
exports.DONE = reply({ final: "done" });
// A throw-away project + fake Ollama (script of replies) and the real `dev_agent serve` on top of them, all torn down by close().
class Env {
    fake;
    server = new serverProcess_1.ServerProcess();
    logs = [];
    project = "";
    client;
    static async create(script, startServer = true) {
        const env = new Env();
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "devagent-ext-"));
        env.project = path.join(dir, "project");
        fs.mkdirSync(env.project);
        const scriptFile = path.join(dir, "script.json");
        fs.writeFileSync(scriptFile, JSON.stringify(script));
        env.fake = (0, node_child_process_1.spawn)(exports.PYTHON, ["-m", "dev_agent.tests.fake_env", env.project, scriptFile], { cwd: exports.REPO, stdio: ["ignore", "pipe", "inherit"] });
        await new Promise((resolve, reject) => {
            env.fake?.stdout?.once("data", () => resolve());
            env.fake?.once("exit", () => reject(new Error("fake_env exited")));
        });
        if (!startServer)
            return env;
        const python = await (0, pythonFinder_1.findPython)(env.project, exports.PYTHON, exports.REPO);
        env.client = await env.server.start({ python, projectRoot: env.project, agentPath: exports.REPO, log: (l) => env.logs.push(l) });
        return env;
    }
    async close() {
        await this.server.stop();
        this.fake?.kill("SIGKILL");
    }
}
exports.Env = Env;
async function until(fn, ms = 15000, what = "condition") {
    const end = Date.now() + ms;
    for (;;) {
        const value = await fn();
        if (value)
            return value;
        if (Date.now() > end)
            throw new Error(`timed out waiting for ${what}`);
        await new Promise((r) => setTimeout(r, 50));
    }
}
function alive(pid) {
    try {
        process.kill(pid, 0);
        return true;
    }
    catch {
        return false;
    }
}
