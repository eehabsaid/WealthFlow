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
exports.candidates = candidates;
exports.findPython = findPython;
const node_child_process_1 = require("node:child_process");
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
function run(cmd, extra, cwd) {
    return new Promise((resolve) => {
        (0, node_child_process_1.execFile)(cmd.command, [...cmd.args, ...extra], { cwd, timeout: 15000, windowsHide: true }, (error, stdout, stderr) => resolve({ ok: !error, out: `${stdout}${stderr}`.trim() }));
    });
}
function candidates(root, configured, platform = process.platform) {
    const list = [];
    if (configured.trim())
        list.push({ command: configured.trim(), args: [] });
    for (const venv of [".venv", "venv", "env"]) {
        const exe = platform === "win32" ? path.join(root, venv, "Scripts", "python.exe") : path.join(root, venv, "bin", "python");
        if (fs.existsSync(exe))
            list.push({ command: exe, args: [] });
    }
    if (platform === "win32")
        list.push({ command: "py", args: ["-3.12"] }, { command: "py", args: ["-3"] }, { command: "python", args: [] });
    else
        list.push({ command: "python3", args: [] }, { command: "python", args: [] });
    return list;
}
// The first interpreter (Python 3.10+) that can import dev_agent from the project folder. The error says what was tried.
async function findPython(root, configured, agentPath) {
    const tried = [];
    const probe = "import sys; assert sys.version_info >= (3, 10); import dev_agent";
    for (const cmd of candidates(root, configured)) {
        const label = [cmd.command, ...cmd.args].join(" ");
        const result = await run(cmd, ["-c", probe], agentPath);
        if (result.ok)
            return cmd;
        tried.push(`${label}: ${result.out.split("\n").pop() || "failed"}`);
    }
    throw new Error(`No Python 3.10+ that can import dev_agent from ${agentPath}.\nSet "devAgent.pythonPath" (for example your project's venv python).\nTried:\n  ${tried.join("\n  ")}`);
}
