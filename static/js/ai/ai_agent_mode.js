"use strict";

/**
 * AI Workspace — Ask / Agent switch, live agent steps and the Stop button.
 * Ask = the fast path (instant answers, then the model). Agent = the model investigates the app with tools and
 * answers from what it read. The choice is remembered per user on the server (/api/financial-advisor/ai/chat-mode/).
 * Depends on: ai_core.js (_aiState, _aiT, _escapeHtml).
 */

const AI_MODE_URL = "/api/financial-advisor/ai/chat-mode/";
const AI_STOP_URL = "/api/financial-advisor/ai/stop/";

function _aiCsrfHeaders() {
  return { "Content-Type": "application/json", "X-CSRFToken": window.wfGetCsrfToken?.() || "" };
}

function _aiChatMode() {
  return _aiState.chatMode === "agent" ? "agent" : "ask";
}

function _aiPaintModeSwitch() {
  const wrap = document.getElementById("ai-ws-mode-switch");
  if (!wrap) return;
  wrap.hidden = _aiState.agentEnabled === false;
  const mode = _aiChatMode();
  wrap.querySelectorAll("button[data-mode]").forEach((btn) => {
    const active = btn.dataset.mode === mode;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
  const hint = document.getElementById("ai-ws-mode-hint");
  if (hint) {
    hint.textContent =
      mode === "agent"
        ? _aiT(
            "ai_mode_agent_hint",
            "Agent: investigates your data and the app with tools. Slower, answers from facts."
          )
        : _aiT("ai_mode_ask_hint", "Ask: fast answers.");
    hint.title = hint.textContent;
  }
}

// Chat domains the sysadmin allows: with one only there is no choice, so the dropdown is hidden and that domain is used.
function _aiPaintDomains() {
  const select = document.getElementById("ai-ws-domain-select");
  const domains = _aiState.domains;
  if (!select || !Array.isArray(domains) || !domains.length) return;
  select.hidden = domains.length < 2;
  if (domains.length === 1) select.value = domains[0];
}

async function _aiLoadChatMode() {
  try {
    const res = await fetch(AI_MODE_URL);
    if (res.ok) {
      const data = await res.json();
      _aiState.chatMode = data.mode;
      _aiState.agentEnabled = data.agent_enabled !== false;
      _aiState.domains = Array.isArray(data.domains) ? data.domains : null;
    }
  } catch (_e) {
    // The switch simply keeps its default (Ask) when the server cannot be reached.
  }
  _aiPaintModeSwitch();
  _aiPaintDomains();
}

async function _aiSetChatMode(mode) {
  _aiState.chatMode = mode === "agent" ? "agent" : "ask";
  _aiPaintModeSwitch();
  try {
    await fetch(AI_MODE_URL, {
      method: "POST",
      headers: _aiCsrfHeaders(),
      body: JSON.stringify({ mode: _aiState.chatMode }),
    });
  } catch (_e) {
    // Remembering the choice is best effort; this request still uses the chosen mode.
  }
}

function _aiStepLabel(step) {
  const fallback = step.label || String(step.tool || "").replace(/_/g, " ");
  return _aiT(`ai_agent_tool_${step.tool}`, fallback).replace("{target}", step.target || "");
}

function _aiStepIcon(status) {
  if (status === "running")
    return '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>';
  return status === "ok"
    ? '<i class="bi bi-check-circle-fill text-success"></i>'
    : '<i class="bi bi-x-circle-fill text-danger"></i>';
}

function _aiRenderAgentSteps(data) {
  const body = document.querySelector("#ai-ws-typing-bubble .ai-ws-msg-body");
  if (!body || !Array.isArray(data.steps)) return;
  let box = document.getElementById("ai-ws-agent-steps");
  if (!box) {
    box = document.createElement("div");
    box.id = "ai-ws-agent-steps";
    box.className = "ai-ws-agent-steps";
    body.appendChild(box);
  }
  const rows = data.steps
    .map(
      (s) =>
        `<li class="ai-ws-agent-step ${s.status}">${_aiStepIcon(s.status)} <span>${_escapeHtml(_aiStepLabel(s))}</span></li>`
    )
    .join("");
  const stop = data.can_stop
    ? `<button type="button" class="btn btn-sm btn-outline-danger ai-ws-agent-stop" id="ai-ws-agent-stop" onclick="_aiStopAgent()"><i class="bi bi-stop-circle me-1"></i>${_escapeHtml(_aiT("ai_agent_stop", "Stop"))}</button>`
    : "";
  box.innerHTML = `<ol class="ai-ws-agent-step-list">${rows}</ol>${stop}`;
}

async function _aiStopAgent() {
  const btn = document.getElementById("ai-ws-agent-stop");
  if (btn) btn.disabled = true;
  try {
    await fetch(AI_STOP_URL, {
      method: "POST",
      headers: _aiCsrfHeaders(),
      body: JSON.stringify({ conversation_id: _aiState.conversationId }),
    });
    _updateThinkingBubbleText(_aiT("ai_agent_stopping", "Stopping after the current step..."));
  } catch (_e) {
    if (btn) btn.disabled = false;
  }
}

window._aiChatMode = _aiChatMode;
window._aiLoadChatMode = _aiLoadChatMode;
window._aiSetChatMode = _aiSetChatMode;
window._aiPaintModeSwitch = _aiPaintModeSwitch;
window._aiRenderAgentSteps = _aiRenderAgentSteps;
window._aiStopAgent = _aiStopAgent;
