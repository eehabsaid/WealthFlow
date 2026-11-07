import type { AgentClient } from "./client";
import type { ServerState } from "./types";

// A light poll of /api/state for the status bar and the "approval needed" notice. The chat view does its own polling; no VS Code imports here.
export class Status {
  state: ServerState | undefined;
  connected = false;
  private listeners = new Set<() => void>();
  private timer: NodeJS.Timeout | undefined;

  constructor(private readonly getClient: () => AgentClient | undefined) {}

  onChange(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  start(intervalMs = 2000): void {
    this.stop();
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), intervalMs);
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }

  reset(): void {
    this.stop();
    this.state = undefined;
    this.connected = false;
    this.listeners.forEach((fn) => fn());
  }

  async refresh(): Promise<void> {
    const client = this.getClient();
    try {
      this.state = client ? await client.state() : undefined;
      this.connected = Boolean(client);
    } catch {
      this.connected = false;
    }
    this.listeners.forEach((fn) => fn());
  }
}
