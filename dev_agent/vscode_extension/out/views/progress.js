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
exports.ProgressView = void 0;
exports.progressRows = progressRows;
const vscode = __importStar(require("vscode"));
const str = (v) => (typeof v === "string" ? v : "");
function describe(e) {
    switch (e.type) {
        case "phase":
            return { label: `Phase: ${str(e.phase)}`, icon: "milestone" };
        case "tool":
            return { label: str(e.name), description: str(e.summary), icon: e.ok ? "check" : "error" };
        case "command":
            return { label: str(e.command), description: `${str(e.status)}${typeof e.duration_s === "number" ? ` (${e.duration_s}s)` : ""}`, icon: e.status === "PASSED" ? "terminal" : "error" };
        case "verify":
            return { label: `Checks (${str(e.label)})`, description: str(e.overall), icon: e.overall === "VERIFIED" ? "verified" : "warning" };
        case "status":
            return { label: `Status: ${str(e.status)}`, description: str(e.reason), icon: "info" };
        case "approval_request":
            return { label: `Approval needed (${str(e.kind)})`, description: str(e.message).slice(0, 120), icon: "bell" };
        case "approval_result":
            return { label: e.approved ? "Approved" : "Denied", icon: e.approved ? "thumbsup" : "thumbsdown" };
        case "invalid_reply":
            return { label: "The model's reply was not valid protocol JSON", icon: "warning" };
        case "error":
            return { label: `Error: ${str(e.message)}`, icon: "error" };
        case "done":
            return { label: `Finished: ${str(e.status)}`, icon: "flag" };
        default:
            return undefined;
    }
}
// Work packages are parents; the tool calls, commands and checks that happened during them are their children.
function progressRows(events) {
    const rows = [];
    let current;
    for (const e of events) {
        if (e.type === "package") {
            if (e.status === "running" || !current) {
                current = { label: `${str(e.id)}: ${str(e.title)}`, description: str(e.status), icon: "package", children: [] };
                rows.push(current);
            }
            else {
                current.description = str(e.status);
            }
            continue;
        }
        const row = describe(e);
        if (!row)
            continue;
        if (current && e.type !== "status" && e.type !== "done" && e.type !== "phase")
            current.children?.push(row);
        else
            rows.push(row);
    }
    return rows;
}
class ProgressView {
    store;
    emitter = new vscode.EventEmitter();
    onDidChangeTreeData = this.emitter.event;
    constructor(store) {
        this.store = store;
        store.onChange(() => this.emitter.fire());
    }
    getTreeItem(row) {
        const item = new vscode.TreeItem(row.label, row.children?.length ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.None);
        item.description = row.description;
        item.tooltip = [row.label, row.description].filter(Boolean).join("\n");
        item.iconPath = new vscode.ThemeIcon(row.icon);
        return item;
    }
    getChildren(row) {
        return row ? (row.children ?? []) : progressRows(this.store.events);
    }
}
exports.ProgressView = ProgressView;
