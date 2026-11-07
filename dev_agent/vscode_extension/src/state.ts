import type { AgentClient, Subscription } from "./client";
import type { AgentEvent, FileRow, ServerState, TaskDetail, TaskRow } from "./types";

const MAX_EVENTS = 2000;
const REFRESH_ON = new Set(["status", "done", "package", "verify", "phase"]);

// Everything the views show. No VS Code imports, so it is tested in plain Node against the real server.
export class Store {
  state: ServerState | undefined;
  tasks: TaskRow[] = [];
  selectedId: string | undefined;
  task: TaskDetail | undefined;
  files: FileRow[] = [];
  events: AgentEvent[] = [];
  connected = false;
  lastError = "";
  onPlanReady: (task: TaskDetail) => void = () => undefined;

  private listeners = new Set<() => void>();
  private sub: Subscription | undefined;
  private timer: NodeJS.Timeout | undefined;
  private debounce: NodeJS.Timeout | undefined;
  private lastStatus = new Map<string, string>();

  constructor(private readonly getClient: () => AgentClient | undefined) {}

  onChange(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private changed(): void {
    this.listeners.forEach((fn) => fn());
  }

  start(intervalMs = 2000): void {
    this.stop();
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), intervalMs);
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
    this.sub?.close();
    this.sub = undefined;
  }

  reset(): void {
    this.stop();
    this.state = undefined;
    this.tasks = [];
    this.files = [];
    this.events = [];
    this.task = undefined;
    this.selectedId = undefined;
    this.connected = false;
    this.changed();
  }

  async refresh(): Promise<void> {
    const client = this.getClient();
    if (!client) {
      this.connected = false;
      return this.changed();
    }
    try {
      const [state, tasks] = await Promise.all([client.state(), client.tasks()]);
      this.state = state;
      this.tasks = tasks;
      this.connected = true;
      this.lastError = "";
      if (this.selectedId) await this.refreshTask();
    } catch (error) {
      this.connected = false;
      this.lastError = (error as Error).message;
    }
    this.changed();
  }

  async refreshTask(): Promise<void> {
    const client = this.getClient();
    const id = this.selectedId;
    if (!client || !id) return;
    const [task, files] = await Promise.all([client.task(id), client.files(id)]);
    if (id !== this.selectedId) return;
    const before = this.lastStatus.get(id);
    this.lastStatus.set(id, task.status);
    this.task = task;
    this.files = files;
    if (task.status === "awaiting_approval" && before !== undefined && before !== "awaiting_approval") this.onPlanReady(task);
    this.changed();
  }

  select(id: string | undefined): void {
    this.sub?.close();
    this.sub = undefined;
    this.selectedId = id;
    this.task = undefined;
    this.files = [];
    this.events = [];
    this.changed();
    const client = this.getClient();
    if (!id || !client) return;
    this.sub = client.subscribe(id, 0, (event) => this.onEvent(id, event));
    void this.refreshTask().then(() => this.changed());
  }

  // Remember the current status before a task starts, so the transition to "awaiting_approval" is recognised as news.
  expect(id: string): void {
    this.lastStatus.set(id, "planning");
  }

  private onEvent(id: string, event: AgentEvent): void {
    if (id !== this.selectedId) return;
    this.events.push(event);
    if (this.events.length > MAX_EVENTS) this.events.splice(0, this.events.length - MAX_EVENTS);
    this.changed();
    if (REFRESH_ON.has(event.type)) {
      clearTimeout(this.debounce);
      this.debounce = setTimeout(() => void this.refresh(), 250);
    }
  }
}
