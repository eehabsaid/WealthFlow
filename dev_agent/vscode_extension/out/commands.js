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
exports.registerCommands = registerCommands;
const vscode = __importStar(require("vscode"));
const diff_1 = require("./diff");
const settingsCommands_1 = require("./settingsCommands");
function registerCommands(d) {
    const { manager, store, log } = d;
    const add = (id, fn) => {
        d.context.subscriptions.push(vscode.commands.registerCommand(`devAgent.${id}`, async (...args) => {
            try {
                await fn(...args);
            }
            catch (error) {
                log.line(`command ${id} failed: ${error.message}`);
                void vscode.window.showErrorMessage(`dev_agent: ${error.message}`);
            }
        }));
    };
    const client = () => {
        const c = manager.client;
        if (!c)
            throw new Error(manager.error || "the agent server is not running (try dev_agent: Restart server)");
        return c;
    };
    const taskId = () => {
        if (!store.selectedId)
            throw new Error("select a task first");
        return store.selectedId;
    };
    const submit = async (goal) => {
        const id = await client().startTask(goal.trim());
        store.expect(id);
        store.select(id);
        void vscode.commands.executeCommand("devAgent.progress.focus");
        log.line(`task ${id} started`);
    };
    add("newTask", async () => {
        const goal = await vscode.window.showInputBox({ prompt: "What should the agent do?", placeHolder: "e.g. add input validation to app/forms.py", ignoreFocusOut: true });
        if (goal?.trim())
            await submit(goal);
    });
    add("newTaskFromEditor", async () => {
        const editor = vscode.window.activeTextEditor;
        const text = editor ? (editor.selection.isEmpty ? editor.document.getText() : editor.document.getText(editor.selection)) : "";
        if (!text.trim())
            throw new Error("open an editor with the task text (or select it) first");
        await submit(text);
    });
    add("selectTask", (id) => store.select(id));
    add("approvePlan", async () => client().approvePlan(taskId()));
    add("rejectPlan", async () => client().rejectPlan(taskId()));
    add("resume", async () => client().resume(taskId()));
    add("stop", async () => {
        const stopped = await client().stop();
        void vscode.window.showInformationMessage(stopped ? "Stopping: running commands are being terminated." : "Nothing is running.");
        await store.refresh();
    });
    add("openDiff", async (rel) => (0, diff_1.openDiff)(store, manager.settings().projectRoot ?? "", rel));
    add("showReport", async () => {
        const text = await client().report(taskId());
        await vscode.window.showTextDocument(await vscode.workspace.openTextDocument({ language: "markdown", content: text }), { preview: true });
    });
    add("showApproval", () => d.approvals.reopen());
    add("showProgress", () => vscode.commands.executeCommand("devAgent.progress.focus"));
    add("refresh", () => store.refresh());
    add("restartServer", () => manager.restart());
    add("showLog", () => log.show());
    (0, settingsCommands_1.registerSettingsCommands)(add, client, store);
}
