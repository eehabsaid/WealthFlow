import * as vscode from "vscode";
import type { ChatView } from "./chatView";
import type { Log } from "./log";
import type { ServerManager } from "./manager";
import { registerSettingsCommands } from "./settingsCommands";

export interface Deps {
  context: vscode.ExtensionContext;
  log: Log;
  manager: ServerManager;
  chat: ChatView;
}

export function registerCommands(d: Deps): void {
  const { manager, log } = d;
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
  add("focus", () => d.chat.focus());
  add("stop", async () => {
    const stopped = await client().stop();
    void vscode.window.showInformationMessage(stopped ? "Stopping: running commands are being terminated." : "Nothing is running.");
  });
  add("restartServer", () => manager.restart());
  add("showLog", () => log.show());
  registerSettingsCommands(add, client);
}
