import * as vscode from "vscode";
import type { Kind } from "./attach";
import type { Host } from "./bridge";
import { openDiff } from "./diff";
import type { ServerManager } from "./manager";
import { askApiKey } from "./settingsCommands";

// The real VS Code side of the bridge: file pickers, the native diff editor, a markdown report tab, native key input.
export function createHost(manager: ServerManager): Host {
  const root = (): string => manager.settings().projectRoot ?? "";
  return {
    client: () => manager.client,
    offlineReason: () => manager.error,
    projectRoot: () => manager.settings().projectRoot,
    async pick(kind: Kind) {
      const chosen = await vscode.window.showOpenDialog({
        canSelectMany: true,
        canSelectFolders: false,
        openLabel: kind === "image" ? "Attach image" : "Attach file",
        defaultUri: root() ? vscode.Uri.file(root()) : undefined,
        filters: kind === "image" ? { Images: ["png", "jpg", "jpeg", "gif", "webp"] } : undefined,
      });
      return (chosen ?? []).map((u) => u.fsPath);
    },
    openDiff: (taskId, rel) => openDiff(root(), taskId, rel),
    async openReport(text) {
      await vscode.window.showTextDocument(await vscode.workspace.openTextDocument({ language: "markdown", content: text }), { preview: true });
    },
    async setApiKey(provider) {
      if (!manager.client) throw new Error("the agent server is not running");
      await askApiKey(manager.client, provider);
    },
    async menu() {
      const items = ["Set API key…", "Remove API key…", "Restart server", "Show log"];
      const choice = await vscode.window.showQuickPick(items, { placeHolder: "dev_agent" });
      const command = { [items[0]]: "setApiKey", [items[1]]: "deleteApiKey", [items[2]]: "restartServer", [items[3]]: "showLog" }[choice ?? ""];
      if (command) await vscode.commands.executeCommand(`devAgent.${command}`);
    },
    restart: () => manager.restart(),
  };
}
