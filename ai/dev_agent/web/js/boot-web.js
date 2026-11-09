import { init } from "./app.js";
import { createWebTransport, login } from "./transport-web.js";

const root = document.getElementById("root");
login()
  .catch(() => undefined) // a wrong token shows up as 401 on the first request, with the banner text
  .finally(() => init(createWebTransport(), root));
