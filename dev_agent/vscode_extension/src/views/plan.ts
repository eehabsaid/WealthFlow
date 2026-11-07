import * as vscode from "vscode";
import type { Store } from "../state";

interface Node {
  label: string;
  description?: string;
  icon?: string;
  children?: Node[];
  tooltip?: string;
}

function group(label: string, items: string[] | undefined, icon: string): Node | undefined {
  if (!items || items.length === 0) return undefined;
  return { label: `${label} (${items.length})`, icon, children: items.map((text) => ({ label: text })) };
}

export function planNodes(store: Store): Node[] {
  const task = store.task;
  if (!task) return [];
  if (!task.plan) return [{ label: task.status === "planning" ? "Planning: the agent is reading the project..." : "No plan", icon: "loading~spin" }];
  const plan = task.plan;
  const nodes: (Node | undefined)[] = [
    { label: plan.summary, icon: "note", tooltip: plan.summary },
    { label: `Steps (${plan.steps.length})`, icon: "list-ordered", children: plan.steps.map((s) => ({ label: s.title, description: (s.files ?? []).join(", ") })) },
    group("Add", plan.files_add, "diff-added"),
    group("Edit", plan.files_edit, "diff-modified"),
    group("DELETE", plan.files_delete, "diff-removed"),
    group("RENAME", plan.files_rename.map((r) => `${r.from} -> ${r.to}`), "arrow-right"),
    group("Protected: will ask you first", plan.needs_owner_approval, "shield"),
    group("Tests", plan.tests, "beaker"),
    group("Risks", plan.risks, "warning"),
  ];
  return nodes.filter((n): n is Node => n !== undefined);
}

export class PlanView implements vscode.TreeDataProvider<Node> {
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;

  constructor(private readonly store: Store) {
    store.onChange(() => {
      void vscode.commands.executeCommand("setContext", "devAgent.awaitingApproval", store.task?.status === "awaiting_approval");
      void vscode.commands.executeCommand("setContext", "devAgent.canResume", store.task?.status === "stopped" && Boolean(store.task.approved_at));
      this.emitter.fire();
    });
  }

  getTreeItem(node: Node): vscode.TreeItem {
    const item = new vscode.TreeItem(node.label, node.children ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.None);
    item.description = node.description;
    item.tooltip = node.tooltip;
    if (node.icon) item.iconPath = new vscode.ThemeIcon(node.icon);
    return item;
  }

  getChildren(node?: Node): Node[] {
    return node ? (node.children ?? []) : planNodes(this.store);
  }
}
