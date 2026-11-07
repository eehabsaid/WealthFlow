// Talks to the local server. The access token comes from the address fragment (#token=...), which is never sent over the network.
const KEY = "dev_agent_token";
let token = "";

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function loadToken() {
  const found = /token=([^&]+)/.exec(location.hash);
  try {
    if (found) {
      sessionStorage.setItem(KEY, decodeURIComponent(found[1]));
      history.replaceState(null, "", location.pathname + location.search);
    }
    token = sessionStorage.getItem(KEY) || "";
  } catch (_error) {
    token = found ? decodeURIComponent(found[1]) : token;
  }
  return Boolean(token);
}

function headers(json) {
  const out = { Authorization: `Bearer ${token}` };
  if (json) out["Content-Type"] = "application/json";
  return out;
}

export async function request(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: headers(body !== undefined),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const isJson = (response.headers.get("Content-Type") || "").includes("json");
  const data = isJson && text ? JSON.parse(text) : text;
  if (!response.ok) {
    throw new ApiError(
      response.status,
      (data && data.code) || "error",
      (data && data.error) || `HTTP ${response.status}`,
    );
  }
  return data;
}

export const get = (path) => request("GET", path);
export const post = (path, body = {}) => request("POST", path, body);

// Server-sent events over fetch (EventSource cannot send the Authorization header). Reconnects with Last-Event-ID; returns a stop function.
export function stream(taskId, after, onEvent) {
  let last = after;
  const controller = new AbortController();
  const run = async () => {
    while (!controller.signal.aborted) {
      try {
        const response = await fetch(`/api/tasks/${taskId}/events?stream=1`, {
          headers: { ...headers(false), "Last-Event-ID": String(last) },
          signal: controller.signal,
        });
        if (!response.ok)
          throw new ApiError(response.status, "error", "stream refused");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let cut = buffer.indexOf("\n\n");
          while (cut >= 0) {
            const block = buffer.slice(0, cut);
            buffer = buffer.slice(cut + 2);
            const line = block.split("\n").find((l) => l.startsWith("data: "));
            if (line) {
              const event = JSON.parse(line.slice(6));
              last = Math.max(last, event.seq);
              onEvent(event);
            }
            cut = buffer.indexOf("\n\n");
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  };
  run();
  return () => controller.abort();
}
