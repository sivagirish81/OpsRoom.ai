"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCopilotAction, useCopilotChatSuggestions } from "@copilotkit/react-core";
import { api, Incident, TimelineEvent } from "@/lib/api";
import { AgentProgressCard, RunbookMatchCard } from "@/components/generative/Cards";
import { TimelineWeaveSplit } from "@/components/TimelineWeaveSplit";
import { CopilotGenerativeActions } from "@/components/generative/CopilotGenerativeActions";
import { OpsRoomAssistantMessage } from "@/components/generative/OpsRoomAssistantMessage";
import { CopilotPrimaryPanel } from "@/components/CopilotPrimaryPanel";
import { IncidentProvider } from "@/context/IncidentContext";

const API_URL = process.env.NEXT_PUBLIC_OPSROOM_API_URL || "http://localhost:8000";

export function IncidentDashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
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

  const runAction = async (action: () => Promise<Incident>, _successMessage?: string) => {
    setBusy(true);
    try {
      const updated = await action();
      setIncident(updated);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const runDeepLogScan = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 1200));
      await api.deeperLogs(selectedId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deep log scan failed");
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
      await runAction(() => api.approval(selectedId, true));
      return "Rollback approved and recorded in Redis.";
    },
  });

  useCopilotAction({
    name: "rejectRollback",
    description: "Reject rollback for the active incident",
    parameters: [],
    handler: async () => {
      if (!selectedId) return "No incident selected";
      await runAction(() => api.approval(selectedId, false));
      return "Rollback rejected.";
    },
  });

  useCopilotAction({
    name: "requestDeeperLogAnalysis",
    description: "Run a deep log scan and surface schema mismatch evidence",
    parameters: [],
    handler: async () => {
      if (!selectedId) return "No incident selected";
      await runDeepLogScan();
      return "Deep log scan complete. Ask me to show smoking gun evidence or hypothesis ranking.";
    },
  });

  useCopilotChatSuggestions({
    instructions: "Suggest CopilotKit generative dashboard prompts for OpsRoom.ai",
    minSuggestions: 4,
    maxSuggestions: 6,
  });

  const suggestions = useMemo(
    () => [
      { title: "Root cause", message: "What is the most likely root cause?" },
      { title: "Live metrics", message: "Show live metrics for consumer lag and error rate" },
      { title: "Hypotheses", message: "Show the hypothesis ranking" },
      { title: "Schema proof", message: "Show the smoking gun schema mismatch evidence" },
      { title: "Deep scan", message: "Scan logs for the smoking gun" },
    ],
    [],
  );

  return (
    <IncidentProvider selectedId={selectedId} incident={incident}>
      <CopilotGenerativeActions />
      <div className="min-h-screen copilot-first-layout">
        <header className="border-b border-war-border bg-war-panel/60 px-6 py-4">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-violet-300">OpsRoom.ai</p>
              <h1 className="text-2xl font-semibold">Copilot-First War Room</h1>
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span className="badge bg-violet-950 text-violet-300">CopilotKit Generative UI</span>
              <span className="badge bg-emerald-950 text-war-ok">Redis Streams</span>
              <span className="badge bg-cyan-950 text-war-accent">LangGraph Agents</span>
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
                  onClick={() => selectedId && runAction(() => api.analyze(selectedId))}
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
                        ? "border-violet-500/60 bg-violet-950/20"
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
                    No incidents yet. Run <code className="text-xs">make demo</code>.
                  </p>
                )}
              </div>
            </div>
          </section>

          <section className="col-span-12 space-y-4 lg:col-span-6">
            <CopilotPrimaryPanel incident={incident} />
            {incident && <TimelineWeaveSplit events={timeline} apiUrl={API_URL} />}
          </section>

          <section className="col-span-12 space-y-4 lg:col-span-3">
            {incident && (
              <>
                <AgentProgressCard incident={incident} />
                <RunbookMatchCard runbooks={incident.runbook_matches || []} />
              </>
            )}
          </section>
        </main>

        <CopilotSidebar
          defaultOpen
          clickOutsideToClose={false}
          AssistantMessage={OpsRoomAssistantMessage}
          labels={{
            title: "Incident Copilot",
            initial:
              "I'm your generative war room. Ask for live metrics, hypothesis rankings, schema evidence, or say **scan logs for the smoking gun** — I'll render dashboards from live incident data.",
          }}
          suggestions={suggestions}
        />
      </div>
    </IncidentProvider>
  );
}
