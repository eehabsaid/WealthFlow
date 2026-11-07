import * as vscode from "vscode";
import { ApiError, type AgentClient } from "./client";
import { PROVIDERS } from "./bridge";

type Add = (id: string, fn: (...args: any[]) => unknown) => void;

// Run a key operation; if the encrypted key file is locked (no OS keyring), ask for the passphrase once and retry. Nothing here is ever logged.
async function withUnlock(client: AgentClient, work: () => Promise<unknown>): Promise<void> {
  try {
    await work();
  } catch (error) {
    if (!(error instanceof ApiError && error.code === "passphrase_required")) throw error;
    const phrase = await vscode.window.showInputBox({ prompt: "Passphrase for the encrypted credential file (no OS keyring is available)", password: true, ignoreFocusOut: true });
    if (!phrase) return;
    await client.unlockKeys(phrase);
    await work();
  }
}

// Keys are typed into VS Code's own masked input box and go straight to the server's keyring; the chat webview never sees them.
export async function askApiKey(client: AgentClient, provider: string): Promise<void> {
  const value = await vscode.window.showInputBox({ prompt: `API key for ${provider} (stored in the OS keyring or the encrypted file, never in settings or git)`, password: true, ignoreFocusOut: true });
  if (!value) return;
  await withUnlock(client, () => client.setKey(provider, value));
  void vscode.window.showInformationMessage(`API key for ${provider} saved.`);
}

export function registerSettingsCommands(add: Add, client: () => AgentClient): void {
  const pick = (placeHolder: string) => vscode.window.showQuickPick(PROVIDERS, { placeHolder });
  add("setApiKey", async () => {
    const provider = await pick("Store an API key for which provider?");
    if (provider) await askApiKey(client(), provider);
  });
  add("deleteApiKey", async () => {
    const provider = await pick("Remove the stored API key for which provider?");
    if (!provider) return;
    await withUnlock(client(), () => client().deleteKey(provider));
    void vscode.window.showInformationMessage(`API key for ${provider} removed.`);
  });
}
