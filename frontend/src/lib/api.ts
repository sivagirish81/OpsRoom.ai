const API_URL = process.env.NEXT_PUBLIC_OPSROOM_API_URL || "http://localhost:8000";

export type Incident = {
  id: string;
  status: string;
  severity: string;
  service: string;
  start_time: string;
  suspected_root_cause: string;
  confidence: number;
  recommended_action: string;
  human_approved: boolean;
  active_agent: string;
  priority_score?: number;
  metrics_findings?: Array<Record<string, unknown>>;
  log_findings?: Array<Record<string, unknown>>;
  deploy_findings?: Array<Record<string, unknown>>;
  runbook_matches?: Array<{ title: string; category: string; content: string; score: number }>;
  hypotheses?: Array<{ rank: number; title: string; confidence: number; evidence: string[] }>;
  commander_summary?: {
    what_happened: string;
    why: string;
    evidence: string[];
    confidence: number;
    recommended_mitigation: string;
    next_steps: string[];
  };
};

export type TimelineEvent = {
  id: string;
  incident_id: string;
  agent: string;
  event_type: string;
  message: string;
  timestamp?: string;
  data?: Record<string, unknown>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export const api = {
  incidents: () => request<Incident[]>("/api/incidents"),
  incident: (id: string) => request<Incident>(`/api/incidents/${id}`),
  timeline: (id: string) => request<TimelineEvent[]>(`/api/incidents/${id}/timeline`),
  analyze: (id: string) => request<Incident>(`/api/incidents/${id}/analyze`, { method: "POST" }),
  approval: (id: string, approved: boolean) =>
    request<Incident>(`/api/incidents/${id}/approval?approved=${approved}`, { method: "POST" }),
  deeperLogs: (id: string) =>
    request<Incident>(`/api/incidents/${id}/deeper-log-analysis`, { method: "POST" }),
  explainHypothesis: (id: string) =>
    request<Incident>(`/api/incidents/${id}/explain-hypothesis`, { method: "POST" }),
};
