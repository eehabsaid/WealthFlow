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
exports.DiffProvider = void 0;
exports.register = register;
exports.openDiff = openDiff;
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const vscode = __importStar(require("vscode"));
const client_1 = require("./client");
const SCHEME = "devagent";
// Serves the recorded ORIGINAL content of a file (from the task ledger) as a read-only virtual document, so VS Code's native diff editor can compare it
// with the file on disk. A file that did not exist before (or no longer exists) shows as empty on that side.
class DiffProvider {
    manager;
    constructor(manager) {
        this.manager = manager;
    }
    static uri(version, taskId, rel) {
        return vscode.Uri.from({ scheme: SCHEME, path: `/${version}/${taskId}/${rel}` });
    }
    async provideTextDocumentContent(uri) {
        const [, version, taskId, ...rest] = uri.path.split("/");
        try {
            return (await this.manager.client?.fileText(taskId, rest.join("/"), version)) ?? "";
        }
        catch (error) {
            if (error instanceof client_1.ApiError && (error.status === 404 || error.status === 415))
                return error.status === 415 ? "(binary file)" : "";
            throw error;
        }
    }
}
exports.DiffProvider = DiffProvider;
function register(context, manager) {
    context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider(SCHEME, new DiffProvider(manager)));
}
async function openDiff(root, id, rel) {
    const onDisk = path.join(root, rel);
    const right = fs.existsSync(onDisk) ? vscode.Uri.file(onDisk) : DiffProvider.uri("current", id, rel);
    await vscode.commands.executeCommand("vscode.diff", DiffProvider.uri("original", id, rel), right, `${rel} (changed by dev_agent)`);
}
