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
exports.Log = void 0;
const vscode = __importStar(require("vscode"));
// The "dev_agent" Output channel. Tokens and API-key-looking strings are masked before anything is written.
class Log {
    channel = vscode.window.createOutputChannel("dev_agent");
    static mask(text) {
        return text.replace(/Bearer\s+\S+/gi, "Bearer ***").replace(/\b(sk-[A-Za-z0-9_-]{10,}|AIza[0-9A-Za-z_-]{20,}|[0-9a-f]{40,})\b/g, "***");
    }
    line(text) {
        this.channel.appendLine(`${new Date().toLocaleTimeString()}  ${Log.mask(text)}`);
    }
    show() {
        this.channel.show(true);
    }
    dispose() {
        this.channel.dispose();
    }
}
exports.Log = Log;
