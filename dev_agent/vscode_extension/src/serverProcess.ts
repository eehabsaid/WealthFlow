import { ChildProcess, execFile, spawn } from "node:child_process";
import * as crypto from "node:crypto";
import { AgentClient } from "./client";
import type { PythonCommand } from "./pythonFinder";

export interface ServerOptions {
  python: PythonCommand;
  projectRoot: string;
  agentPath: string; // folder that contains the dev_agent package; the server starts there
  log: (line: string) => void;
  startTimeoutMs?: number;
}

// Starts and owns the hidden `python -m dev_agent serve` process. The token goes in through the environment (never argv, never logged);
// the port comes back on stdout. The server also watches this process's pid and exits by itself if the editor disappears.
export class ServerProcess {
  private child: ChildProcess | undefined;
  client: AgentClient | undefined;
  onExit: (code: number | null) => void = () => undefined;

  get running(): boolean {
    return this.child !== undefined && this.child.exitCode === null && this.client !== undefined;
  }

  async start(opts: ServerOptions): Promise<AgentClient> {
    if (this.running) return this.client as AgentClient;
    const token = crypto.randomBytes(32).toString("hex");
    const args = [...opts.python.args, "-m", "dev_agent", "--root", opts.projectRoot, "serve", "--parent-pid", String(process.pid)];
    const child = spawn(opts.python.command, args, {
      cwd: opts.agentPath,
      env: { ...process.env, DEV_AGENT_TOKEN: token, PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8" },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
      detached: process.platform !== "win32", // own process group on POSIX so the whole tree can be signalled
    });
    this.child = child;
    child.stderr?.setEncoding("utf8").on("data", (t: string) => t.split(/\r?\n/).filter(Boolean).forEach((l) => opts.log(`[server] ${l}`)));
    const port = await new Promise<number>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("the agent server did not report a port in time")), opts.startTimeoutMs ?? 20000);
      let buffer = "";
      child.stdout?.setEncoding("utf8").on("data", (t: string) => {
        buffer += t;
        for (let nl = buffer.indexOf("\n"); nl >= 0; nl = buffer.indexOf("\n")) {
          const line = buffer.slice(0, nl).trim();
          buffer = buffer.slice(nl + 1);
          try {
            const msg = JSON.parse(line) as { event?: string; port?: number };
            if (msg.event === "listening" && typeof msg.port === "number") {
              clearTimeout(timer);
              resolve(msg.port);
            }
          } catch {
            opts.log(`[server] ${line}`);
          }
        }
      });
      child.once("error", (e) => reject(new Error(`cannot start Python: ${e.message}`)));
      child.once("exit", (code) => reject(new Error(`the agent server exited during start (code ${code}); see the Output channel`)));
    }).catch(async (error: Error) => {
      await this.kill();
      throw error;
    });
    child.on("exit", (code) => {
      opts.log(`[server] exited (code ${code})`);
      this.client = undefined;
      this.onExit(code);
    });
    this.client = new AgentClient(port, token);
    return this.client;
  }

  // Ask politely (the server stops running commands and exits), then make sure: the whole tree is killed if it is still there.
  async stop(): Promise<void> {
    const child = this.child;
    if (!child) return;
    try {
      await this.client?.shutdown();
    } catch {
      /* already gone or unreachable: fall through to the hard kill */
    }
    if (child.exitCode === null) await this.waitExit(child, 6000);
    await this.kill();
    this.client = undefined;
  }

  private waitExit(child: ChildProcess, ms: number): Promise<void> {
    return new Promise((resolve) => {
      if (child.exitCode !== null) return resolve();
      const timer = setTimeout(resolve, ms);
      child.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
    });
  }

  async kill(): Promise<void> {
    const child = this.child;
    if (!child || child.pid === undefined || child.exitCode !== null) return;
    if (process.platform === "win32") {
      await new Promise<void>((resolve) => execFile("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true }, () => resolve()));
    } else {
      try {
        process.kill(-child.pid, "SIGKILL");
      } catch {
        child.kill("SIGKILL");
      }
    }
    await this.waitExit(child, 3000);
  }
}
