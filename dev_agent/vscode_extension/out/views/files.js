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
exports.FilesView = void 0;
const vscode = __importStar(require("vscode"));
const ICON = {
    written: "diff-modified",
    unchanged: "circle-outline",
    rolled_back: "discard",
    rollback_failed: "error",
    conflict: "warning",
    failed: "error",
    rejected: "circle-slash",
};
class FilesView {
    store;
    emitter = new vscode.EventEmitter();
    onDidChangeTreeData = this.emitter.event;
    constructor(store) {
        this.store = store;
        store.onChange(() => this.emitter.fire());
    }
    getTreeItem(file) {
        const item = new vscode.TreeItem(file.path, vscode.TreeItemCollapsibleState.None);
        item.description = file.state.replace(/_/g, " ");
        item.tooltip = file.detail ? `${file.path}\n${file.state}: ${file.detail}` : `${file.path}\n${file.state}`;
        item.iconPath = new vscode.ThemeIcon(ICON[file.state] ?? "file");
        item.command = { command: "devAgent.openDiff", title: "Show diff", arguments: [file.path] };
        return item;
    }
    getChildren() {
        return this.store.files;
    }
}
exports.FilesView = FilesView;
