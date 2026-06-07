import type { Incident } from "@/lib/api";
import { MetricsChart } from "@/components/demo/MetricsChart";
import { SmokingGunCard } from "@/components/demo/SmokingGunCard";

function isKeyEvidenceLine(line: string): boolean {
  const lowered = line.toLowerCase();
  return (
    lowered.includes("deep_scan") ||
    lowered.includes("deserial") ||
    lowered.includes("avrotypeexception") ||
    lowered.includes("schema fingerprint")
  );
}

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
  previousHypotheses,
  pulseTop,
  highlightKeyEvidence,
  compact,
}: {
  hypotheses: NonNullable<Incident["hypotheses"]>;
  previousHypotheses?: NonNullable<Incident["hypotheses"]>;
  pulseTop?: boolean;
  highlightKeyEvidence?: boolean;
  compact?: boolean;
}) {
  const previousByRank = new Map(
    (previousHypotheses || []).map((item) => [item.rank, item.confidence]),
  );

  return (
    <div className={compact ? "" : "card p-4"}>
      {!compact && (
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-war-accent">
            Hypotheses
          </h3>
          <span className="text-xs text-slate-500">ranked by confidence</span>
        </div>
      )}
      <div className="space-y-3">
        {hypotheses?.length ? (
          hypotheses.map((item) => {
            const previous = previousByRank.get(item.rank);
            const delta =
              previous !== undefined ? Math.round((item.confidence - previous) * 100) : null;
            const isTop = item.rank === 1;
            return (
              <div
                key={item.rank}
                className={`rounded-lg border p-3 transition-all duration-500 ${
                  isTop && pulseTop
                    ? "border-emerald-500/70 bg-emerald-950/20 shadow-md shadow-emerald-900/20"
                    : isTop
                      ? "border-war-accent/40 bg-cyan-950/10"
                      : "border-war-border"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium text-slate-100">
                    #{item.rank} {item.title}
                  </p>
                  <div className="flex shrink-0 items-center gap-2">
                    {delta !== null && delta !== 0 && (
                      <span
                        className={`badge ${
                          delta > 0 ? "bg-emerald-950 text-war-ok" : "bg-rose-950 text-rose-300"
                        } ${pulseTop && isTop ? "confidence-pop" : ""}`}
                      >
                        {delta > 0 ? "+" : ""}
                        {delta}%
                      </span>
                    )}
                    <span
                      className={`badge bg-slate-800 text-slate-200 ${
                        pulseTop && isTop ? "confidence-pop" : ""
                      }`}
                    >
                      {(item.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${
                      isTop ? "bg-gradient-to-r from-cyan-600 to-emerald-400" : "bg-slate-600"
                    }`}
                    style={{ width: `${Math.max(item.confidence * 100, 4)}%` }}
                  />
                </div>
                <ul className="mt-2 space-y-1 pl-0 text-xs">
                  {item.evidence?.map((line) => {
                    const keyEvidence = highlightKeyEvidence && isTop && isKeyEvidenceLine(line);
                    return (
                      <li
                        key={line}
                        className={`list-none rounded-md px-2 py-1 ${
                          keyEvidence
                            ? "border border-amber-700/50 bg-amber-950/40 text-amber-100"
                            : "text-slate-300"
                        }`}
                      >
                        {keyEvidence && (
                          <span className="mr-2 badge bg-amber-900 text-amber-200">KEY EVIDENCE</span>
                        )}
                        {line}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-slate-400">Root cause agent has not ranked hypotheses yet.</p>
        )}
      </div>
    </div>
  );
}

export function IncidentResponseCards({ payload }: { payload: Record<string, unknown> }) {
  if (payload.type !== "incident_response") return null;

  const showMetrics = payload.show_metrics !== false && Array.isArray(payload.metrics_findings);
  const showHypotheses = payload.show_hypotheses !== false && Array.isArray(payload.hypotheses);
  const showSmokingGun = payload.show_smoking_gun !== false && Array.isArray(payload.log_findings);

  return (
    <div className="my-3 max-h-[70vh] space-y-3 overflow-y-auto">
      <div className="card p-4">
        <h4 className="text-xs uppercase tracking-wide text-violet-300">
          CopilotKit Generative UI
        </h4>
        <p className="mt-2 text-sm">{String(payload.root_cause || "")}</p>
        <p className="mt-2 text-xs text-slate-400">
          {String(payload.service || payload.incident_id || "incident")} • Confidence:{" "}
          {Number(payload.confidence || 0) * 100}% • Action:{" "}
          {String(payload.recommended_action || "")}
        </p>
      </div>

      {showMetrics && (
        <MetricsChart findings={payload.metrics_findings as Incident["metrics_findings"]} compact />
      )}

      {showHypotheses && (
        <HypothesisPanel
          hypotheses={payload.hypotheses as NonNullable<Incident["hypotheses"]>}
          highlightKeyEvidence
          compact
        />
      )}

      {showSmokingGun && (
        <SmokingGunCard
          logFindings={payload.log_findings as Incident["log_findings"]}
          revealed
        />
      )}

      {Array.isArray(payload.evidence) && payload.evidence.length > 0 && (
        <div className="card p-4">
          <h4 className="text-xs uppercase tracking-wide text-war-accent">Commander Evidence</h4>
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
