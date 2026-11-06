"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.state = exports.config = exports.answers = exports.calls = void 0;
// A minimal stand-in for the `vscode` module so the extension's own code (activate, commands, tree views, dialogs, diff, status bar) runs in plain Node.
// It records what the extension asks VS Code to do. It is NOT VS Code: real-editor behaviour is not covered by these tests.
const node_module_1 = __importDefault(require("node:module"));
exports.calls = { commands: new Map(), trees: new Map(), executed: [], warnings: [], infos: [], errors: [], contexts: new Map(), providers: new Map() };
exports.answers = { warning: [], info: [], input: [], pick: [] };
exports.config = {};
exports.state = { folder: "", statusItem: { text: "", command: "", tooltip: "" } };
class Emitter {
    fns = [];
    event = (fn) => (this.fns.push(fn), { dispose: () => undefined });
    fire(v) {
        this.fns.forEach((f) => f(v));
    }
}
class TreeItem {
    label;
    collapsibleState;
    description;
    tooltip;
    iconPath;
    command;
    contextValue;
    constructor(label, collapsibleState = 0) {
        this.label = label;
        this.collapsibleState = collapsibleState;
    }
}
const vscode = {
    EventEmitter: Emitter,
    TreeItem,
    TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
    ThemeIcon: class {
        id;
        constructor(id) {
            this.id = id;
        }
    },
    ThemeColor: class {
        id;
        constructor(id) {
            this.id = id;
        }
    },
    MarkdownString: class {
        value = "";
        appendText(t) { this.value += t; return this; }
    },
    StatusBarAlignment: { Left: 1 },
    Uri: { file: (p) => ({ scheme: "file", path: p, fsPath: p }), from: (o) => ({ ...o, fsPath: o.path }) },
    window: {
        createOutputChannel: () => ({ appendLine: (l) => void (process.env.DEV_AGENT_TRACE && process.stderr.write(`[log ${Date.now() % 100000}] ${l}\n`)), show: () => undefined, dispose: () => undefined }),
        createStatusBarItem: () => ({ ...exports.state.statusItem, show() { }, dispose() { }, set text(v) { exports.state.statusItem.text = v; }, get text() { return exports.state.statusItem.text; }, set command(v) { exports.state.statusItem.command = v; }, set tooltip(v) { exports.state.statusItem.tooltip = v; }, set backgroundColor(_v) { } }),
        createTreeView: (id, o) => (exports.calls.trees.set(id, o.treeDataProvider), { dispose: () => undefined }),
        showWarningMessage: async (...a) => (exports.calls.warnings.push(a), exports.answers.warning.shift()),
        showInformationMessage: async (...a) => (exports.calls.infos.push(a), exports.answers.info.shift()),
        showErrorMessage: async (m) => void exports.calls.errors.push(m),
        showInputBox: async () => exports.answers.input.shift(),
        showQuickPick: async () => exports.answers.pick.shift(),
        showTextDocument: async () => undefined,
    },
    workspace: {
        get workspaceFolders() { return [{ uri: { fsPath: exports.state.folder } }]; },
        getConfiguration: () => ({ get: (k) => exports.config[k] }),
        registerTextDocumentContentProvider: (scheme, p) => (exports.calls.providers.set(scheme, p), { dispose: () => undefined }),
        openTextDocument: async (o) => o,
    },
    commands: {
        registerCommand: (id, fn) => (exports.calls.commands.set(id, fn), { dispose: () => undefined }),
        executeCommand: async (id, ...a) => {
            if (id === "setContext")
                exports.calls.contexts.set(a[0], a[1]);
            else
                exports.calls.executed.push([id, ...a]);
        },
    },
};
const original = node_module_1.default._load;
node_module_1.default._load = function (request, ...rest) {
    return request === "vscode" ? vscode : original.call(this, request, ...rest);
};
