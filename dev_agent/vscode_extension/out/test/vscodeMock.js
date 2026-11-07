"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.state = exports.config = exports.answers = exports.calls = void 0;
// A minimal stand-in for the `vscode` module so the extension's own code (activate, commands, chat view, diff, status bar) runs in plain Node.
// It records what the extension asks VS Code to do. It is NOT VS Code: real-editor behaviour (webview runtime, CSP enforcement) is not covered here.
const node_module_1 = __importDefault(require("node:module"));
exports.calls = { commands: new Map(), executed: [], infos: [], errors: [], contexts: new Map(), providers: new Map(), views: new Map(), docs: [] };
exports.answers = { info: [], input: [], pick: [], open: [] };
exports.config = {};
exports.state = { folder: "", statusItem: { text: "", command: "", tooltip: "" } };
class Emitter {
    fns = [];
    event = (fn) => (this.fns.push(fn), { dispose: () => undefined });
    fire(v) {
        this.fns.forEach((f) => f(v));
    }
}
const uri = (p) => ({ scheme: "file", path: p, fsPath: p, toString: () => `vscode-resource:${p}` });
const vscode = {
    EventEmitter: Emitter,
    ThemeColor: class {
        id;
        constructor(id) {
            this.id = id;
        }
    },
    StatusBarAlignment: { Left: 1 },
    Uri: { file: uri, joinPath: (b, ...p) => uri([b.path, ...p].join("/")), from: (o) => ({ ...o, fsPath: o.path }) },
    window: {
        createOutputChannel: () => ({ appendLine: (l) => void (process.env.DEV_AGENT_TRACE && process.stderr.write(`[log] ${l}\n`)), show: () => undefined, dispose: () => undefined }),
        createStatusBarItem: () => ({ show() { }, dispose() { }, set text(v) { exports.state.statusItem.text = v; }, get text() { return exports.state.statusItem.text; }, set command(v) { exports.state.statusItem.command = v; }, set tooltip(v) { exports.state.statusItem.tooltip = v; }, set backgroundColor(_v) { } }),
        registerWebviewViewProvider: (id, p) => (exports.calls.views.set(id, p), { dispose: () => undefined }),
        showInformationMessage: async (...a) => (exports.calls.infos.push(a), exports.answers.info.shift()),
        showErrorMessage: async (m) => void exports.calls.errors.push(m),
        showInputBox: async () => exports.answers.input.shift(),
        showQuickPick: async () => exports.answers.pick.shift(),
        showOpenDialog: async () => (exports.answers.open.shift() ?? []).map(uri),
        showTextDocument: async () => undefined,
    },
    workspace: {
        get workspaceFolders() { return [{ uri: { fsPath: exports.state.folder } }]; },
        getConfiguration: () => ({ get: (k) => exports.config[k] }),
        registerTextDocumentContentProvider: (scheme, p) => (exports.calls.providers.set(scheme, p), { dispose: () => undefined }),
        openTextDocument: async (o) => (exports.calls.docs.push(o), o),
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
