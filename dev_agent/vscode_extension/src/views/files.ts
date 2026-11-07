import * as vscode from "vscode";
import type { Store } from "../state";
import type { FileRow } from "../types";

const ICON: Record<string, string> = {
  written: "diff-modified",
  unchanged: "circle-outline",
  rolled_back: "discard",
  rollback_failed: "error",
  conflict: "warning",
  failed: "error",
  rejected: "circle-slash",
};

export class FilesView implements vscode.TreeDataProvider<FileRow> {
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;

  constructor(private readonly store: Store) {
    store.onChange(() => this.emitter.fire());
  }

  getTreeItem(file: FileRow): vscode.TreeItem {
    const item = new vscode.TreeItem(file.path, vscode.TreeItemCollapsibleState.None);
    item.description = file.state.replace(/_/g, " ");
    item.tooltip = file.detail ? `${file.path}\n${file.state}: ${file.detail}` : `${file.path}\n${file.state}`;
    item.iconPath = new vscode.ThemeIcon(ICON[file.state] ?? "file");
    item.command = { command: "devAgent.openDiff", title: "Show diff", arguments: [file.path] };
    return item;
  }

  getChildren(): FileRow[] {
    return this.store.files;
  }
}
