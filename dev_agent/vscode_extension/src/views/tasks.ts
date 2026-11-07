import * as vscode from "vscode";
import type { Store } from "../state";
import type { TaskRow } from "../types";

export const STATUS_ICON: Record<string, string> = {
  completed: "pass",
  answered: "comment",
  awaiting_approval: "question",
  executing: "sync~spin",
  planning: "sync~spin",
  approved: "play",
  stopped: "debug-stop",
  rejected: "circle-slash",
  failed: "error",
};

export class TasksView implements vscode.TreeDataProvider<TaskRow> {
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;

  constructor(private readonly store: Store) {
    store.onChange(() => this.emitter.fire());
  }

  getTreeItem(task: TaskRow): vscode.TreeItem {
    const item = new vscode.TreeItem(task.goal.split("\n")[0].slice(0, 80), vscode.TreeItemCollapsibleState.None);
    item.description = task.status.replace(/_/g, " ");
    item.tooltip = new vscode.MarkdownString().appendText(`${task.goal}\n\n${task.status}${task.stop_reason ? ` - ${task.stop_reason}` : ""}`);
    item.iconPath = new vscode.ThemeIcon(STATUS_ICON[task.status] ?? "circle-outline");
    item.contextValue = task.id === this.store.selectedId ? "task.selected" : "task";
    item.command = { command: "devAgent.selectTask", title: "Open task", arguments: [task.id] };
    return item;
  }

  getChildren(): TaskRow[] {
    return this.store.tasks;
  }
}
