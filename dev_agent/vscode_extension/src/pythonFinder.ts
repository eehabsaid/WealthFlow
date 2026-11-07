import { execFile } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";

export interface PythonCommand {
  command: string;
  args: string[];
}

function run(cmd: PythonCommand, extra: string[], cwd: string): Promise<{ ok: boolean; out: string }> {
  return new Promise((resolve) => {
    execFile(cmd.command, [...cmd.args, ...extra], { cwd, timeout: 15000, windowsHide: true }, (error, stdout, stderr) =>
      resolve({ ok: !error, out: `${stdout}${stderr}`.trim() }),
    );
  });
}

export function candidates(root: string, configured: string, platform: NodeJS.Platform = process.platform): PythonCommand[] {
  const list: PythonCommand[] = [];
  if (configured.trim()) list.push({ command: configured.trim(), args: [] });
  for (const venv of [".venv", "venv", "env"]) {
    const exe = platform === "win32" ? path.join(root, venv, "Scripts", "python.exe") : path.join(root, venv, "bin", "python");
    if (fs.existsSync(exe)) list.push({ command: exe, args: [] });
  }
  if (platform === "win32") list.push({ command: "py", args: ["-3.12"] }, { command: "py", args: ["-3"] }, { command: "python", args: [] });
  else list.push({ command: "python3", args: [] }, { command: "python", args: [] });
  return list;
}

// The first interpreter (Python 3.10+) that can import dev_agent from the project folder. The error says what was tried.
export async function findPython(root: string, configured: string, agentPath: string): Promise<PythonCommand> {
  const tried: string[] = [];
  const probe = "import sys; assert sys.version_info >= (3, 10); import dev_agent";
  for (const cmd of candidates(root, configured)) {
    const label = [cmd.command, ...cmd.args].join(" ");
    const result = await run(cmd, ["-c", probe], agentPath);
    if (result.ok) return cmd;
    tried.push(`${label}: ${result.out.split("\n").pop() || "failed"}`);
  }
  throw new Error(
    `No Python 3.10+ that can import dev_agent from ${agentPath}.\nSet "devAgent.pythonPath" (for example your project's venv python).\nTried:\n  ${tried.join("\n  ")}`,
  );
}
