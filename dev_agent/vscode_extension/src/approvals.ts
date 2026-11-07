import * as vscode from "vscode";
import { ApiError } from "./client";
import type { ServerManager } from "./manager";
import type { Store } from "./state";
import type { Approval, TaskDetail } from "./types";

// Modal approval dialogs. The engine blocks until someone answers; the first answer wins, whichever interface it comes from.
export class Approvals {
  private asked = new Set<string>();
  private dismissed = new Set<string>();
  private busy = false;

  constructor(
    private readonly store: Store,
    private readonly manager: ServerManager,
  ) {
    store.onChange(() => void this.check());
    store.onPlanReady = (task) => void this.planReady(task);
  }

  get pending(): Approval[] {
    return this.store.state?.approvals ?? [];
  }

  get waiting(): number {
    return this.pending.filter((a) => this.dismissed.has(a.id)).length || (this.busy ? 1 : 0);
  }

  private async check(): Promise<void> {
    if (this.busy) return;
    const next = this.pending.find((a) => !this.asked.has(a.id));
    if (!next) return;
    this.busy = true;
    this.asked.add(next.id);
    try {
      await this.ask(next);
    } finally {
      this.busy = false;
      void this.check();
    }
  }

  async ask(approval: Approval): Promise<void> {
    const choice = await vscode.window.showWarningMessage(`dev_agent needs your approval (${approval.kind})`, { modal: true, detail: approval.message }, "Approve", "Deny");
    if (!choice) {
      this.dismissed.add(approval.id); // closed without answering: it stays pending, the status bar offers it again
      return;
    }
    this.dismissed.delete(approval.id);
    try {
      await this.manager.client?.answer(approval, choice === "Approve");
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 404)) void vscode.window.showErrorMessage(`Could not send your answer: ${(error as Error).message}`);
    }
    void this.store.refresh();
  }

  async reopen(): Promise<void> {
    const next = this.pending.find((a) => this.dismissed.has(a.id)) ?? this.pending[0];
    if (next) await this.ask(next);
    else void vscode.window.showInformationMessage("Nothing is waiting for your approval.");
  }

  private async planReady(task: TaskDetail): Promise<void> {
    const plan = task.plan;
    if (!plan) return;
    const lines = [plan.summary, "", `Steps: ${plan.steps.length}`];
    const add = (label: string, items: string[]): void => void (items.length && lines.push(`${label}: ${items.slice(0, 10).join(", ")}${items.length > 10 ? ", ..." : ""}`));
    add("Add", plan.files_add);
    add("Edit", plan.files_edit);
    add("DELETE", plan.files_delete);
    add("RENAME", plan.files_rename.map((r) => `${r.from} -> ${r.to}`));
    add("Protected (will ask you first)", plan.needs_owner_approval);
    add("Risks", plan.risks);
    const choice = await vscode.window.showInformationMessage("The plan is ready for your review", { modal: true, detail: lines.join("\n") }, "Approve and run", "Reject");
    const client = this.manager.client;
    if (!choice || !client) return; // decide later from the Plan view
    try {
      if (choice === "Reject") await client.rejectPlan(task.id);
      else await client.approvePlan(task.id);
    } catch (error) {
      void vscode.window.showErrorMessage((error as Error).message);
    }
    void this.store.refresh();
  }
}
