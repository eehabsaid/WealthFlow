import { ChildProcess, spawn } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { AgentClient } from "../client";
import { findPython } from "../pythonFinder";
import { ServerProcess } from "../serverProcess";
import { Store } from "../state";

export const REPO = path.resolve(__dirname, "../../../..");
export const AGENT = path.join(REPO, "dev_agent");
export const PYTHON = process.env.DEV_AGENT_TEST_PYTHON ?? "python3";

export function reply(value: unknown): string {
  return JSON.stringify(value);
}

export const PLAN = (extra: Record<string, unknown> = {}): string =>
  reply({
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

export const WRITE = reply({ tool: "edit_files", args: { edits: [{ path: "app/more.py", content: "X = 1\n" }] } });
export const DONE = reply({ final: "done" });

// A throw-away project + fake Ollama (script of replies), the real `dev_agent serve` on top of them, and a Store, all torn down by close().
export class Env {
  fake: ChildProcess | undefined;
  server = new ServerProcess();
  logs: string[] = [];
  project = "";
  client!: AgentClient;
  store = new Store(() => this.server.client);

  static async create(script: unknown[], startServer = true): Promise<Env> {
    const env = new Env();
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "devagent-ext-"));
    env.project = path.join(dir, "project");
    fs.mkdirSync(env.project);
    const scriptFile = path.join(dir, "script.json");
    fs.writeFileSync(scriptFile, JSON.stringify(script));
    env.fake = spawn(PYTHON, ["-m", "dev_agent.tests.fake_env", env.project, scriptFile], { cwd: REPO, stdio: ["ignore", "pipe", "inherit"] });
    await new Promise<void>((resolve, reject) => {
      env.fake?.stdout?.once("data", () => resolve());
      env.fake?.once("exit", () => reject(new Error("fake_env exited")));
    });
    if (!startServer) return env;
    const python = await findPython(env.project, PYTHON, REPO);
    env.client = await env.server.start({ python, projectRoot: env.project, agentPath: REPO, log: (l) => env.logs.push(l) });
    return env;
  }

  async close(): Promise<void> {
    this.store.stop();
    await this.server.stop();
    this.fake?.kill("SIGKILL");
  }
}

export async function until<T>(fn: () => T | Promise<T>, ms = 15000, what = "condition"): Promise<NonNullable<T>> {
  const end = Date.now() + ms;
  for (;;) {
    const value = await fn();
    if (value) return value as NonNullable<T>;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await new Promise((r) => setTimeout(r, 50));
  }
}

export function alive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}
