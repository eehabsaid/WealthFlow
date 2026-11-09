import * as vscode from "vscode";

// The "dev_agent" Output channel. Tokens and API-key-looking strings are masked before anything is written.
export class Log {
  private readonly channel = vscode.window.createOutputChannel("dev_agent");

  static mask(text: string): string {
    return text.replace(/Bearer\s+\S+/gi, "Bearer ***").replace(/\b(sk-[A-Za-z0-9_-]{10,}|AIza[0-9A-Za-z_-]{20,}|[0-9a-f]{40,})\b/g, "***");
  }

  line(text: string): void {
    this.channel.appendLine(`${new Date().toLocaleTimeString()}  ${Log.mask(text)}`);
  }

  show(): void {
    this.channel.show(true);
  }

  dispose(): void {
    this.channel.dispose();
  }
}
