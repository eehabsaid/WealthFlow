import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import { createRequire } from "node:module";
import * as path from "node:path";
import { test } from "node:test";
import { Bridge, type Host } from "../bridge";
import { webviewHtml } from "../html";
import { Env, DONE, PLAN, WRITE, spawned, until } from "./env";

// The REAL chat UI (media/chat) in a real Chromium, under the REAL webview CSP, talking through the REAL bridge to a REAL agent server.
// Only VS Code itself is replaced by a shim (acquireVsCodeApi -> postMessage). Skipped when Playwright/Chromium is not installed.
const MEDIA = path.resolve(__dirname, "../../media/chat");
let chromium: any;
try {
  chromium = createRequire(__filename)("playwright").chromium;
} catch {
  /* not installed */
}

test("chat UI in Chromium under the webview CSP: attach, plan, approve, diff, no network, no secrets", { skip: !chromium || !fs.existsSync(MEDIA) }, async () => {
  const env = await Env.create([PLAN(), WRITE, DONE]);
  const diffs: string[][] = [];
  const posted: unknown[] = [];
  let page: any;
  const host: Host = {
    client: () => env.client, offlineReason: () => "", projectRoot: () => env.project,
    pick: async () => [path.join(env.project, "app/money.py")],
    openDiff: async (id, rel) => void diffs.push([id, rel]),
    openReport: async () => undefined, setApiKey: async () => undefined, menu: async () => undefined, restart: async () => undefined,
  };
  const bridge = new Bridge(host, (m) => void page.evaluate((x: unknown) => (globalThis as any).postMessage(x, "*"), m).catch(() => undefined));
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
  try {
    page = await browser.newPage();
    const problems: string[] = [];
    page.on("pageerror", (e: Error) => problems.push(e.message));
    page.on("console", (m: { type(): string; text(): string }) => m.type() === "error" && problems.push(m.text()));
    await page.exposeFunction("__toHost", (m: unknown) => (posted.push(m), void bridge.handle(m as never)));
    await page.addInitScript(() => {
      (globalThis as any).acquireVsCodeApi = () => ({ postMessage: (m: unknown) => (globalThis as any).__toHost(m), getState: () => null, setState: () => undefined });
    });
    html = webviewHtml({ cspSource: origin, uri: (r) => `${origin}/${r}` });
    await page.goto(`${origin}/`);
    await page.waitForSelector("#goal", { timeout: 5000 }).catch((e: Error) => { throw new Error(`${e.message}\n${problems.join("\n")}`); });

    // the page cannot reach the network, not even the real agent server
    const blocked = await page.evaluate((u: string) => fetch(u).then(() => "reached", () => "blocked"), `http://127.0.0.1:${env.client.port}/api/health`);
    assert.equal(blocked, "blocked");

    await page.click("#attach-file");
    await page.waitForSelector("text=money.py");
    await page.fill("#goal", "add more");
    await page.click("#send-btn");
    await page.waitForSelector("[data-act=approve]", { timeout: 30000 });
    await page.click("[data-act=approve]");
    await page.waitForSelector(".final", { timeout: 30000 });
    assert.equal(fs.readFileSync(path.join(env.project, "app/more.py"), "utf8"), "X = 1\n");
    await page.click("[data-act=diff]");
    await until(() => diffs.length > 0, 10000, "diff request");
    assert.equal(diffs[0][1], "app/more.py");

    const token = spawned.at(-1)?.token ?? "";
    assert.ok(token.length >= 32);
    assert.ok(!(await page.content()).includes(token) && !JSON.stringify(posted).includes(token), "no token in the page");
    assert.deepEqual(problems.filter((p) => !/favicon|api\/health/.test(p)), [], "no console errors or CSP violations");
  } catch (error) {
    if (process.env.DEV_AGENT_TRACE) console.error(await page.innerText("body"), JSON.stringify(posted).slice(0, 1500));
    throw error;
  } finally {
    bridge.dispose();
    await browser.close();
    files.close();
    await env.close();
  }
});
