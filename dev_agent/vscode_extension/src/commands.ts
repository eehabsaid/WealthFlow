import * as vscode from "vscode";
import type { Approvals } from "./approvals";
import { openDiff } from "./diff";
import type { Log } from "./log";
import type { ServerManager } from "./manager";
import { registerSettingsCommands } from "./settingsCommands";
import type { Store } from "./state";

export interface Deps {
  context: vscode.ExtensionContext;
  log: Log;
  manager: ServerManager;
  store: Store;
  approvals: Approvals;
}

export function registerCommands(d: Deps): void {
  const { manager, store, log } = d;
  const add = (id: string, fn: (...args: any[]) => unknown): void => {
    d.context.subscriptions.push(
      vscode.commands.registerCommand(`devAgent.${id}`, async (...args: unknown[]) => {
        try {
          await fn(...args);
        } catch (error) {
          log.line(`command ${id} failed: ${(error as Error).message}`);
          void vscode.window.showErrorMessage(`dev_agent: ${(error as Error).message}`);
        }
      }),
    );
  };
  const client = () => {
    const c = manager.client;
    if (!c) throw new Error(manager.error || "the agent server is not running (try dev_agent: Restart server)");
    return c;
  };
  const taskId = (): string => {
    if (!store.selectedId) throw new Error("select a task first");
    return store.selectedId;
  };
  const submit = async (goal: string): Promise<void> => {
    const id = await client().startTask(goal.trim());
    store.expect(id);
    store.select(id);
    void vscode.commands.executeCommand("devAgent.progress.focus");
    log.line(`task ${id} started`);
  };

  add("newTask", async () => {
    const goal = await vscode.window.showInputBox({ prompt: "What should the agent do?", placeHolder: "e.g. add input validation to app/forms.py", ignoreFocusOut: true });
    if (goal?.trim()) await submit(goal);
  });
  add("newTaskFromEditor", async () => {
    const editor = vscode.window.activeTextEditor;
    const text = editor ? (editor.selection.isEmpty ? editor.document.getText() : editor.document.getText(editor.selection)) : "";
    if (!text.trim()) throw new Error("open an editor with the task text (or select it) first");
    await submit(text);
  });
  add("selectTask", (id: string) => store.select(id));
  add("approvePlan", async () => client().approvePlan(taskId()));
  add("rejectPlan", async () => client().rejectPlan(taskId()));
  add("resume", async () => client().resume(taskId()));
  add("stop", async () => {
    const stopped = await client().stop();
    void vscode.window.showInformationMessage(stopped ? "Stopping: running commands are being terminated." : "Nothing is running.");
    await store.refresh();
  });
  add("openDiff", async (rel: string) => openDiff(store, manager.settings().projectRoot ?? "", rel));
  add("showReport", async () => {
    const text = await client().report(taskId());
    await vscode.window.showTextDocument(await vscode.workspace.openTextDocument({ language: "markdown", content: text }), { preview: true });
  });
  add("showApproval", () => d.approvals.reopen());
  add("showProgress", () => vscode.commands.executeCommand("devAgent.progress.focus"));
  add("refresh", () => store.refresh());
  add("restartServer", () => manager.restart());
  add("showLog", () => log.show());
  registerSettingsCommands(add, client, store);
}
