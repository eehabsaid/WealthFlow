// Shapes of the local server's JSON (see dev_agent/server). Only what the extension reads.
export interface TaskRow {
  id: string;
  goal: string;
  status: string;
  updated: string;
  stop_reason: string;
}

export interface PlanStep {
  title: string;
  files?: string[];
}

export interface Plan {
  summary: string;
  steps: PlanStep[];
  files_add: string[];
  files_edit: string[];
  files_delete: string[];
  files_rename: { from: string; to: string }[];
  needs_owner_approval: string[];
  tests: string[];
  risks: string[];
}

export interface TaskDetail extends TaskRow {
  plan: Plan | null;
  approved_at: string;
  answer?: string;
}

export interface Approval {
  id: string;
  kind: string;
  message: string;
}

export interface ServerState {
  busy: boolean;
  current: { id: string; phase: string } | null;
  approvals: Approval[];
  provider: string;
  model: string;
}

export interface FileRow {
  path: string;
  state: string;
  detail: string;
}

export interface AgentEvent {
  seq: number;
  type: string;
  [key: string]: unknown;
}

export type Version = "original" | "current";
export type KeyStatus = Record<string, boolean | null>;
