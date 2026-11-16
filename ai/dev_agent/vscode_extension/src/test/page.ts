import * as fs from "node:fs";
import * as http from "node:http";
import { createRequire } from "node:module";
import * as path from "node:path";
import { Bridge, type Host } from "../bridge";
import { webviewHtml } from "../html";
import type { Env } from "./env";

// The REAL chat UI (media/chat) in a real Chromium, under the REAL webview CSP, talking through the REAL bridge to a REAL agent server.
// Only VS Code itself is replaced by a shim (acquireVsCodeApi -> postMessage). Tests using it are skipped when Playwright/Chromium is not installed.
export const MEDIA = path.resolve(__dirname, "../../media/chat");
let chromium: any;
try {
  chromium = createRequire(__filename)("playwright").chromium;
} catch {
  /* not installed */
}
export const canRunBrowser = !!chromium && fs.existsSync(MEDIA);

export async function openChat(env: Env, over: Partial<Host> = {}) {
  const host: Host = {
    client: () => env.client, offlineReason: () => "", projectRoot: () => env.project, pick: async () => [], openDiff: async () => undefined,
    openReport: async () => undefined, setApiKey: async () => undefined, menu: async () => undefined, restart: async () => undefined, ...over,
  };
  let page: any;
  const posted: unknown[] = [];
  const problems: string[] = [];
  const toPage = (m: unknown) => page.evaluate((x: unknown) => (globalThis as any).postMessage(x, "*"), m).catch(() => undefined);
  const bridge = new Bridge(host, (m) => void toPage(m));
  let html = "";
  const files = http.createServer((req, res) => {
    if (req.url === "/") return void res.writeHead(200, { "Content-Type": "text/html" }).end(html);
    const file = path.join(MEDIA, decodeURIComponent((req.url ?? "").split("?")[0]));
    if (!file.startsWith(MEDIA) || !fs.existsSync(file)) return void res.writeHead(404).end();
    res.writeHead(200, { "Content-Type": file.endsWith(".css") ? "text/css" : "text/javascript", "Access-Control-Allow-Origin": "*" }).end(fs.readFileSync(file));
  });
  await new Promise<void>((r) => files.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${(files.address() as { port: number }).port}`;
  const browser = await chromium.launch();
  const close = async () => {
    bridge.dispose();
    await browser.close();
    files.close();
  };
  try {
    page = await browser.newPage();
    page.on("pageerror", (e: Error) => problems.push(e.message));
    page.on("console", (m: { type(): string; text(): string }) => m.type() === "error" && problems.push(m.text()));
    await page.exposeFunction("__toHost", (m: unknown) => (posted.push(m), void bridge.handle(m as never)));
    await page.addInitScript(() => {
      (globalThis as any).acquireVsCodeApi = () => ({ postMessage: (m: unknown) => (globalThis as any).__toHost(m), getState: () => null, setState: () => undefined });
    });
    html = webviewHtml({ cspSource: origin, uri: (r) => `${origin}/${r}` });
    await page.goto(`${origin}/`);
    await page.waitForSelector("#goal", { timeout: 5000 }).catch((e: Error) => { throw new Error(`${e.message}\n${problems.join("\n")}`); });
  } catch (error) {
    await close();
    throw error;
  }
  return { page, posted, problems, toPage, origin, close };
}
