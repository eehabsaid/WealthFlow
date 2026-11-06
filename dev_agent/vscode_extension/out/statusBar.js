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
exports.StatusBar = void 0;
const vscode = __importStar(require("vscode"));
class StatusBar {
    manager;
    store;
    approvals;
    item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
    constructor(manager, store, approvals) {
        this.manager = manager;
        this.store = store;
        this.approvals = approvals;
        manager.onStatus(() => this.update());
        store.onChange(() => this.update());
        this.update();
        this.item.show();
    }
    update() {
        const { status, error } = this.manager;
        const state = this.store.state;
        const set = (text, tip, command, bad = false) => {
            this.item.text = text;
            this.item.tooltip = tip;
            this.item.command = command;
            this.item.backgroundColor = bad ? new vscode.ThemeColor("statusBarItem.warningBackground") : undefined;
        };
        if (status === "starting")
            return set("$(sync~spin) dev_agent: starting", "Starting the agent server", "devAgent.showLog");
        if (status === "error")
            return set("$(error) dev_agent: offline", `${error}\nClick to restart`, "devAgent.restartServer", true);
        if (status === "stopped")
            return set("$(circle-slash) dev_agent: stopped", "Click to start", "devAgent.restartServer");
        if (this.approvals.pending.length > 0)
            return set("$(bell) dev_agent: approval needed", this.approvals.pending[0].message.slice(0, 200), "devAgent.showApproval", true);
        const model = state ? `${state.provider}: ${state.model || "no model chosen"}` : "";
        if (state?.busy)
            return set(`$(sync~spin) dev_agent: ${state.current?.phase ?? "working"}`, `Working (${model}). Click to see progress.`, "devAgent.showProgress");
        set("$(robot) dev_agent", `Idle (${model})`, "devAgent.newTask");
    }
    dispose() {
        this.item.dispose();
    }
}
exports.StatusBar = StatusBar;
