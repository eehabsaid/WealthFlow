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
exports.PlanView = void 0;
exports.planNodes = planNodes;
const vscode = __importStar(require("vscode"));
function group(label, items, icon) {
    if (!items || items.length === 0)
        return undefined;
    return { label: `${label} (${items.length})`, icon, children: items.map((text) => ({ label: text })) };
}
function planNodes(store) {
    const task = store.task;
    if (!task)
        return [];
    if (!task.plan)
        return [{ label: task.status === "planning" ? "Planning: the agent is reading the project..." : "No plan", icon: "loading~spin" }];
    const plan = task.plan;
    const nodes = [
        { label: plan.summary, icon: "note", tooltip: plan.summary },
        { label: `Steps (${plan.steps.length})`, icon: "list-ordered", children: plan.steps.map((s) => ({ label: s.title, description: (s.files ?? []).join(", ") })) },
        group("Add", plan.files_add, "diff-added"),
        group("Edit", plan.files_edit, "diff-modified"),
        group("DELETE", plan.files_delete, "diff-removed"),
        group("RENAME", plan.files_rename.map((r) => `${r.from} -> ${r.to}`), "arrow-right"),
        group("Protected: will ask you first", plan.needs_owner_approval, "shield"),
        group("Tests", plan.tests, "beaker"),
        group("Risks", plan.risks, "warning"),
    ];
    return nodes.filter((n) => n !== undefined);
}
class PlanView {
    store;
    emitter = new vscode.EventEmitter();
    onDidChangeTreeData = this.emitter.event;
    constructor(store) {
        this.store = store;
        store.onChange(() => {
            void vscode.commands.executeCommand("setContext", "devAgent.awaitingApproval", store.task?.status === "awaiting_approval");
            void vscode.commands.executeCommand("setContext", "devAgent.canResume", store.task?.status === "stopped" && Boolean(store.task.approved_at));
            this.emitter.fire();
        });
    }
    getTreeItem(node) {
        const item = new vscode.TreeItem(node.label, node.children ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.None);
        item.description = node.description;
        item.tooltip = node.tooltip;
        if (node.icon)
            item.iconPath = new vscode.ThemeIcon(node.icon);
        return item;
    }
    getChildren(node) {
        return node ? (node.children ?? []) : planNodes(this.store);
    }
}
exports.PlanView = PlanView;
