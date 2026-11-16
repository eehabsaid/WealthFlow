import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import { Env, DONE, PLAN, WRITE, spawned, until } from "./env";
import { canRunBrowser, openChat } from "./page";

test("chat UI in Chromium under the webview CSP: attach, plan, approve, diff, no network, no secrets", { skip: !canRunBrowser }, async () => {
  const env = await Env.create([PLAN(), WRITE, DONE]);
  const diffs: string[][] = [];
  const chat = await openChat(env, { pick: async () => [path.join(env.project, "app/money.py")], openDiff: async (id, rel) => void diffs.push([id, rel]) });
  const { page, posted, problems } = chat;
  try {
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
    await chat.close();
    await env.close();
  }
});
