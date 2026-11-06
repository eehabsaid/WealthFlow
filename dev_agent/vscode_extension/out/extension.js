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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const approvals_1 = require("./approvals");
const commands_1 = require("./commands");
const diff = __importStar(require("./diff"));
const log_1 = require("./log");
const manager_1 = require("./manager");
const state_1 = require("./state");
const statusBar_1 = require("./statusBar");
const files_1 = require("./views/files");
const plan_1 = require("./views/plan");
const progress_1 = require("./views/progress");
const tasks_1 = require("./views/tasks");
let manager;
function activate(context) {
    const log = new log_1.Log();
    const store = new state_1.Store(() => manager?.client);
    manager = new manager_1.ServerManager(log, store);
    const approvals = new approvals_1.Approvals(store, manager);
    const status = new statusBar_1.StatusBar(manager, store, approvals);
    const tree = (id, provider) => vscode.window.createTreeView(id, { treeDataProvider: provider, showCollapseAll: false });
    context.subscriptions.push(log, status, tree("devAgent.tasks", new tasks_1.TasksView(store)), tree("devAgent.plan", new plan_1.PlanView(store)), tree("devAgent.progress", new progress_1.ProgressView(store)), tree("devAgent.files", new files_1.FilesView(store)));
    diff.register(context, manager);
    (0, commands_1.registerCommands)({ context, log, manager, store, approvals });
    context.subscriptions.push({ dispose: () => void manager?.stop() });
    void manager.start();
}
// Stop the hidden server (and any command it is running) when the window closes.
async function deactivate() {
    await manager?.stop();
}
