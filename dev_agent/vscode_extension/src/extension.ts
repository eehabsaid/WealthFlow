import * as vscode from "vscode";
import { ChatView } from "./chatView";
import { registerCommands } from "./commands";
import * as diff from "./diff";
import { createHost } from "./host";
import { Log } from "./log";
import { ServerManager } from "./manager";
import { Status } from "./status";
import { StatusBar } from "./statusBar";

let manager: ServerManager | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const log = new Log();
  const poller = new Status(() => manager?.client);
  manager = new ServerManager(log, poller);
  const chat = new ChatView(context, createHost(manager));
  context.subscriptions.push(
    log,
    chat,
    new StatusBar(manager, poller),
    vscode.window.registerWebviewViewProvider(ChatView.viewType, chat, { webviewOptions: { retainContextWhenHidden: true } }),
  );
  // A request that blocks the engine must not go unnoticed when the chat is not on screen (first one wins, whichever interface answers).
  let notified = "";
  context.subscriptions.push({
    dispose: poller.onChange(() => {
      const first = poller.state?.approvals[0];
      if (!first || first.id === notified || chat.visible) return;
      notified = first.id;
      void vscode.window.showInformationMessage("dev_agent needs your approval.", "Open chat").then((choice) => choice && chat.focus());
    }),
  });
  diff.register(context, manager);
  registerCommands({ context, log, manager, chat });
  context.subscriptions.push({ dispose: () => void manager?.stop() });
  void manager.start();
}

// Stop the hidden server (and any command it is running) when the window closes.
export async function deactivate(): Promise<void> {
  await manager?.stop();
}
