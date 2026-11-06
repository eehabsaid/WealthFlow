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
exports.ServerProcess = void 0;
const node_child_process_1 = require("node:child_process");
const crypto = __importStar(require("node:crypto"));
const client_1 = require("./client");
// Starts and owns the hidden `python -m dev_agent serve` process. The token goes in through the environment (never argv, never logged);
// the port comes back on stdout. The server also watches this process's pid and exits by itself if the editor disappears.
class ServerProcess {
    child;
    client;
    onExit = () => undefined;
    get running() {
        return this.child !== undefined && this.child.exitCode === null && this.client !== undefined;
    }
    async start(opts) {
        if (this.running)
            return this.client;
        const token = crypto.randomBytes(32).toString("hex");
        const args = [...opts.python.args, "-m", "dev_agent", "--root", opts.projectRoot, "serve", "--parent-pid", String(process.pid)];
        const child = (0, node_child_process_1.spawn)(opts.python.command, args, {
            cwd: opts.agentPath,
            env: { ...process.env, DEV_AGENT_TOKEN: token, PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8" },
            stdio: ["ignore", "pipe", "pipe"],
            windowsHide: true,
            detached: process.platform !== "win32", // own process group on POSIX so the whole tree can be signalled
        });
        this.child = child;
        child.stderr?.setEncoding("utf8").on("data", (t) => t.split(/\r?\n/).filter(Boolean).forEach((l) => opts.log(`[server] ${l}`)));
        const port = await new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error("the agent server did not report a port in time")), opts.startTimeoutMs ?? 20000);
            let buffer = "";
            child.stdout?.setEncoding("utf8").on("data", (t) => {
                buffer += t;
                for (let nl = buffer.indexOf("\n"); nl >= 0; nl = buffer.indexOf("\n")) {
                    const line = buffer.slice(0, nl).trim();
                    buffer = buffer.slice(nl + 1);
                    try {
                        const msg = JSON.parse(line);
                        if (msg.event === "listening" && typeof msg.port === "number") {
                            clearTimeout(timer);
                            resolve(msg.port);
                        }
                    }
                    catch {
                        opts.log(`[server] ${line}`);
                    }
                }
            });
            child.once("error", (e) => reject(new Error(`cannot start Python: ${e.message}`)));
            child.once("exit", (code) => reject(new Error(`the agent server exited during start (code ${code}); see the Output channel`)));
        }).catch(async (error) => {
            await this.kill();
            throw error;
        });
        child.on("exit", (code) => {
            opts.log(`[server] exited (code ${code})`);
            this.client = undefined;
            this.onExit(code);
        });
        this.client = new client_1.AgentClient(port, token);
        return this.client;
    }
    // Ask politely (the server stops running commands and exits), then make sure: the whole tree is killed if it is still there.
    async stop() {
        const child = this.child;
        if (!child)
            return;
        try {
            await this.client?.shutdown();
        }
        catch {
            /* already gone or unreachable: fall through to the hard kill */
        }
        if (child.exitCode === null)
            await this.waitExit(child, 6000);
        await this.kill();
        this.client = undefined;
    }
    waitExit(child, ms) {
        return new Promise((resolve) => {
            if (child.exitCode !== null)
                return resolve();
            const timer = setTimeout(resolve, ms);
            child.once("exit", () => {
                clearTimeout(timer);
                resolve();
            });
        });
    }
    async kill() {
        const child = this.child;
        if (!child || child.pid === undefined || child.exitCode !== null)
            return;
        if (process.platform === "win32") {
            await new Promise((resolve) => (0, node_child_process_1.execFile)("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true }, () => resolve()));
        }
        else {
            try {
                process.kill(-child.pid, "SIGKILL");
            }
            catch {
                child.kill("SIGKILL");
            }
        }
        await this.waitExit(child, 3000);
    }
}
exports.ServerProcess = ServerProcess;
