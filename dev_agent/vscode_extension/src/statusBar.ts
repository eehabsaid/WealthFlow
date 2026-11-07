import * as vscode from "vscode";
import type { Approvals } from "./approvals";
import type { ServerManager } from "./manager";
import type { Store } from "./state";

export class StatusBar {
  private readonly item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);

  constructor(
    private readonly manager: ServerManager,
    private readonly store: Store,
    private readonly approvals: Approvals,
  ) {
    manager.onStatus(() => this.update());
    store.onChange(() => this.update());
    this.update();
    this.item.show();
  }

  update(): void {
    const { status, error } = this.manager;
    const state = this.store.state;
    const set = (text: string, tip: string, command: string, bad = false): void => {
      this.item.text = text;
      this.item.tooltip = tip;
      this.item.command = command;
      this.item.backgroundColor = bad ? new vscode.ThemeColor("statusBarItem.warningBackground") : undefined;
    };
    if (status === "starting") return set("$(sync~spin) dev_agent: starting", "Starting the agent server", "devAgent.showLog");
    if (status === "error") return set("$(error) dev_agent: offline", `${error}\nClick to restart`, "devAgent.restartServer", true);
    if (status === "stopped") return set("$(circle-slash) dev_agent: stopped", "Click to start", "devAgent.restartServer");
    if (this.approvals.pending.length > 0) return set("$(bell) dev_agent: approval needed", this.approvals.pending[0].message.slice(0, 200), "devAgent.showApproval", true);
    const model = state ? `${state.provider}: ${state.model || "no model chosen"}` : "";
    if (state?.busy) return set(`$(sync~spin) dev_agent: ${state.current?.phase ?? "working"}`, `Working (${model}). Click to see progress.`, "devAgent.showProgress");
    set("$(robot) dev_agent", `Idle (${model})`, "devAgent.newTask");
  }

  dispose(): void {
    this.item.dispose();
  }
}
