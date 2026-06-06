import type { Incident } from "@/lib/api";

export function RootCauseCard({ incident }: { incident: Incident }) {
  return (
    <div className="card p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-war-accent">
          Root Cause
        </h3>
        <span className="badge bg-cyan-950 text-war-accent">
          {(incident.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <p className="text-sm leading-relaxed text-slate-200">{incident.suspected_root_cause}</p>
    </div>
  );
}

export function TimelineCard({ events }: { events: Array<{ agent: string; message: string; event_type: string; timestamp?: string }> }) {
  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-war-accent">
        Live Timeline
      </h3>
      <div className="max-h-64 space-y-3 overflow-y-auto pr-1">
        {events.length === 0 && (
          <p className="text-sm text-slate-400">Waiting for agent activity…</p>
        )}
        {events.map((event, index) => (
          <div key={`${event.agent}-${index}`} className="border-l-2 border-war-accent/40 pl-3">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="font-mono text-war-accent">{event.agent}</span>
              <span>•</span>
              <span>{event.event_type}</span>
            </div>
            <p className="mt-1 text-sm text-slate-200">{event.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function MitigationApprovalCard({
  incident,
  onApprove,
  onReject,
  busy,
}: {
  incident: Incident;
  onApprove: () => void;
  onReject: () => void;
  busy: boolean;
}) {
  const awaiting = incident.status === "awaiting_approval";
  return (
    <div className="card p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-war-warn">
        Mitigation Approval
      </h3>
      <p className="mb-3 text-sm text-slate-200">{incident.recommended_action}</p>
      {awaiting ? (
        <div className="flex flex-wrap gap-2">
          <button
            disabled={busy}
            onClick={onApprove}
            className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            Approve rollback
          </button>
          <button
            disabled={busy}
            onClick={onReject}
            className="rounded-lg bg-rose-700 px-3 py-2 text-sm font-medium hover:bg-rose-600 disabled:opacity-50"
          >
            Reject rollback
          </button>
        </div>
      ) : (
        <span className={`badge ${incident.status === "mitigated" ? "bg-emerald-950 text-war-ok" : "bg-slate-800 text-slate-300"}`}>
          {incident.status}
        </span>
      )}
    </div>
  );
}

export function RunbookMatchCard({
  runbooks,
}: {
  runbooks: NonNullable<Incident["runbook_matches"]>;
}) {
  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-war-accent">
        Retrieved Runbooks
      </h3>
      <div className="space-y-3">
        {runbooks?.length ? (
          runbooks.map((runbook) => (
            <div key={runbook.category} className="rounded-lg border border-war-border p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-100">{runbook.title}</p>
                <span className="badge bg-slate-800 text-slate-300">
                  {(runbook.score * 100).toFixed(0)}% match
                </span>
              </div>
              <p className="mt-2 line-clamp-3 text-xs text-slate-400">{runbook.content.slice(0, 220)}…</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-400">Runbook memory agent has not run yet.</p>
        )}
      </div>
    </div>
  );
}

export function AgentProgressCard({ incident }: { incident: Incident }) {
  const agents = [
    "Metrics Agent",
    "Logs Agent",
    "Deploy Agent",
    "Runbook Memory Agent",
    "Root Cause Agent",
    "Mitigation Agent",
    "Incident Commander",
  ];
  const active = incident.active_agent || "Intake Agent";
  const activeIndex = agents.indexOf(active);

  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-war-accent">
        Agent Progress
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {agents.map((agent, index) => {
          const done = active === "Complete" || (activeIndex >= 0 && index < activeIndex);
          const running = agent === active;
          return (
            <div
              key={agent}
              className={`rounded-lg border px-2 py-2 text-xs ${
                running
                  ? "border-war-accent bg-cyan-950/40 text-war-accent"
                  : done
                    ? "border-emerald-900 bg-emerald-950/20 text-war-ok"
                    : "border-war-border text-slate-400"
              }`}
            >
              {agent}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function HypothesisPanel({
  hypotheses,
}: {
  hypotheses: NonNullable<Incident["hypotheses"]>;
}) {
  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-war-accent">
        Hypotheses
      </h3>
      <div className="space-y-3">
        {hypotheses?.length ? (
          hypotheses.map((item) => (
            <div key={item.rank} className="rounded-lg border border-war-border p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">
                  #{item.rank} {item.title}
                </p>
                <span className="badge bg-slate-800 text-slate-200">
                  {(item.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-400">
                {item.evidence?.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-400">Root cause agent has not ranked hypotheses yet.</p>
        )}
      </div>
    </div>
  );
}

export function IncidentResponseCards({ payload }: { payload: Record<string, unknown> }) {
  if (payload.type !== "incident_response") return null;
  return (
    <div className="my-3 space-y-3">
      <div className="card p-4">
        <h4 className="text-xs uppercase tracking-wide text-war-accent">Copilot Answer</h4>
        <p className="mt-2 text-sm">{String(payload.root_cause || "")}</p>
        <p className="mt-2 text-xs text-slate-400">
          Confidence: {Number(payload.confidence || 0) * 100}% • Action:{" "}
          {String(payload.recommended_action || "")}
        </p>
      </div>
      {Array.isArray(payload.evidence) && payload.evidence.length > 0 && (
        <div className="card p-4">
          <h4 className="text-xs uppercase tracking-wide text-war-accent">Evidence</h4>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-300">
            {(payload.evidence as string[]).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
