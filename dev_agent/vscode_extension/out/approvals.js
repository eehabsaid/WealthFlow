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
exports.Approvals = void 0;
const vscode = __importStar(require("vscode"));
const client_1 = require("./client");
// Modal approval dialogs. The engine blocks until someone answers; the first answer wins, whichever interface it comes from.
class Approvals {
    store;
    manager;
    asked = new Set();
    dismissed = new Set();
    busy = false;
    constructor(store, manager) {
        this.store = store;
        this.manager = manager;
        store.onChange(() => void this.check());
        store.onPlanReady = (task) => void this.planReady(task);
    }
    get pending() {
        return this.store.state?.approvals ?? [];
    }
    get waiting() {
        return this.pending.filter((a) => this.dismissed.has(a.id)).length || (this.busy ? 1 : 0);
    }
    async check() {
        if (this.busy)
            return;
        const next = this.pending.find((a) => !this.asked.has(a.id));
        if (!next)
            return;
        this.busy = true;
        this.asked.add(next.id);
        try {
            await this.ask(next);
        }
        finally {
            this.busy = false;
            void this.check();
        }
    }
    async ask(approval) {
        const choice = await vscode.window.showWarningMessage(`dev_agent needs your approval (${approval.kind})`, { modal: true, detail: approval.message }, "Approve", "Deny");
        if (!choice) {
            this.dismissed.add(approval.id); // closed without answering: it stays pending, the status bar offers it again
            return;
        }
        this.dismissed.delete(approval.id);
        try {
            await this.manager.client?.answer(approval, choice === "Approve");
        }
        catch (error) {
            if (!(error instanceof client_1.ApiError && error.status === 404))
                void vscode.window.showErrorMessage(`Could not send your answer: ${error.message}`);
        }
        void this.store.refresh();
    }
    async reopen() {
        const next = this.pending.find((a) => this.dismissed.has(a.id)) ?? this.pending[0];
        if (next)
            await this.ask(next);
        else
            void vscode.window.showInformationMessage("Nothing is waiting for your approval.");
    }
    async planReady(task) {
        const plan = task.plan;
        if (!plan)
            return;
        const lines = [plan.summary, "", `Steps: ${plan.steps.length}`];
        const add = (label, items) => void (items.length && lines.push(`${label}: ${items.slice(0, 10).join(", ")}${items.length > 10 ? ", ..." : ""}`));
        add("Add", plan.files_add);
        add("Edit", plan.files_edit);
        add("DELETE", plan.files_delete);
        add("RENAME", plan.files_rename.map((r) => `${r.from} -> ${r.to}`));
        add("Protected (will ask you first)", plan.needs_owner_approval);
        add("Risks", plan.risks);
        const choice = await vscode.window.showInformationMessage("The plan is ready for your review", { modal: true, detail: lines.join("\n") }, "Approve and run", "Reject");
        const client = this.manager.client;
        if (!choice || !client)
            return; // decide later from the Plan view
        try {
            if (choice === "Reject")
                await client.rejectPlan(task.id);
            else
                await client.approvePlan(task.id);
        }
        catch (error) {
            void vscode.window.showErrorMessage(error.message);
        }
        void this.store.refresh();
    }
}
exports.Approvals = Approvals;
