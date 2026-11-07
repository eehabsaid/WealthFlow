import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { ApiError } from "./client";
import type { ServerManager } from "./manager";
import type { Store } from "./state";
import type { Version } from "./types";

const SCHEME = "devagent";

// Serves the recorded ORIGINAL content of a file (from the task ledger) as a read-only virtual document, so VS Code's native diff editor can compare it
// with the file on disk. A file that did not exist before (or no longer exists) shows as empty on that side.
export class DiffProvider implements vscode.TextDocumentContentProvider {
  constructor(private readonly manager: ServerManager) {}

  static uri(version: Version, taskId: string, rel: string): vscode.Uri {
    return vscode.Uri.from({ scheme: SCHEME, path: `/${version}/${taskId}/${rel}` });
  }

  async provideTextDocumentContent(uri: vscode.Uri): Promise<string> {
    const [, version, taskId, ...rest] = uri.path.split("/");
    try {
      return (await this.manager.client?.fileText(taskId, rest.join("/"), version as Version)) ?? "";
    } catch (error) {
      if (error instanceof ApiError && (error.status === 404 || error.status === 415)) return error.status === 415 ? "(binary file)" : "";
      throw error;
    }
  }
}

export function register(context: vscode.ExtensionContext, manager: ServerManager): void {
  context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider(SCHEME, new DiffProvider(manager)));
}

export async function openDiff(store: Store, root: string, rel: string): Promise<void> {
  const id = store.selectedId;
  if (!id) return;
  const onDisk = path.join(root, rel);
  const right = fs.existsSync(onDisk) ? vscode.Uri.file(onDisk) : DiffProvider.uri("current", id, rel);
  await vscode.commands.executeCommand("vscode.diff", DiffProvider.uri("original", id, rel), right, `${rel} (changed by dev_agent)`);
}
