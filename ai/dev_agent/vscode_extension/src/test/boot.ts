import { calls, config, state } from "./vscodeMock"; // must be imported before the extension: it installs the fake `vscode`
import { Env, PYTHON, REPO, until } from "./env";

type Ext = typeof import("../extension");
export type Res = { type: string; id?: number; ok?: boolean; data?: any; error?: any; event?: any; name?: string };

// Activate the extension, open its chat view like VS Code would, and give back a function that makes the same calls the webview page makes.
export async function boot(env: Env) {
  const ext = require("../extension") as Ext;
  state.folder = env.project;
  config.pythonPath = PYTHON;
  config.agentPath = REPO;
  const context = { subscriptions: [] as { dispose(): unknown }[], extensionUri: { path: "/ext", scheme: "file", fsPath: "/ext" } };
  ext.activate(context as never);
  await until(() => calls.contexts.get("devAgent.connected") === true || (/offline/.test(state.statusItem.text) && (() => { throw new Error(`offline: ${String(state.statusItem.tooltip)}`); })()), 30000, "server to start");
  const out: Res[] = [];
  let receive: (m: unknown) => void = () => undefined;
  const view = {
    visible: true,
    webview: { options: {} as any, html: "", cspSource: "vscode-webview://x", asWebviewUri: (u: any) => u, postMessage: async (m: Res) => void out.push(m), onDidReceiveMessage: (fn: (m: unknown) => void) => void (receive = fn) },
    onDidDispose: () => undefined,
  };
  calls.views.get("devAgent.chat").resolveWebviewView(view);
  let n = 0;
  const call = async (name: string, args: Record<string, unknown> = {}): Promise<Res> => {
    const id = ++n;
    receive({ type: "call", id, name, args });
    return until(() => out.find((m) => m.type === "res" && m.id === id), 20000, `reply to ${name}`);
  };
  // like VS Code on shutdown: deactivate(), then dispose everything the extension registered
  const closing = { deactivate: async () => (await ext.deactivate(), context.subscriptions.forEach((d) => void d.dispose())) };
  return { ext: closing, view, out, call, send: (m: unknown) => receive(m) };
}
