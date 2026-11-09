// Copies the shared chat UI (ai/dev_agent/web/css and js) into media/chat so the extension ships exactly what the Web UI runs.
const fs = require("fs");
const path = require("path");

const from = path.resolve(__dirname, "..", "..", "web");
const to = path.resolve(__dirname, "..", "media", "chat");
fs.rmSync(to, { recursive: true, force: true });
for (const dir of ["css", "js"]) {
  fs.mkdirSync(path.join(to, dir), { recursive: true });
  for (const file of fs.readdirSync(path.join(from, dir))) {
    if (file.startsWith("transport-web") || file.startsWith("boot-web")) continue;
    fs.copyFileSync(path.join(from, dir, file), path.join(to, dir, file));
  }
}
console.log("copied chat UI to media/chat");
