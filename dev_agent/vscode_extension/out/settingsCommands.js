"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerSettingsCommands = registerSettingsCommands;
const vscode = __importStar(require("vscode"));
const client_1 = require("./client");
const PROVIDERS = ["ollama", "anthropic", "openai", "gemini"];
async function pickProvider(placeHolder) {
    return vscode.window.showQuickPick(PROVIDERS, { placeHolder });
}
// Run a key operation; if the encrypted key file is locked (no OS keyring), ask for the passphrase once and retry. Nothing here is ever logged.
async function withUnlock(client, work) {
    try {
        await work();
    }
    catch (error) {
        if (!(error instanceof client_1.ApiError && error.code === "passphrase_required"))
            throw error;
        const phrase = await vscode.window.showInputBox({ prompt: "Passphrase for the encrypted credential file (no OS keyring is available)", password: true, ignoreFocusOut: true });
        if (!phrase)
            return;
        await client.unlockKeys(phrase);
        await work();
    }
}
function registerSettingsCommands(add, client, store) {
    add("chooseProvider", async () => {
        const provider = await pickProvider("Provider for the agent");
        if (!provider)
            return;
        await client().updateSettings({ provider });
        await store.refresh();
        const keys = await client().keys();
        if (keys.keys[provider] === false)
            void vscode.window.showInformationMessage(`No API key stored for ${provider}. Run "dev_agent: Set API key".`);
    });
    add("chooseModel", async () => {
        const state = await client().state();
        let name;
        try {
            const found = await client().models(state.provider);
            if (found.models.length > 0)
                name = await vscode.window.showQuickPick(found.models, { placeHolder: `Model for ${state.provider} (current: ${state.model || "none"})` });
            else
                name = await vscode.window.showInputBox({ prompt: `Model name for ${state.provider}`, value: state.model, ignoreFocusOut: true });
        }
        catch {
            name = await vscode.window.showInputBox({ prompt: `Model name for ${state.provider} (the list could not be loaded)`, value: state.model, ignoreFocusOut: true });
        }
        if (!name)
            return;
        await client().updateSettings({ model: name });
        await store.refresh();
    });
    add("setApiKey", async () => {
        const provider = await pickProvider("Store an API key for which provider?");
        if (!provider)
            return;
        const value = await vscode.window.showInputBox({ prompt: `API key for ${provider} (stored in the OS keyring or the encrypted file, never in settings or git)`, password: true, ignoreFocusOut: true });
        if (!value)
            return;
        await withUnlock(client(), () => client().setKey(provider, value));
        void vscode.window.showInformationMessage(`API key for ${provider} saved.`);
    });
    add("deleteApiKey", async () => {
        const provider = await pickProvider("Remove the stored API key for which provider?");
        if (!provider)
            return;
        await withUnlock(client(), () => client().deleteKey(provider));
        void vscode.window.showInformationMessage(`API key for ${provider} removed.`);
    });
}
