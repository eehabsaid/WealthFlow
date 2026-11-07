import { ApiError } from "./errors.js";

// VS Code webview transport. The page has no network access (strict CSP) and no token or keys: every call is a postMessage to the extension host,
// which owns the connection, checks it against an allowlist and answers with plain data.
export function createVsCodeTransport(vscode, host = window) {
  const waiting = new Map();
  const listeners = new Set();
  let n = 0;

  host.addEventListener("message", ({ data }) => {
    if (!data) return;
    if (data.type === "res" && waiting.has(data.id)) {
      const { resolve, reject } = waiting.get(data.id);
      waiting.delete(data.id);
      if (data.ok) resolve(data.data);
      else reject(new ApiError(data.error.status, data.error.code, data.error.message));
    } else if (data.type === "event") {
      listeners.forEach((fn) => fn(data));
    }
  });

  const call = (name, args = {}) =>
    new Promise((resolve, reject) => {
      n += 1;
      waiting.set(n, { resolve, reject });
      vscode.postMessage({ type: "call", id: n, name, args });
    });

  return {
    kind: "vscode",
    keysInPage: false,
    request: (method, path, body) => call("request", { method, path, body }),
    // The host keeps one live stream; events for other tasks are ignored here.
    subscribe(taskId, onEvent) {
      const fn = (message) => message.taskId === taskId && onEvent(message.event);
      listeners.add(fn);
      call("subscribe", { taskId }).catch(() => undefined);
      return () => {
        listeners.delete(fn);
        call("unsubscribe").catch(() => undefined);
      };
    },
    state: { get: () => vscode.getState() || {}, set: (value) => vscode.setState(value) },
    attach: (kind) => call("attach", { kind }),
    detach: (id) => call("detach", { id }),
    submit: ({ goal, provider, model }) => call("submit", { goal, provider, model }),
    openDiff: (taskId, path) => call("openDiff", { taskId, path }),
    openReport: (taskId) => call("openReport", { taskId }),
    setApiKey: (provider) => call("setApiKey", { provider }),
    menu: () => call("menu"),
    restart: () => call("restart"),
  };
}
