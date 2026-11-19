// The data every card renders: server state, task list, the open task with its files and live events. One store per page; the transport hides
// whether the server is reached directly (browser) or through the VS Code extension host.
const LIVE = new Set([
  "status",
  "done",
  "package",
  "verify",
  "phase",
  "attachments",
  "approval_request",
  "approval_result",
]);
const MAX_EVENTS = 2000;
const MAX_EARLIER = 8; // earlier tasks of the chat shown above the open one
const FINISHED = new Set(["completed", "answered", "stopped", "rejected"]);

export function createStore(api) {
  const s = {
    server: {
      busy: false,
      current: null,
      approvals: [],
      provider: "",
      model: "",
      vision: false,
      vision_note: "",
    },
    tasks: [],
    taskId: "",
    task: null,
    files: [],
    events: [],
    earlier: [], // [{task, events, files}] the earlier tasks of the open chat, oldest first: the chat is one continuous conversation
    context: null, // newest `context` event of the open task (the meter reads it)
    override: null, // {provider, model} for the next task only
    error: null,
  };
  const listeners = new Set();
  let stopStream = null;
  let timer = null;
  let soon = null;
  let filesKey = "";
  const cache = new Map(); // finished earlier tasks never change: loaded once
  const emit = () => listeners.forEach((fn) => fn());

  const stateQuery = () =>
    s.override
      ? `?provider=${encodeURIComponent(s.override.provider)}&model=${encodeURIComponent(s.override.model)}`
      : "";

  async function loadTask() {
    const id = s.taskId;
    const task = await api.request("GET", `/api/tasks/${id}`);
    if (id !== s.taskId) return;
    s.task = task;
    const key = `${task.updated}|${JSON.stringify(task.files || {})}`; // `updated` only has one-second resolution
    if (key !== filesKey) {
      const found = await api.request("GET", `/api/tasks/${id}/files`);
      if (id === s.taskId) {
        s.files = found.files;
        filesKey = key;
      }
    }
  }

  // The tasks that came before the open one in the same chat, loaded in full (task, every event, files) so the page can show the whole conversation.
  async function loadEarlier() {
    const task = s.task;
    if (!task) return;
    const chat = task.chat_id || task.id;
    const ids = s.tasks
      .filter((t) => (t.chat || t.id) === chat && t.id < task.id)
      .map((t) => t.id)
      .sort()
      .slice(-MAX_EARLIER);
    const out = [];
    for (const id of ids) {
      let item = cache.get(id);
      if (!item || !FINISHED.has(item.task.status)) {
        const loaded = await api.request("GET", `/api/tasks/${id}`);
        const events = [];
        for (let after = 0; ; ) {
          const page = await api.request("GET", `/api/tasks/${id}/events?after=${after}`);
          if (!page.events.length) break;
          events.push(...page.events);
          after = page.next;
        }
        const files = Object.keys(loaded.files || {}).length ? (await api.request("GET", `/api/tasks/${id}/files`)).files : [];
        item = { task: loaded, events: events.slice(-MAX_EVENTS), files };
        cache.set(id, item);
      }
      out.push(item);
    }
    if (task === s.task) s.earlier = out;
  }

  async function refresh() {
    try {
      const [server, list] = await Promise.all([
        api.request("GET", `/api/state${stateQuery()}`),
        api.request("GET", "/api/tasks"),
      ]);
      s.server = server;
      s.tasks = list.tasks;
      if (s.taskId) {
        await loadTask();
        await loadEarlier();
      }
      s.error = null;
    } catch (error) {
      s.error = error;
    }
    emit();
  }

  function onEvent(id, event) {
    if (id !== s.taskId) return;
    s.events.push(event);
    if (event.type === "context") s.context = event;
    if (s.events.length > MAX_EVENTS) s.events.splice(0, s.events.length - MAX_EVENTS);
    emit();
    if (LIVE.has(event.type)) {
      clearTimeout(soon);
      soon = setTimeout(refresh, 200);
    }
  }

  function open(id) {
    if (stopStream) stopStream();
    stopStream = null;
    Object.assign(s, { taskId: id, task: null, files: [], events: [], earlier: [], context: null });
    filesKey = "";
    if (id) stopStream = api.subscribe(id, (event) => onEvent(id, event));
    if (api.state) api.state.set({ taskId: id });
    emit();
    return refresh();
  }

  async function act(method, path, body) {
    try {
      const result = await api.request(method, path, body);
      await refresh();
      return result;
    } catch (error) {
      s.error = error;
      emit();
      throw error;
    }
  }

  return {
    s,
    on: (fn) => (listeners.add(fn), () => listeners.delete(fn)),
    refresh,
    open,
    newChat: () => open(""),
    start() {
      const saved = api.state && api.state.get();
      if (saved && saved.taskId) open(saved.taskId);
      else refresh();
      timer = setInterval(refresh, 2000);
    },
    stop: () => clearInterval(timer),
    setOverride(value) {
      s.override = value;
      return refresh();
    },
    async submit(goal) {
      const { provider, model } = s.override || {};
      const { id } = await api.submit({ goal, provider, model, chat: s.taskId }); // a message in an open chat continues it (queued while a task runs); "New chat" clears taskId
      s.override = null;
      await open(id);
    },
    approve: (id) => act("POST", `/api/tasks/${id}/approve`, {}),
    reject: (id) => act("POST", `/api/tasks/${id}/reject`, {}),
    resume: (id) => act("POST", `/api/tasks/${id}/resume`, {}),
    stopRun: () => act("POST", "/api/stop", {}),
    answer: (aid, approve) => act("POST", `/api/approvals/${aid}`, { approve }),
    saveModel: (provider, model) => act("PUT", "/api/settings", { values: { provider, model } }),
  };
}
