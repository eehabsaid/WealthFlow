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
    override: null, // {provider, model} for the next task only
    error: null,
  };
  const listeners = new Set();
  let stopStream = null;
  let timer = null;
  let soon = null;
  let filesKey = "";
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

  async function refresh() {
    try {
      const [server, list] = await Promise.all([
        api.request("GET", `/api/state${stateQuery()}`),
        api.request("GET", "/api/tasks"),
      ]);
      s.server = server;
      s.tasks = list.tasks;
      if (s.taskId) await loadTask();
      s.error = null;
    } catch (error) {
      s.error = error;
    }
    emit();
  }

  function onEvent(id, event) {
    if (id !== s.taskId) return;
    s.events.push(event);
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
    Object.assign(s, { taskId: id, task: null, files: [], events: [] });
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
      const { id } = await api.submit({ goal, provider, model });
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
