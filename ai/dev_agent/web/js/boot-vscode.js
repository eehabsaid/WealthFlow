import { init } from "./app.js";
import { createVsCodeTransport } from "./transport-vscode.js";

init(createVsCodeTransport(acquireVsCodeApi()), document.getElementById("root"));
