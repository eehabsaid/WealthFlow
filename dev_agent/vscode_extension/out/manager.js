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
exports.ServerManager = void 0;
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const vscode = __importStar(require("vscode"));
const pythonFinder_1 = require("./pythonFinder");
const serverProcess_1 = require("./serverProcess");
// Owns the hidden Python server for this window: finds Python, starts it, restarts it on request, stops it on exit. No manual steps for the user.
class ServerManager {
    log;
    poller;
    status = "stopped";
    error = "";
    server = new serverProcess_1.ServerProcess();
    emitter = new vscode.EventEmitter();
    onStatus = this.emitter.event;
    stopping = false;
    constructor(log, poller) {
        this.log = log;
        this.poller = poller;
    }
    get client() {
        return this.server.client;
    }
    settings() {
        const cfg = vscode.workspace.getConfiguration("devAgent");
        const projectRoot = cfg.get("projectRoot")?.trim() || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        return { projectRoot, agentPath: cfg.get("agentPath")?.trim() || projectRoot || "", pythonPath: cfg.get("pythonPath") ?? "" };
    }
    set(status, error = "") {
        this.status = status;
        this.error = error;
        void vscode.commands.executeCommand("setContext", "devAgent.connected", status === "running");
        this.emitter.fire();
    }
    async start() {
        if (this.status === "starting" || this.status === "running")
            return;
        const { projectRoot, agentPath, pythonPath } = this.settings();
        if (!projectRoot)
            return this.set("error", "Open a project folder first (the folder that contains dev_agent).");
        this.set("starting");
        this.stopping = false;
        try {
            if (!fs.existsSync(path.join(agentPath, "dev_agent", "__init__.py")))
                throw new Error(`dev_agent was not found in ${agentPath}. Set "devAgent.agentPath" to the folder that contains the dev_agent package.`);
            const python = await (0, pythonFinder_1.findPython)(projectRoot, pythonPath, agentPath);
            this.log.line(`starting the agent server with ${[python.command, ...python.args].join(" ")} in ${agentPath}`);
            this.server = new serverProcess_1.ServerProcess();
            this.server.onExit = (code) => {
                if (this.stopping)
                    return;
                this.log.line(`the agent server stopped unexpectedly (code ${code})`);
                this.set("error", `The agent server stopped unexpectedly (code ${code}). Use "dev_agent: Restart server".`);
            };
            await this.server.start({ python, projectRoot, agentPath, log: (l) => this.log.line(l) });
            this.poller.start();
            this.set("running");
            this.log.line(`agent server ready on 127.0.0.1:${this.server.client?.port}`);
        }
        catch (error) {
            this.log.line(`cannot start the agent server: ${error.message}`);
            this.set("error", error.message);
        }
    }
    async stop() {
        this.stopping = true;
        this.poller.reset();
        await this.server.stop();
        this.set("stopped");
    }
    async restart() {
        await this.stop();
        await this.start();
    }
}
exports.ServerManager = ServerManager;
