// The HTML of the chat view. The strict CSP is the isolation boundary: the page may load only the extension's own scripts and styles and cannot make
// any network request (no connect-src), so it cannot reach the agent server or anything else. It talks to the extension host by postMessage only.
export interface HtmlOptions {
  cspSource: string;
  uri: (relative: string) => string;
}

const STYLES = ["theme", "controls", "chat", "cards", "files", "composer", "overlays"];

export function webviewHtml(o: HtmlOptions): string {
  const csp = `default-src 'none'; style-src ${o.cspSource}; script-src ${o.cspSource}; img-src ${o.cspSource} data:; font-src ${o.cspSource};`;
  const links = STYLES.map((s) => `<link rel="stylesheet" href="${o.uri(`css/${s}.css`)}">`).join("\n    ");
  return `<!doctype html>
<html lang="en" class="vscode">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="${csp}">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    ${links}
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="${o.uri("js/boot-vscode.js")}"></script>
  </body>
</html>
`;
}
