import { ApiError, type AgentClient, type Subscription } from "./client";
import { readAttachment, type Chip, type Item, type Kind } from "./attach";

export const PROVIDERS = ["ollama", "anthropic", "openai", "gemini"];

// What the bridge needs from VS Code itself (dialogs, editors). Kept as an interface so the bridge is tested in plain Node.
export interface Host {
  client(): AgentClient | undefined;
  offlineReason(): string;
  pick(kind: Kind): Promise<string[]>;
  openDiff(taskId: string, rel: string): Promise<void>;
  openReport(text: string): Promise<void>;
  setApiKey(provider: string): Promise<void>;
  menu(): Promise<void>;
  restart(): Promise<void>;
  projectRoot(): string | undefined;
}

type Reply = { type: "res"; id: number; ok: true; data: unknown } | { type: "res"; id: number; ok: false; error: { status: number; code: string; message: string } };
export type Post = (message: Reply | { type: "event"; taskId: string; event: unknown }) => void;

const ID = "[\\w.-]+";
// The ONLY requests a webview may make. No key writes, no shutdown, no file contents, and task creation goes through `submit` (attachments stay here).
const ALLOWED: [string, RegExp][] = [
  ["GET", /^\/api\/state(\?[\w=&%.:+-]*)?$/],
  ["GET", /^\/api\/tasks$/],
  ["GET", new RegExp(`^/api/tasks/${ID}$`)],
  ["GET", new RegExp(`^/api/tasks/${ID}/files$`)],
  ["GET", /^\/api\/models\?provider=[a-z]+$/],
  ["GET", /^\/api\/keys$/],
  ["GET", /^\/api\/settings$/],
  ["POST", new RegExp(`^/api/tasks/${ID}/(approve|reject|resume)$`)],
  ["POST", /^\/api\/stop$/],
  ["POST", new RegExp(`^/api/approvals/${ID}$`)],
  ["PUT", /^\/api\/settings$/],
];

function allowed(method: unknown, path: unknown, body: unknown): boolean {
  if (typeof method !== "string" || typeof path !== "string") return false;
  if (!ALLOWED.some(([m, re]) => m === method && re.test(path))) return false;
  if (method === "PUT") {
    const values = (body as { values?: Record<string, unknown> } | undefined)?.values;
    return !!values && Object.keys(values).every((k) => k === "provider" || k === "model") && Object.values(values).every((v) => typeof v === "string");
  }
  return true;
}

function describe(error: unknown, offline: string): { status: number; code: string; message: string } {
  if (error instanceof ApiError) return { status: error.status, code: error.code, message: error.message };
  const e = error as NodeJS.ErrnoException;
  const down = ["ECONNREFUSED", "ECONNRESET", "EPIPE"].includes(e.code ?? "") || /not running|did not answer|closed the connection/.test(e.message);
  return { status: 0, code: down ? "offline" : "error", message: down ? offline || "The agent server is not running." : e.message };
}

// Everything the webview may ask of the extension host. The access token and API keys exist only on this side: the webview gets plain data back.
export class Bridge {
  private pending = new Map<string, Item>();
  private n = 0;
  private sub: Subscription | undefined;

  constructor(
    private readonly host: Host,
    private readonly post: Post,
  ) {}

  dispose(): void {
    this.sub?.close();
    this.sub = undefined;
  }

  async handle(message: { type?: string; id?: number; name?: string; args?: Record<string, any> }): Promise<void> {
    if (message?.type !== "call" || typeof message.id !== "number" || typeof message.name !== "string") return;
    try {
      this.post({ type: "res", id: message.id, ok: true, data: await this.dispatch(message.name, message.args ?? {}) });
    } catch (error) {
      this.post({ type: "res", id: message.id, ok: false, error: describe(error, this.host.offlineReason()) });
    }
  }

  private client(): AgentClient {
    const client = this.host.client();
    if (!client) throw new Error("the agent server is not running");
    return client;
  }

  private async dispatch(name: string, a: Record<string, any>): Promise<unknown> {
    switch (name) {
      case "request":
        if (!allowed(a.method, a.path, a.body)) throw new ApiError(403, "blocked", `the chat view may not call ${String(a.method)} ${String(a.path)}`);
        return this.client().request(a.method, a.path, a.body);
      case "subscribe": {
        if (typeof a.taskId !== "string" || !new RegExp(`^${ID}$`).test(a.taskId)) throw new Error("bad task id");
        this.sub?.close();
        const taskId: string = a.taskId;
        this.sub = this.client().subscribe(taskId, 0, (event) => this.post({ type: "event", taskId, event }));
        return true;
      }
      case "unsubscribe":
        this.sub?.close();
        this.sub = undefined;
        return true;
      case "attach":
        return this.attach(a.kind === "image" ? "image" : "file");
      case "detach":
        return this.pending.delete(String(a.id));
      case "submit": {
        if (typeof a.goal !== "string") throw new Error("the task text is missing");
        const override = typeof a.provider === "string" && typeof a.model === "string" && a.provider && a.model ? { provider: a.provider, model: a.model } : {};
        const id = await this.client().startTask(a.goal, [...this.pending.values()], override);
        this.pending.clear();
        return { id };
      }
      case "openDiff":
        if (typeof a.taskId !== "string" || typeof a.path !== "string") throw new Error("bad diff request");
        return this.host.openDiff(a.taskId, a.path);
      case "openReport":
        if (typeof a.taskId !== "string") throw new Error("bad report request");
        return this.host.openReport(await this.client().report(a.taskId));
      case "setApiKey":
        if (!PROVIDERS.includes(a.provider)) throw new Error("unknown provider");
        return this.host.setApiKey(a.provider);
      case "menu":
        return this.host.menu();
      case "restart":
        return this.host.restart();
      default:
        throw new Error(`unknown call ${name}`);
    }
  }

  private async attach(kind: Kind): Promise<{ chips: Chip[]; rejected: { name: string; reason: string }[] }> {
    const chips: Chip[] = [];
    const rejected: { name: string; reason: string }[] = [];
    for (const file of await this.host.pick(kind)) {
      const id = `h${++this.n}`;
      const read = readAttachment(file, kind, id, this.host.projectRoot());
      if (read.ok) {
        this.pending.set(id, read.item);
        chips.push(read.chip);
      } else rejected.push({ name: read.name, reason: read.reason });
    }
    return { chips, rejected };
  }
}
