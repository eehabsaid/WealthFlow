import * as http from "node:http";
import type { AgentEvent, Approval, FileRow, KeyStatus, ServerState, TaskDetail, TaskRow, Version } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export interface Subscription {
  close(): void;
}

// Plain Node http client for the local server: loopback only, bearer token, no dependencies.
export class AgentClient {
  constructor(
    readonly port: number,
    private readonly token: string,
  ) {}

  private options(method: string, path: string, extra: http.OutgoingHttpHeaders = {}): http.RequestOptions {
    const headers = { Authorization: `Bearer ${this.token}`, ...extra };
    return { host: "127.0.0.1", port: this.port, method, path, headers, agent: false }; // no connection pooling: a server that went away must not leave a request hanging
  }

  request<T = unknown>(method: string, path: string, body?: unknown, timeoutMs = 30000): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const payload = body === undefined ? undefined : Buffer.from(JSON.stringify(body), "utf8");
      const headers = payload ? { "Content-Type": "application/json", "Content-Length": payload.length } : {};
      let finished = false;
      const finish = (fn: () => void): void => {
        if (finished) return;
        finished = true;
        clearTimeout(deadline);
        fn();
      };
      const req = http.request(this.options(method, path, headers), (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (c: Buffer) => chunks.push(c));
        res.on("error", (e) => finish(() => reject(e)));
        res.on("aborted", () => finish(() => reject(new Error("the agent server closed the connection"))));
        res.on("end", () =>
          finish(() => {
            const text = Buffer.concat(chunks).toString("utf8");
            const isJson = String(res.headers["content-type"] ?? "").includes("json");
            const data: unknown = isJson && text ? JSON.parse(text) : text;
            const status = res.statusCode ?? 0;
            if (status >= 400) {
              const info = (isJson ? data : {}) as { error?: string; code?: string };
              reject(new ApiError(status, info.code ?? "error", info.error ?? `HTTP ${status}`));
            } else {
              resolve(data as T);
            }
          }),
        );
      });
      // A hard deadline for the whole request (a socket idle-timeout alone is not enough if the server disappears mid-request).
      const deadline = setTimeout(() => {
        req.destroy();
        finish(() => reject(new Error("the agent server did not answer in time")));
      }, timeoutMs);
      req.on("error", (e) => finish(() => reject(e)));
      req.end(payload);
    });
  }

  health = () => this.request<{ ok: boolean; version: string; pid: number }>("GET", "/api/health");
  state = () => this.request<ServerState>("GET", "/api/state");
  tasks = async () => (await this.request<{ tasks: TaskRow[] }>("GET", "/api/tasks")).tasks;
  task = (id: string) => this.request<TaskDetail>("GET", `/api/tasks/${id}`);
  files = async (id: string) => (await this.request<{ files: FileRow[] }>("GET", `/api/tasks/${id}/files`)).files;
  fileText = (id: string, path: string, version: Version) =>
    this.request<string>("GET", `/api/tasks/${id}/file?path=${encodeURIComponent(path)}&version=${version}`);
  report = (id: string) => this.request<string>("GET", `/api/tasks/${id}/report`);
  startTask = async (goal: string, attachments: unknown[] = [], override: { provider?: string; model?: string } = {}) =>
    (await this.request<{ id: string }>("POST", "/api/tasks", { goal, attachments, ...override }, 120000)).id;
  approvePlan = (id: string) => this.request("POST", `/api/tasks/${id}/approve`, {});
  rejectPlan = (id: string) => this.request("POST", `/api/tasks/${id}/reject`, {});
  resume = (id: string) => this.request("POST", `/api/tasks/${id}/resume`, {});
  stop = async () => (await this.request<{ stopped: boolean }>("POST", "/api/stop", {})).stopped;
  answer = (approval: Approval | string, approve: boolean) =>
    this.request("POST", `/api/approvals/${typeof approval === "string" ? approval : approval.id}`, { approve });
  settings = () => this.request<Record<string, unknown>>("GET", "/api/settings");
  updateSettings = (values: Record<string, string>) => this.request("PUT", "/api/settings", { values });
  keys = () => this.request<{ keys: KeyStatus; backend: string }>("GET", "/api/keys");
  setKey = (provider: string, value: string) => this.request("PUT", `/api/keys/${provider}`, { value });
  deleteKey = (provider: string) => this.request("DELETE", `/api/keys/${provider}`, {});
  unlockKeys = (passphrase: string) => this.request("POST", "/api/keys/unlock", { passphrase });
  models = (provider: string) =>
    this.request<{ models: string[]; note?: string }>("GET", `/api/models?provider=${encodeURIComponent(provider)}`);
  shutdown = () => this.request("POST", "/api/shutdown", {}, 5000);

  // Server-sent events with automatic reconnect that resumes after the last seen sequence number.
  subscribe(taskId: string, after: number, onEvent: (e: AgentEvent) => void, onDown?: (error: Error) => void): Subscription {
    let last = after;
    let closed = false;
    let current: http.ClientRequest | undefined;
    let retry: NodeJS.Timeout | undefined;
    const connect = (): void => {
      if (closed) return;
      const req = http.request(this.options("GET", `/api/tasks/${taskId}/events?stream=1`, { "Last-Event-ID": String(last) }), (res) => {
        if ((res.statusCode ?? 0) !== 200) {
          res.resume();
          return again(new ApiError(res.statusCode ?? 0, "stream", "event stream refused"));
        }
        let buffer = "";
        res.setEncoding("utf8");
        res.on("data", (piece: string) => {
          buffer += piece;
          for (let cut = buffer.indexOf("\n\n"); cut >= 0; cut = buffer.indexOf("\n\n")) {
            const line = buffer.slice(0, cut).split("\n").find((l) => l.startsWith("data: "));
            buffer = buffer.slice(cut + 2);
            if (line) {
              const event = JSON.parse(line.slice(6)) as AgentEvent;
              last = Math.max(last, event.seq);
              onEvent(event);
            }
          }
        });
        res.on("end", () => again(new Error("event stream ended")));
        res.on("error", again);
      });
      req.on("error", again);
      req.end();
      current = req;
    };
    const again = (error: Error): void => {
      if (closed) return;
      onDown?.(error);
      if (error instanceof ApiError && error.status === 401) return;
      retry = setTimeout(connect, 1500);
    };
    connect();
    return {
      close: () => {
        closed = true;
        if (retry) clearTimeout(retry);
        current?.destroy();
      },
    };
  }
}
