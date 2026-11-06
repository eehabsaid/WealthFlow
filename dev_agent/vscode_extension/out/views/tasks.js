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
exports.TasksView = exports.STATUS_ICON = void 0;
const vscode = __importStar(require("vscode"));
exports.STATUS_ICON = {
    completed: "pass",
    answered: "comment",
    awaiting_approval: "question",
    executing: "sync~spin",
    planning: "sync~spin",
    approved: "play",
    stopped: "debug-stop",
    rejected: "circle-slash",
    failed: "error",
};
class TasksView {
    store;
    emitter = new vscode.EventEmitter();
    onDidChangeTreeData = this.emitter.event;
    constructor(store) {
        this.store = store;
        store.onChange(() => this.emitter.fire());
    }
    getTreeItem(task) {
        const item = new vscode.TreeItem(task.goal.split("\n")[0].slice(0, 80), vscode.TreeItemCollapsibleState.None);
        item.description = task.status.replace(/_/g, " ");
        item.tooltip = new vscode.MarkdownString().appendText(`${task.goal}\n\n${task.status}${task.stop_reason ? ` - ${task.stop_reason}` : ""}`);
        item.iconPath = new vscode.ThemeIcon(exports.STATUS_ICON[task.status] ?? "circle-outline");
        item.contextValue = task.id === this.store.selectedId ? "task.selected" : "task";
        item.command = { command: "devAgent.selectTask", title: "Open task", arguments: [task.id] };
        return item;
    }
    getChildren() {
        return this.store.tasks;
    }
}
exports.TasksView = TasksView;
