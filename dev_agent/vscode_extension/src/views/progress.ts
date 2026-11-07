import * as vscode from "vscode";
import type { Store } from "../state";
import type { AgentEvent } from "../types";

export interface Row {
  label: string;
  description?: string;
  icon: string;
  children?: Row[];
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");

function describe(e: AgentEvent): Row | undefined {
  switch (e.type) {
    case "phase":
      return { label: `Phase: ${str(e.phase)}`, icon: "milestone" };
    case "tool":
      return { label: str(e.name), description: str(e.summary), icon: e.ok ? "check" : "error" };
    case "command":
      return { label: str(e.command), description: `${str(e.status)}${typeof e.duration_s === "number" ? ` (${e.duration_s}s)` : ""}`, icon: e.status === "PASSED" ? "terminal" : "error" };
    case "verify":
      return { label: `Checks (${str(e.label)})`, description: str(e.overall), icon: e.overall === "VERIFIED" ? "verified" : "warning" };
    case "status":
      return { label: `Status: ${str(e.status)}`, description: str(e.reason), icon: "info" };
    case "approval_request":
      return { label: `Approval needed (${str(e.kind)})`, description: str(e.message).slice(0, 120), icon: "bell" };
    case "approval_result":
      return { label: e.approved ? "Approved" : "Denied", icon: e.approved ? "thumbsup" : "thumbsdown" };
    case "invalid_reply":
      return { label: "The model's reply was not valid protocol JSON", icon: "warning" };
    case "error":
      return { label: `Error: ${str(e.message)}`, icon: "error" };
    case "done":
      return { label: `Finished: ${str(e.status)}`, icon: "flag" };
    default:
      return undefined;
  }
}

// Work packages are parents; the tool calls, commands and checks that happened during them are their children.
export function progressRows(events: AgentEvent[]): Row[] {
  const rows: Row[] = [];
  let current: Row | undefined;
  for (const e of events) {
    if (e.type === "package") {
      if (e.status === "running" || !current) {
        current = { label: `${str(e.id)}: ${str(e.title)}`, description: str(e.status), icon: "package", children: [] };
        rows.push(current);
      } else {
        current.description = str(e.status);
      }
      continue;
    }
    const row = describe(e);
    if (!row) continue;
    if (current && e.type !== "status" && e.type !== "done" && e.type !== "phase") current.children?.push(row);
    else rows.push(row);
  }
  return rows;
}

export class ProgressView implements vscode.TreeDataProvider<Row> {
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;

  constructor(private readonly store: Store) {
    store.onChange(() => this.emitter.fire());
  }

  getTreeItem(row: Row): vscode.TreeItem {
    const item = new vscode.TreeItem(row.label, row.children?.length ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.None);
    item.description = row.description;
    item.tooltip = [row.label, row.description].filter(Boolean).join("\n");
    item.iconPath = new vscode.ThemeIcon(row.icon);
    return item;
  }

  getChildren(row?: Row): Row[] {
    return row ? (row.children ?? []) : progressRows(this.store.events);
  }
}
