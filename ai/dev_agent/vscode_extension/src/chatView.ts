import * as vscode from "vscode";
import { Bridge, type Host } from "./bridge";
import { webviewHtml } from "./html";

// The chat sidebar: a webview that shows the same UI as the Web UI (the files in media/chat are a build-time copy of ai/dev_agent/web).
export class ChatView implements vscode.WebviewViewProvider {
  static readonly viewType = "devAgent.chat";
  private view: vscode.WebviewView | undefined;
  private bridge: Bridge | undefined;
  private queued: string[] = [];
  private ready = false;

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly host: Host,
  ) {}

  get visible(): boolean {
    return this.view?.visible ?? false;
  }

  resolveWebviewView(view: vscode.WebviewView): void {
    this.view = view;
    const media = vscode.Uri.joinPath(this.context.extensionUri, "media", "chat");
    view.webview.options = { enableScripts: true, localResourceRoots: [media] };
    view.webview.html = webviewHtml({
      cspSource: view.webview.cspSource,
      uri: (relative) => view.webview.asWebviewUri(vscode.Uri.joinPath(media, ...relative.split("/"))).toString(),
    });
    this.bridge?.dispose();
    this.ready = false;
    const bridge = (this.bridge = new Bridge(this.host, (message) => void view.webview.postMessage(message)));
    view.webview.onDidReceiveMessage((message) => {
      if (message?.type === "ready") this.flush(); // the page is loaded and listens for commands
      else void bridge.handle(message);
    });
    view.onDidDispose(() => this.dispose());
  }

  dispose(): void {
    this.bridge?.dispose();
    this.bridge = undefined;
    this.view = undefined;
    this.ready = false;
  }

  // Ask the chat page to run one of its own actions (e.g. open "Context & limits"). Queued until the page has loaded, so it also works when the view was closed.
  async command(name: string): Promise<void> {
    this.queued.push(name);
    if (this.view && this.ready) this.flush();
    else if (!this.view) await this.focus(); // opening the view loads the page, which then announces itself with `ready`
  }

  private flush(): void {
    this.ready = true;
    for (const name of this.queued.splice(0)) void this.view?.webview.postMessage({ type: "command", name });
  }

  focus(): Thenable<unknown> {
    return vscode.commands.executeCommand(`${ChatView.viewType}.focus`);
  }
}
