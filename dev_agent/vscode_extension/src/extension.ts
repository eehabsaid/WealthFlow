import * as vscode from "vscode";
import { Approvals } from "./approvals";
import { registerCommands } from "./commands";
import * as diff from "./diff";
import { Log } from "./log";
import { ServerManager } from "./manager";
import { Store } from "./state";
import { StatusBar } from "./statusBar";
import { FilesView } from "./views/files";
import { PlanView } from "./views/plan";
import { ProgressView } from "./views/progress";
import { TasksView } from "./views/tasks";

let manager: ServerManager | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const log = new Log();
  const store = new Store(() => manager?.client);
  manager = new ServerManager(log, store);
  const approvals = new Approvals(store, manager);
  const status = new StatusBar(manager, store, approvals);
  const tree = (id: string, provider: vscode.TreeDataProvider<any>): vscode.Disposable => vscode.window.createTreeView(id, { treeDataProvider: provider, showCollapseAll: false });
  context.subscriptions.push(log, status, tree("devAgent.tasks", new TasksView(store)), tree("devAgent.plan", new PlanView(store)), tree("devAgent.progress", new ProgressView(store)), tree("devAgent.files", new FilesView(store)));
  diff.register(context, manager);
  registerCommands({ context, log, manager, store, approvals });
  context.subscriptions.push({ dispose: () => void manager?.stop() });
  void manager.start();
}

// Stop the hidden server (and any command it is running) when the window closes.
export async function deactivate(): Promise<void> {
  await manager?.stop();
}
