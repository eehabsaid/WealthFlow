import * as vscode from "vscode";
import { ApiError, type AgentClient } from "./client";
import type { Store } from "./state";

const PROVIDERS = ["ollama", "anthropic", "openai", "gemini"];

type Add = (id: string, fn: (...args: any[]) => unknown) => void;

async function pickProvider(placeHolder: string): Promise<string | undefined> {
  return vscode.window.showQuickPick(PROVIDERS, { placeHolder });
}

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

export function registerSettingsCommands(add: Add, client: () => AgentClient, store: Store): void {
  add("chooseProvider", async () => {
    const provider = await pickProvider("Provider for the agent");
    if (!provider) return;
    await client().updateSettings({ provider });
    await store.refresh();
    const keys = await client().keys();
    if (keys.keys[provider] === false) void vscode.window.showInformationMessage(`No API key stored for ${provider}. Run "dev_agent: Set API key".`);
  });
  add("chooseModel", async () => {
    const state = await client().state();
    let name: string | undefined;
    try {
      const found = await client().models(state.provider);
      if (found.models.length > 0) name = await vscode.window.showQuickPick(found.models, { placeHolder: `Model for ${state.provider} (current: ${state.model || "none"})` });
      else name = await vscode.window.showInputBox({ prompt: `Model name for ${state.provider}`, value: state.model, ignoreFocusOut: true });
    } catch {
      name = await vscode.window.showInputBox({ prompt: `Model name for ${state.provider} (the list could not be loaded)`, value: state.model, ignoreFocusOut: true });
    }
    if (!name) return;
    await client().updateSettings({ model: name });
    await store.refresh();
  });
  add("setApiKey", async () => {
    const provider = await pickProvider("Store an API key for which provider?");
    if (!provider) return;
    const value = await vscode.window.showInputBox({ prompt: `API key for ${provider} (stored in the OS keyring or the encrypted file, never in settings or git)`, password: true, ignoreFocusOut: true });
    if (!value) return;
    await withUnlock(client(), () => client().setKey(provider, value));
    void vscode.window.showInformationMessage(`API key for ${provider} saved.`);
  });
  add("deleteApiKey", async () => {
    const provider = await pickProvider("Remove the stored API key for which provider?");
    if (!provider) return;
    await withUnlock(client(), () => client().deleteKey(provider));
    void vscode.window.showInformationMessage(`API key for ${provider} removed.`);
  });
}
