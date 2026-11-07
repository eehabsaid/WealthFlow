import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import type { AgentClient } from "./client";
import type { Log } from "./log";
import { findPython } from "./pythonFinder";
import { ServerProcess } from "./serverProcess";
import type { Status as Poller } from "./status";

export type Status = "stopped" | "starting" | "running" | "error";

// Owns the hidden Python server for this window: finds Python, starts it, restarts it on request, stops it on exit. No manual steps for the user.
export class ServerManager {
  status: Status = "stopped";
  error = "";
  private server = new ServerProcess();
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onStatus = this.emitter.event;
  private stopping = false;

  constructor(
    private readonly log: Log,
    private readonly poller: Poller,
  ) {}

  get client(): AgentClient | undefined {
    return this.server.client;
  }

  settings(): { projectRoot: string | undefined; agentPath: string; pythonPath: string } {
    const cfg = vscode.workspace.getConfiguration("devAgent");
    const projectRoot = cfg.get<string>("projectRoot")?.trim() || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    return { projectRoot, agentPath: cfg.get<string>("agentPath")?.trim() || projectRoot || "", pythonPath: cfg.get<string>("pythonPath") ?? "" };
  }

  private set(status: Status, error = ""): void {
    this.status = status;
    this.error = error;
    void vscode.commands.executeCommand("setContext", "devAgent.connected", status === "running");
    this.emitter.fire();
  }

  async start(): Promise<void> {
    if (this.status === "starting" || this.status === "running") return;
    const { projectRoot, agentPath, pythonPath } = this.settings();
    if (!projectRoot) return this.set("error", "Open a project folder first (the folder that contains dev_agent).");
    this.set("starting");
    this.stopping = false;
    try {
      if (!fs.existsSync(path.join(agentPath, "dev_agent", "__init__.py"))) throw new Error(`dev_agent was not found in ${agentPath}. Set "devAgent.agentPath" to the folder that contains the dev_agent package.`);
      const python = await findPython(projectRoot, pythonPath, agentPath);
      this.log.line(`starting the agent server with ${[python.command, ...python.args].join(" ")} in ${agentPath}`);
      this.server = new ServerProcess();
      this.server.onExit = (code) => {
        if (this.stopping) return;
        this.log.line(`the agent server stopped unexpectedly (code ${code})`);
        this.set("error", `The agent server stopped unexpectedly (code ${code}). Use "dev_agent: Restart server".`);
      };
      await this.server.start({ python, projectRoot, agentPath, log: (l) => this.log.line(l) });
      this.poller.start();
      this.set("running");
      this.log.line(`agent server ready on 127.0.0.1:${this.server.client?.port}`);
    } catch (error) {
      this.log.line(`cannot start the agent server: ${(error as Error).message}`);
      this.set("error", (error as Error).message);
    }
  }

  async stop(): Promise<void> {
    this.stopping = true;
    this.poller.reset();
    await this.server.stop();
    this.set("stopped");
  }

  async restart(): Promise<void> {
    await this.stop();
    await this.start();
  }
}
