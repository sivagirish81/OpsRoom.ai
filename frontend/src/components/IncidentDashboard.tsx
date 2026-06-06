"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCopilotAction, useCopilotChatSuggestions } from "@copilotkit/react-core";
import { api, Incident, TimelineEvent } from "@/lib/api";
import {
  AgentProgressCard,
  HypothesisPanel,
  MitigationApprovalCard,
  RootCauseCard,
  RunbookMatchCard,
  TimelineCard,
} from "@/components/generative/Cards";
import { ChatGenerativeRenderer } from "@/components/ChatGenerativeRenderer";

const AGENT_NAMES = [
  "Metrics Agent",
  "Logs Agent",
  "Deploy Agent",
  "Runbook Memory Agent",
  "Root Cause Agent",
  "Mitigation Agent",
  "Incident Commander",
];

export function IncidentDashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const rows = await api.incidents();
      setIncidents(rows);
      const active = selectedId || rows[0]?.id || null;
      if (active) {
        setSelectedId(active);
        const [detail, events] = await Promise.all([
          api.incident(active),
          api.timeline(active),
        ]);
        setIncident(detail);
        setTimeline(events);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load incidents");
    }
  }, [selectedId]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 2500);
    return () => clearInterval(timer);
  }, [refresh]);

  const runAction = async (action: () => Promise<Incident>, successMessage: string) => {
    setBusy(true);
    setActionMessage(null);
    try {
      const updated = await action();
      setIncident(updated);
      await refresh();
      setActionMessage(successMessage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  useCopilotAction({
    name: "approveRollback",
    description: "Approve rollback for the active incident",
    parameters: [],
    handler: async () => {
      if (!selectedId) return "No incident selected";
      await runAction(() => api.approval(selectedId, true), "Rollback approved and recorded.");
      return "Rollback approved and recorded in Redis.";
    },
  });

  useCopilotAction({
    name: "rejectRollback",
    description: "Reject rollback for the active incident",
    parameters: [],
    handler: async () => {
      if (!selectedId) return "No incident selected";
      await runAction(() => api.approval(selectedId, false), "Rollback rejected.");
      return "Rollback rejected.";
    },
  });

  useCopilotAction({
    name: "requestDeeperLogAnalysis",
    description: "Ask agents to perform deeper log analysis",
    parameters: [],
    handler: async () => {
      if (!selectedId) return "No incident selected";
      await runAction(
        () => api.deeperLogs(selectedId),
        "Deep scan log injected. Agents re-ran — check timeline and hypothesis #1 evidence.",
      );
      return "Triggered deeper log analysis.";
    },
  });

  useCopilotAction({
    name: "explainHypothesis",
    description: "Explain why the top hypothesis is likely",
    parameters: [],
    handler: async () => {
      if (!selectedId) return "No incident selected";
      await runAction(
        () => api.explainHypothesis(selectedId),
        "Agents re-ran with hypothesis focus — check timeline for new entries.",
      );
      return "Re-ran analysis with hypothesis explanation context.";
    },
  });

  useCopilotChatSuggestions({
    instructions: "Suggest incident commander questions for OpsRoom.ai",
    minSuggestions: 3,
    maxSuggestions: 5,
  });

  const suggestions = useMemo(
    () => [
      { title: "Root cause", message: "What is the most likely root cause?" },
      { title: "Evidence", message: "Show me the evidence." },
      { title: "Changes", message: "What changed before the incident?" },
      { title: "First step", message: "What should I do first?" },
      { title: "Rollback", message: "Why is rollback recommended?" },
    ],
    [],
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-war-border bg-war-panel/60 px-6 py-4">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-war-accent">OpsRoom.ai</p>
            <h1 className="text-2xl font-semibold">Incident War Room</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span className="badge bg-emerald-950 text-war-ok">Redis Streams</span>
            <span className="badge bg-cyan-950 text-war-accent">LangGraph Agents</span>
            <span className="badge bg-violet-950 text-violet-300">W&B Weave</span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1600px] grid-cols-12 gap-4 p-4">
        <section className="col-span-12 lg:col-span-3">
          <div className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">Incidents</h2>
              <button
                className="text-xs text-war-accent hover:underline"
                onClick={() => selectedId && runAction(() => api.analyze(selectedId), "Full agent workflow re-triggered.")}
                disabled={!selectedId || busy}
              >
                Re-analyze
              </button>
            </div>
            {error && <p className="mb-2 text-xs text-rose-400">{error}</p>}
            <div className="space-y-2">
              {incidents.map((row) => (
                <button
                  key={row.id}
                  onClick={() => setSelectedId(row.id)}
                  className={`w-full rounded-lg border p-3 text-left transition ${
                    selectedId === row.id
                      ? "border-war-accent bg-cyan-950/30"
                      : "border-war-border hover:border-slate-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-400">{row.id}</span>
                    <span className="badge bg-rose-950 text-war-danger">{row.severity}</span>
                  </div>
                  <p className="mt-1 text-sm font-medium">{row.service}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    Priority {row.priority_score?.toFixed(1)} • {row.status}
                  </p>
                </button>
              ))}
              {!incidents.length && (
                <p className="text-sm text-slate-400">
                  No incidents yet. Run the seed or replay script.
                </p>
              )}
            </div>
          </div>
        </section>

        <section className="col-span-12 space-y-4 lg:col-span-6">
          {incident ? (
            <>
              <div className="card p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-xl font-semibold">{incident.service}</h2>
                    <p className="text-sm text-slate-400">{incident.id}</p>
                  </div>
                  <div className="flex gap-2">
                    <span className="badge bg-rose-950 text-war-danger">{incident.severity}</span>
                    <span className="badge bg-slate-800">{incident.status}</span>
                    <span className="badge bg-slate-800">{incident.active_agent}</span>
                  </div>
                </div>
              </div>

              <RootCauseCard incident={incident} />
              <HypothesisPanel hypotheses={incident.hypotheses || []} />
              <TimelineCard events={timeline} />
              <MitigationApprovalCard
                incident={incident}
                busy={busy}
                onApprove={() =>
                  selectedId &&
                  runAction(() => api.approval(selectedId, true), "Rollback approved and recorded.")
                }
                onReject={() =>
                  selectedId &&
                  runAction(() => api.approval(selectedId, false), "Rollback rejected.")
                }
              />
              <div className="flex flex-wrap gap-2">
                <button
                  disabled={busy || !selectedId}
                  onClick={() =>
                    selectedId &&
                    runAction(
                      () => api.deeperLogs(selectedId),
                      "Deep scan log injected. Agents re-ran — check timeline and hypothesis #1 evidence.",
                    )
                  }
                  className="rounded-lg border border-war-border px-3 py-2 text-sm hover:border-war-accent disabled:opacity-50"
                >
                  {busy ? "Agents analyzing…" : "Ask for deeper log analysis"}
                </button>
                <button
                  disabled={busy || !selectedId}
                  onClick={() =>
                    selectedId &&
                    runAction(
                      () => api.explainHypothesis(selectedId),
                      "Agents re-ran with hypothesis focus — check timeline for new entries.",
                    )
                  }
                  className="rounded-lg border border-war-border px-3 py-2 text-sm hover:border-war-accent disabled:opacity-50"
                >
                  {busy ? "Agents analyzing…" : "Ask why this hypothesis is likely"}
                </button>
              </div>
              {actionMessage && (
                <div className="rounded-lg border border-emerald-900 bg-emerald-950/30 px-3 py-2 text-sm text-war-ok">
                  {actionMessage}
                </div>
              )}
            </>
          ) : (
            <div className="card p-8 text-center text-slate-400">
              Select or seed an incident to begin the war room demo.
            </div>
          )}
        </section>

        <section className="col-span-12 space-y-4 lg:col-span-3">
          {incident && (
            <>
              <AgentProgressCard incident={incident} />
              <RunbookMatchCard runbooks={incident.runbook_matches || []} />
              <div className="card p-4">
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-war-accent">
                  Agent Cards
                </h3>
                <div className="space-y-2">
                  {AGENT_NAMES.map((name) => (
                    <div key={name} className="rounded-lg border border-war-border px-3 py-2 text-xs">
                      {name}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      </main>

      <CopilotSidebar
        defaultOpen
        labels={{
          title: "Incident Copilot",
          initial: "Ask about root cause, evidence, deploy changes, or mitigation.",
        }}
        suggestions={suggestions}
      />
      <ChatGenerativeRenderer />
    </div>
  );
}
