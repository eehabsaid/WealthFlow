import * as vscode from "vscode";
import { Bridge, type Host } from "./bridge";
import { webviewHtml } from "./html";

// The chat sidebar: a webview that shows the same UI as the Web UI (the files in media/chat are a build-time copy of dev_agent/web).
export class ChatView implements vscode.WebviewViewProvider {
  static readonly viewType = "devAgent.chat";
  private view: vscode.WebviewView | undefined;
  private bridge: Bridge | undefined;

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
    const bridge = (this.bridge = new Bridge(this.host, (message) => void view.webview.postMessage(message)));
    view.webview.onDidReceiveMessage((message) => void bridge.handle(message));
    view.onDidDispose(() => this.dispose());
  }

  dispose(): void {
    this.bridge?.dispose();
    this.bridge = undefined;
    this.view = undefined;
  }

  focus(): Thenable<unknown> {
    return vscode.commands.executeCommand(`${ChatView.viewType}.focus`);
  }
}
