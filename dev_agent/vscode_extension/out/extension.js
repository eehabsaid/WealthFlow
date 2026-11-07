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
const chatView_1 = require("./chatView");
const commands_1 = require("./commands");
const diff = __importStar(require("./diff"));
const host_1 = require("./host");
const log_1 = require("./log");
const manager_1 = require("./manager");
const status_1 = require("./status");
const statusBar_1 = require("./statusBar");
let manager;
function activate(context) {
    const log = new log_1.Log();
    const poller = new status_1.Status(() => manager?.client);
    manager = new manager_1.ServerManager(log, poller);
    const chat = new chatView_1.ChatView(context, (0, host_1.createHost)(manager));
    context.subscriptions.push(log, chat, new statusBar_1.StatusBar(manager, poller), vscode.window.registerWebviewViewProvider(chatView_1.ChatView.viewType, chat, { webviewOptions: { retainContextWhenHidden: true } }));
    // A request that blocks the engine must not go unnoticed when the chat is not on screen (first one wins, whichever interface answers).
    let notified = "";
    context.subscriptions.push({
        dispose: poller.onChange(() => {
            const first = poller.state?.approvals[0];
            if (!first || first.id === notified || chat.visible)
                return;
            notified = first.id;
            void vscode.window.showInformationMessage("dev_agent needs your approval.", "Open chat").then((choice) => choice && chat.focus());
        }),
    });
    diff.register(context, manager);
    (0, commands_1.registerCommands)({ context, log, manager, chat });
    context.subscriptions.push({ dispose: () => void manager?.stop() });
    void manager.start();
}
// Stop the hidden server (and any command it is running) when the window closes.
async function deactivate() {
    await manager?.stop();
}
