// A minimal stand-in for the `vscode` module so the extension's own code (activate, commands, tree views, dialogs, diff, status bar) runs in plain Node.
// It records what the extension asks VS Code to do. It is NOT VS Code: real-editor behaviour is not covered by these tests.
import Module from "node:module";

type Fn = (...a: any[]) => any;
export const calls = { commands: new Map<string, Fn>(), trees: new Map<string, any>(), executed: [] as any[][], warnings: [] as any[][], infos: [] as any[][], errors: [] as string[], contexts: new Map<string, unknown>(), providers: new Map<string, any>() };
export const answers: { warning: (string | undefined)[]; info: (string | undefined)[]; input: (string | undefined)[]; pick: (string | undefined)[] } = { warning: [], info: [], input: [], pick: [] };
export const config: Record<string, string> = {};
export const state = { folder: "", statusItem: { text: "", command: "" as string | undefined, tooltip: "" as unknown } };

class Emitter {
  private fns: Fn[] = [];
  event = (fn: Fn): { dispose(): void } => (this.fns.push(fn), { dispose: () => undefined });
  fire(v?: unknown): void {
    this.fns.forEach((f) => f(v));
  }
}
class TreeItem {
  description?: string;
  tooltip?: unknown;
  iconPath?: unknown;
  command?: unknown;
  contextValue?: string;
  constructor(public label: string, public collapsibleState = 0) {}
}
const vscode = {
  EventEmitter: Emitter,
  TreeItem,
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  ThemeIcon: class { constructor(public id: string) {} },
  ThemeColor: class { constructor(public id: string) {} },
  MarkdownString: class { value = ""; appendText(t: string) { this.value += t; return this; } },
  StatusBarAlignment: { Left: 1 },
  Uri: { file: (p: string) => ({ scheme: "file", path: p, fsPath: p }), from: (o: { scheme: string; path: string }) => ({ ...o, fsPath: o.path }) },
  window: {
    createOutputChannel: () => ({ appendLine: (l: string) => void (process.env.DEV_AGENT_TRACE && process.stderr.write(`[log ${Date.now() % 100000}] ${l}\n`)), show: () => undefined, dispose: () => undefined }),
    createStatusBarItem: () => ({ ...state.statusItem, show() {}, dispose() {}, set text(v: string) { state.statusItem.text = v; }, get text() { return state.statusItem.text; }, set command(v: string | undefined) { state.statusItem.command = v; }, set tooltip(v: unknown) { state.statusItem.tooltip = v; }, set backgroundColor(_v: unknown) {} }),
    createTreeView: (id: string, o: { treeDataProvider: unknown }) => (calls.trees.set(id, o.treeDataProvider), { dispose: () => undefined }),
    showWarningMessage: async (...a: any[]) => (calls.warnings.push(a), answers.warning.shift()),
    showInformationMessage: async (...a: any[]) => (calls.infos.push(a), answers.info.shift()),
    showErrorMessage: async (m: string) => void calls.errors.push(m),
    showInputBox: async () => answers.input.shift(),
    showQuickPick: async () => answers.pick.shift(),
    showTextDocument: async () => undefined,
  },
  workspace: {
    get workspaceFolders() { return [{ uri: { fsPath: state.folder } }]; },
    getConfiguration: () => ({ get: (k: string) => config[k] }),
    registerTextDocumentContentProvider: (scheme: string, p: unknown) => (calls.providers.set(scheme, p), { dispose: () => undefined }),
    openTextDocument: async (o: unknown) => o,
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
