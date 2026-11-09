import { ApiError } from "./errors.js";

const MAX_TEXT = 2000000; // refuse absurd files in the browser before sending; the server applies the real budget
const MAX_IMAGE = 3000000;
const IMAGES = ["image/png", "image/jpeg", "image/gif", "image/webp"];

// Browser transport. The access token arrives once in the address (#token=...), is traded for an HttpOnly session cookie and removed from the
// address bar; after that page scripts never hold it. Requests carry the cookie only.
export async function login() {
  const found = /token=([^&]+)/.exec(location.hash);
  if (!found) return;
  const token = decodeURIComponent(found[1]);
  history.replaceState(null, "", location.pathname + location.search);
  const response = await fetch("/api/session", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok)
    throw new ApiError(response.status, "unauthorized", "Access token missing or wrong.");
}

async function request(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const isJson = (response.headers.get("Content-Type") || "").includes("json");
  const data = isJson && text ? JSON.parse(text) : text;
  if (!response.ok)
    throw new ApiError(
      response.status,
      (data && data.code) || "error",
      (data && data.error) || `HTTP ${response.status}`
    );
  return data;
}

// Server-sent events over fetch; reconnects with Last-Event-ID. Returns a stop function.
function subscribe(taskId, onEvent) {
  let last = 0;
  const controller = new AbortController();
  (async () => {
    while (!controller.signal.aborted) {
      try {
        const response = await fetch(`/api/tasks/${taskId}/events?stream=1`, {
          headers: { "Last-Event-ID": String(last) },
          signal: controller.signal,
        });
        if (!response.ok) throw new ApiError(response.status, "error", "stream refused");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          for (let cut = buffer.indexOf("\n\n"); cut >= 0; cut = buffer.indexOf("\n\n")) {
            const line = buffer
              .slice(0, cut)
              .split("\n")
              .find((l) => l.startsWith("data: "));
            buffer = buffer.slice(cut + 2);
            if (line) {
              const event = JSON.parse(line.slice(6));
              last = Math.max(last, event.seq);
              onEvent(event);
            }
          }
        }
      } catch (error) {
        if (controller.signal.aborted || (error instanceof ApiError && error.status === 401))
          return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  })();
  return () => controller.abort();
}

function choose(accept) {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.accept = accept;
    input.addEventListener("change", () => resolve([...input.files]));
    input.addEventListener("cancel", () => resolve([]));
    input.click();
  });
}

const base64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

export function createWebTransport() {
  const pending = new Map();
  let n = 0;
  return {
    kind: "web",
    keysInPage: true,
    request,
    subscribe,
    state: {
      get: () => {
        try {
          return JSON.parse(sessionStorage.getItem("dev_agent_ui") || "{}");
        } catch (_error) {
          return {};
        }
      },
      set: (value) => {
        try {
          sessionStorage.setItem("dev_agent_ui", JSON.stringify(value));
        } catch (_error) {
          /* storage unavailable: the open task is simply not remembered */
        }
      },
    },
    // Reads the chosen files here in the page; the content stays in memory until the task is sent. Returns {chips, rejected}.
    async attach(kind) {
      const chips = [];
      const rejected = [];
      for (const file of await choose(kind === "image" ? IMAGES.join(",") : "")) {
        n += 1;
        const id = `w${n}`;
        try {
          if (kind === "image") {
            if (!IMAGES.includes(file.type)) throw new Error("only PNG, JPEG, GIF or WebP images");
            if (file.size > MAX_IMAGE) throw new Error("larger than 3 MB");
            pending.set(id, { kind, name: file.name, mime: file.type, data: await base64(file) });
            chips.push({ id, name: file.name, kind, size: file.size });
          } else {
            if (file.size > MAX_TEXT) throw new Error("larger than 2 MB");
            const text = await file.text();
            if (text.includes("\u0000")) throw new Error("this looks like a binary file");
            pending.set(id, { kind, name: file.name, text });
            chips.push({ id, name: file.name, kind, size: file.size, chars: text.length });
          }
        } catch (error) {
          rejected.push({ name: file.name, reason: error.message });
        }
      }
      return { chips, rejected };
    },
    detach: (id) => pending.delete(id),
    async submit({ goal, provider, model }) {
      const body = { goal, attachments: [...pending.values()] };
      if (provider && model) Object.assign(body, { provider, model });
      const result = await request("POST", "/api/tasks", body);
      pending.clear();
      return result;
    },
  };
}
