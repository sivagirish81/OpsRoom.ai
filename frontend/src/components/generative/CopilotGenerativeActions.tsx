"use client";

import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";
import { api } from "@/lib/api";
import { useIncidentContext } from "@/context/IncidentContext";
import { HypothesisPanel } from "@/components/generative/Cards";
import { MetricsChart } from "@/components/demo/MetricsChart";
import { SmokingGunCard } from "@/components/demo/SmokingGunCard";

const METRIC_OPTIONS = [
  "kafka_consumer_lag",
  "checkout_latency_ms",
  "error_rate",
  "throughput",
  "redis_used_memory_pct",
  "redis_evicted_keys_per_sec",
] as const;

function GenerativeShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="my-3 overflow-hidden rounded-xl border border-violet-900/50 bg-war-panel/95 shadow-lg">
      <div className="border-b border-violet-900/40 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-violet-300">
        {title} · CopilotKit Generative UI
      </div>
      <div className="p-2">{children}</div>
    </div>
  );
}

function LoadingCard({ label }: { label: string }) {
  return (
    <GenerativeShell title={label}>
      <p className="animate-pulse px-2 py-4 text-sm text-slate-400">Loading live incident data…</p>
    </GenerativeShell>
  );
}

export function CopilotGenerativeActions() {
  const { selectedId, incident } = useIncidentContext();

  useCopilotReadable({
    description: "Active OpsRoom incident summary (no raw hypothesis dumps)",
    value: incident
      ? {
          incident_id: incident.id,
          service: incident.service,
          status: incident.status,
          severity: incident.severity,
          root_cause: incident.suspected_root_cause,
          confidence: incident.confidence,
          hypothesis_count: incident.hypotheses?.length || 0,
        }
      : { message: "No incident selected" },
  });

  useCopilotAction({
    name: "showLiveMetrics",
    description:
      "Render a live metrics chart for the active incident. Use when the user asks about metrics, lag, latency, throughput, or performance.",
    parameters: [
      {
        name: "metrics",
        type: "string[]",
        description:
          "Optional metric names to highlight, e.g. kafka_consumer_lag, checkout_latency_ms, error_rate, throughput.",
        required: false,
      },
    ],
    handler: async ({ metrics }) => {
      if (!selectedId) {
        return { error: "No incident selected" };
      }
      const detail = await api.incident(selectedId);
      const requested = (metrics || []).filter(Boolean);
      const findings = (detail.metrics_findings || []).filter((row) =>
        requested.length ? requested.includes(String(row.metric)) : true,
      );
      return {
        service: detail.service,
        metrics: findings.length ? findings : detail.metrics_findings || [],
        filter: requested,
      };
    },
    render: ({ status, result }) => {
      if (status !== "complete" || !result || "error" in result) {
        return <LoadingCard label="Live Metrics" />;
      }
      const title = result.filter?.length
        ? `Live Metrics (${(result.filter as string[]).join(", ")})`
        : "Live Metrics";
      return (
        <GenerativeShell title={title}>
          <MetricsChart findings={result.metrics as Record<string, unknown>[]} />
        </GenerativeShell>
      );
    },
  });

  useCopilotAction({
    name: "showHypothesisRanking",
    description:
      "Render ranked incident hypotheses with confidence bars. Use when the user asks about hypotheses, root cause candidates, or confidence scores.",
    parameters: [],
    handler: async () => {
      if (!selectedId) {
        return { error: "No incident selected" };
      }
      const detail = await api.incident(selectedId);
      return { hypotheses: detail.hypotheses || [], confidence: detail.confidence };
    },
    render: ({ status, result }) => {
      if (status !== "complete" || !result || "error" in result) {
        return <LoadingCard label="Hypotheses" />;
      }
      return (
        <GenerativeShell title="Hypothesis Ranking">
          <HypothesisPanel
            hypotheses={(result.hypotheses as NonNullable<typeof incident>["hypotheses"]) || []}
            highlightKeyEvidence
          />
        </GenerativeShell>
      );
    },
  });

  useCopilotAction({
    name: "showSmokingGunEvidence",
    description:
      "Render schema mismatch / Avro deserialization smoking-gun evidence. Use after deep log scan or when user asks for proof.",
    parameters: [],
    handler: async () => {
      if (!selectedId) {
        return { error: "No incident selected" };
      }
      const detail = await api.incident(selectedId);
      return { log_findings: detail.log_findings || [] };
    },
    render: ({ status, result }) => {
      if (status !== "complete" || !result || "error" in result) {
        return <LoadingCard label="Smoking Gun" />;
      }
      return (
        <GenerativeShell title="Smoking Gun Evidence">
          <SmokingGunCard
            logFindings={result.log_findings as Record<string, unknown>[]}
            revealed
          />
        </GenerativeShell>
      );
    },
  });

  useCopilotAction({
    name: "showIncidentDashboard",
    description:
      "Render a customizable incident dashboard bundle (metrics + hypotheses + smoking gun). "
      + "Use when the user asks for a overview, summary dashboard, or custom view.",
    parameters: [
      {
        name: "includeMetrics",
        type: "boolean",
        description: "Include live metrics chart",
        required: false,
      },
      {
        name: "includeHypotheses",
        type: "boolean",
        description: "Include hypothesis ranking",
        required: false,
      },
      {
        name: "includeSmokingGun",
        type: "boolean",
        description: "Include smoking gun evidence card",
        required: false,
      },
      {
        name: "metrics",
        type: "string[]",
        description: "Optional metric filter when includeMetrics is true",
        required: false,
      },
    ],
    handler: async ({ includeMetrics = true, includeHypotheses = true, includeSmokingGun = true, metrics }) => {
      if (!selectedId) {
        return { error: "No incident selected" };
      }
      const detail = await api.incident(selectedId);
      const requested = (metrics || []).filter(Boolean);
      const metricRows = (detail.metrics_findings || []).filter((row) =>
        requested.length ? requested.includes(String(row.metric)) : true,
      );
      return {
        service: detail.service,
        includeMetrics,
        includeHypotheses,
        includeSmokingGun,
        metrics: metricRows.length ? metricRows : detail.metrics_findings || [],
        hypotheses: detail.hypotheses || [],
        log_findings: detail.log_findings || [],
        root_cause: detail.suspected_root_cause,
        confidence: detail.confidence,
      };
    },
    render: ({ status, result }) => {
      if (status !== "complete" || !result || "error" in result) {
        return <LoadingCard label="Incident Dashboard" />;
      }
      return (
        <GenerativeShell title={`${result.service as string} — Custom View`}>
          <div className="space-y-3">
            <p className="px-1 text-sm text-slate-300">
              {String(result.root_cause || "")}{" "}
              <span className="text-war-accent">
                ({Math.round(Number(result.confidence || 0) * 100)}%)
              </span>
            </p>
            {result.includeMetrics !== false && (
              <MetricsChart findings={result.metrics as Record<string, unknown>[]} />
            )}
            {result.includeHypotheses !== false && (
              <HypothesisPanel
                hypotheses={(result.hypotheses as NonNullable<typeof incident>["hypotheses"]) || []}
                highlightKeyEvidence
              />
            )}
            {result.includeSmokingGun !== false && (
              <SmokingGunCard
                logFindings={result.log_findings as Record<string, unknown>[]}
                revealed
              />
            )}
          </div>
        </GenerativeShell>
      );
    },
  });

  return null;
}

export { METRIC_OPTIONS };
