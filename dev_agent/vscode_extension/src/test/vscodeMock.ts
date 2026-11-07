// A minimal stand-in for the `vscode` module so the extension's own code (activate, commands, chat view, diff, status bar) runs in plain Node.
// It records what the extension asks VS Code to do. It is NOT VS Code: real-editor behaviour (webview runtime, CSP enforcement) is not covered here.
import Module from "node:module";

type Fn = (...a: any[]) => any;
export const calls = { commands: new Map<string, Fn>(), executed: [] as any[][], infos: [] as any[][], errors: [] as string[], contexts: new Map<string, unknown>(), providers: new Map<string, any>(), views: new Map<string, any>(), docs: [] as any[] };
export const answers: { info: (string | undefined)[]; input: (string | undefined)[]; pick: (string | undefined)[]; open: string[][] } = { info: [], input: [], pick: [], open: [] };
export const config: Record<string, string> = {};
export const state = { folder: "", statusItem: { text: "", command: "" as string | undefined, tooltip: "" as unknown } };

class Emitter {
  private fns: Fn[] = [];
  event = (fn: Fn): { dispose(): void } => (this.fns.push(fn), { dispose: () => undefined });
  fire(v?: unknown): void {
    this.fns.forEach((f) => f(v));
  }
}
const uri = (p: string) => ({ scheme: "file", path: p, fsPath: p, toString: () => `vscode-resource:${p}` });
const vscode = {
  EventEmitter: Emitter,
  ThemeColor: class { constructor(public id: string) {} },
  StatusBarAlignment: { Left: 1 },
  Uri: { file: uri, joinPath: (b: { path: string }, ...p: string[]) => uri([b.path, ...p].join("/")), from: (o: { scheme: string; path: string }) => ({ ...o, fsPath: o.path }) },
  window: {
    createOutputChannel: () => ({ appendLine: (l: string) => void (process.env.DEV_AGENT_TRACE && process.stderr.write(`[log] ${l}\n`)), show: () => undefined, dispose: () => undefined }),
    createStatusBarItem: () => ({ show() {}, dispose() {}, set text(v: string) { state.statusItem.text = v; }, get text() { return state.statusItem.text; }, set command(v: string | undefined) { state.statusItem.command = v; }, set tooltip(v: unknown) { state.statusItem.tooltip = v; }, set backgroundColor(_v: unknown) {} }),
    registerWebviewViewProvider: (id: string, p: unknown) => (calls.views.set(id, p), { dispose: () => undefined }),
    showInformationMessage: async (...a: any[]) => (calls.infos.push(a), answers.info.shift()),
    showErrorMessage: async (m: string) => void calls.errors.push(m),
    showInputBox: async () => answers.input.shift(),
    showQuickPick: async () => answers.pick.shift(),
    showOpenDialog: async () => (answers.open.shift() ?? []).map(uri),
    showTextDocument: async () => undefined,
  },
  workspace: {
    get workspaceFolders() { return [{ uri: { fsPath: state.folder } }]; },
    getConfiguration: () => ({ get: (k: string) => config[k] }),
    registerTextDocumentContentProvider: (scheme: string, p: unknown) => (calls.providers.set(scheme, p), { dispose: () => undefined }),
    openTextDocument: async (o: unknown) => (calls.docs.push(o), o),
  },
  commands: {
    registerCommand: (id: string, fn: Fn) => (calls.commands.set(id, fn), { dispose: () => undefined }),
    executeCommand: async (id: string, ...a: any[]) => {
      if (id === "setContext") calls.contexts.set(a[0], a[1]);
      else calls.executed.push([id, ...a]);
    },
  },
};

const original = (Module as any)._load;
(Module as any)._load = function (request: string, ...rest: unknown[]) {
  return request === "vscode" ? vscode : original.call(this, request, ...rest);
};
