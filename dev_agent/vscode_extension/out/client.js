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
exports.AgentClient = exports.ApiError = void 0;
const http = __importStar(require("node:http"));
class ApiError extends Error {
    status;
    code;
    constructor(status, code, message) {
        super(message);
        this.status = status;
        this.code = code;
    }
}
exports.ApiError = ApiError;
// Plain Node http client for the local server: loopback only, bearer token, no dependencies.
class AgentClient {
    port;
    token;
    constructor(port, token) {
        this.port = port;
        this.token = token;
    }
    options(method, path, extra = {}) {
        const headers = { Authorization: `Bearer ${this.token}`, ...extra };
        return { host: "127.0.0.1", port: this.port, method, path, headers, agent: false }; // no connection pooling: a server that went away must not leave a request hanging
    }
    request(method, path, body, timeoutMs = 30000) {
        return new Promise((resolve, reject) => {
            const payload = body === undefined ? undefined : Buffer.from(JSON.stringify(body), "utf8");
            const headers = payload ? { "Content-Type": "application/json", "Content-Length": payload.length } : {};
            let finished = false;
            const finish = (fn) => {
                if (finished)
                    return;
                finished = true;
                clearTimeout(deadline);
                fn();
            };
            const req = http.request(this.options(method, path, headers), (res) => {
                const chunks = [];
                res.on("data", (c) => chunks.push(c));
                res.on("error", (e) => finish(() => reject(e)));
                res.on("aborted", () => finish(() => reject(new Error("the agent server closed the connection"))));
                res.on("end", () => finish(() => {
                    const text = Buffer.concat(chunks).toString("utf8");
                    const isJson = String(res.headers["content-type"] ?? "").includes("json");
                    const data = isJson && text ? JSON.parse(text) : text;
                    const status = res.statusCode ?? 0;
                    if (status >= 400) {
                        const info = (isJson ? data : {});
                        reject(new ApiError(status, info.code ?? "error", info.error ?? `HTTP ${status}`));
                    }
                    else {
                        resolve(data);
                    }
                }));
            });
            // A hard deadline for the whole request (a socket idle-timeout alone is not enough if the server disappears mid-request).
            const deadline = setTimeout(() => {
                req.destroy();
                finish(() => reject(new Error("the agent server did not answer in time")));
            }, timeoutMs);
            req.on("error", (e) => finish(() => reject(e)));
            req.end(payload);
        });
    }
    health = () => this.request("GET", "/api/health");
    state = () => this.request("GET", "/api/state");
    tasks = async () => (await this.request("GET", "/api/tasks")).tasks;
    task = (id) => this.request("GET", `/api/tasks/${id}`);
    files = async (id) => (await this.request("GET", `/api/tasks/${id}/files`)).files;
    fileText = (id, path, version) => this.request("GET", `/api/tasks/${id}/file?path=${encodeURIComponent(path)}&version=${version}`);
    report = (id) => this.request("GET", `/api/tasks/${id}/report`);
    startTask = async (goal, attachments = [], override = {}) => (await this.request("POST", "/api/tasks", { goal, attachments, ...override }, 120000)).id;
    approvePlan = (id) => this.request("POST", `/api/tasks/${id}/approve`, {});
    rejectPlan = (id) => this.request("POST", `/api/tasks/${id}/reject`, {});
    resume = (id) => this.request("POST", `/api/tasks/${id}/resume`, {});
    stop = async () => (await this.request("POST", "/api/stop", {})).stopped;
    answer = (approval, approve) => this.request("POST", `/api/approvals/${typeof approval === "string" ? approval : approval.id}`, { approve });
    settings = () => this.request("GET", "/api/settings");
    updateSettings = (values) => this.request("PUT", "/api/settings", { values });
    keys = () => this.request("GET", "/api/keys");
    setKey = (provider, value) => this.request("PUT", `/api/keys/${provider}`, { value });
    deleteKey = (provider) => this.request("DELETE", `/api/keys/${provider}`, {});
    unlockKeys = (passphrase) => this.request("POST", "/api/keys/unlock", { passphrase });
    models = (provider) => this.request("GET", `/api/models?provider=${encodeURIComponent(provider)}`);
    shutdown = () => this.request("POST", "/api/shutdown", {}, 5000);
    // Server-sent events with automatic reconnect that resumes after the last seen sequence number.
    subscribe(taskId, after, onEvent, onDown) {
        let last = after;
        let closed = false;
        let current;
        let retry;
        const connect = () => {
            if (closed)
                return;
            const req = http.request(this.options("GET", `/api/tasks/${taskId}/events?stream=1`, { "Last-Event-ID": String(last) }), (res) => {
                if ((res.statusCode ?? 0) !== 200) {
                    res.resume();
                    return again(new ApiError(res.statusCode ?? 0, "stream", "event stream refused"));
                }
                let buffer = "";
                res.setEncoding("utf8");
                res.on("data", (piece) => {
                    buffer += piece;
                    for (let cut = buffer.indexOf("\n\n"); cut >= 0; cut = buffer.indexOf("\n\n")) {
                        const line = buffer.slice(0, cut).split("\n").find((l) => l.startsWith("data: "));
                        buffer = buffer.slice(cut + 2);
                        if (line) {
                            const event = JSON.parse(line.slice(6));
                            last = Math.max(last, event.seq);
                            onEvent(event);
                        }
                    }
                });
                res.on("end", () => again(new Error("event stream ended")));
                res.on("error", again);
            });
            req.on("error", again);
            req.end();
            current = req;
        };
        const again = (error) => {
            if (closed)
                return;
            onDown?.(error);
            if (error instanceof ApiError && error.status === 401)
                return;
            retry = setTimeout(connect, 1500);
        };
        connect();
        return {
            close: () => {
                closed = true;
                if (retry)
                    clearTimeout(retry);
                current?.destroy();
            },
        };
    }
}
exports.AgentClient = AgentClient;
