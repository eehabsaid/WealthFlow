import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { MEDIA } from "./page";

// The pure functions of the chat UI (meter model, "what changed" lines, pending values), run in plain Node. The page's modules are ES modules; a copy in a
// folder marked "type": "module" loads on every Node version (the extension folder itself is CommonJS).
async function load(name: string): Promise<any> {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "devagent-js-"));
  fs.writeFileSync(path.join(dir, "package.json"), '{"type":"module"}');
  for (const file of fs.readdirSync(path.join(MEDIA, "js"))) fs.copyFileSync(path.join(MEDIA, "js", file), path.join(dir, file));
  return import(pathToFileURL(path.join(dir, name)).href);
}

const READING = { used: 40_000, window: 150_000, reserve: 28_000, limit: 122_000, percent: 26.7, remaining: 110_000, remaining_usable: 82_000, level: "ok", source: "provider", reported: { input_tokens: 39_000, output_tokens: 1_000 }, phase: "package P1", step: 3 };

test("meter model: numbers, source, trim marker and level texts", { skip: !fs.existsSync(MEDIA) }, async () => {
  const { meterModel, tokens } = await load("meter.js");
  assert.deepEqual([0, 999, 1000, 1500, 10_000, 150_000, 1_500_000, NaN, undefined].map(tokens), ["0", "999", "1k", "1.5k", "10k", "150k", "1.5M", "0", "0"]);
  assert.equal(meterModel(null), null);
  assert.equal(meterModel({ window: 0 }), null);
  const ok = meterModel(READING);
  assert.deepEqual([ok.level, ok.used, ok.percent, ok.left, ok.bar], ["ok", "40k / 150k", "26.7%", "110k left", 26.7]);
  assert.equal(Math.round(ok.trim * 10) / 10, 81.3, "the marker sits where the agent starts trimming (window minus reserve)");
  assert.match(ok.title, /Context: 40,000 of 150,000 tokens \(26\.7%\)\nFree: 110,000 tokens; 82,000 before the agent trims old steps \(at 122,000\)\nSource: reported by the provider \(prompt 39,000 \+ reply 1,000\)\nAfter package P1, step 3$/);
  const warn = meterModel({ ...READING, used: 105_000, percent: 70, level: "warn", remaining_usable: 17_000 });
  assert.ok(warn.level === "warn" && warn.title.endsWith("Getting full: the agent will soon trim old steps."));
  const hot = meterModel({ ...READING, used: 160_000, percent: 106.7, level: "critical", source: "estimate", remaining: 0, remaining_usable: 0 });
  assert.deepEqual([hot.level, hot.bar, hot.used, hot.percent, hot.left], ["critical", 100, "~160k / 150k", "~106.7%", "~0 left"], "an estimate is marked with ~, the bar never overflows");
  assert.match(hot.title, /estimated by the agent[^\n]*\nAfter package P1, step 3\nNearly full: old steps are about to be trimmed\.$/);
});

test("settings dialog helpers: what is sent and what is said about the result", { skip: !fs.existsSync(MEDIA) }, async () => {
  const { changeLines, pendingValues } = await load("context-settings.js");
  const rows = [
    { spec: { key: "timeout_s", value: 3600 }, input: { value: "3,600" } },
    { spec: { key: "max_fix_rounds", value: 12 }, input: { value: " 7 " } },
    { spec: { key: "context_window", value: 150_000 }, input: { value: "150000" } },
  ];
  assert.deepEqual(pendingValues(rows), { max_fix_rounds: 7 }, "only what differs from the saved value, as numbers");
  assert.equal(pendingValues([{ spec: { key: "timeout_s", value: 1 }, input: { value: "" } }]), null);
  assert.equal(pendingValues([{ spec: { key: "timeout_s", value: 1 }, input: { value: "abc" } }]), null);
  const lines = changeLines({
    changed: [
      { label: "Max fix rounds", old: 12, new: 7 },
      { label: "Model request timeout", old: 3600, new: 30, requested: 10, clamped: true, note: "allowed range is 30 to 86,400" },
      { label: "Reserve for reasoning", old: 140_000, new: 28_192, clamped: true, note: "window minus reserve must stay at least 4,096" },
    ],
    unchanged: [{ label: "Max output per reply", new: 8192, clamped: true, note: "one reply cannot be bigger than the whole window" }, { label: "Max steps per phase", new: 200 }],
  });
  assert.deepEqual(lines, [
    "Max fix rounds: 12 → 7",
    "Model request timeout: 3,600 → 30 (you asked for 10; kept within limits: allowed range is 30 to 86,400)",
    "Reserve for reasoning: 140,000 → 28,192 (you asked for a smaller window; kept within limits: window minus reserve must stay at least 4,096)",
    "Max output per reply: stays 8,192 (one reply cannot be bigger than the whole window)",
  ]);
});
