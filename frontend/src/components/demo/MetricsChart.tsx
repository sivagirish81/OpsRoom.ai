"use client";

import type { Incident } from "@/lib/api";

const LABELS: Record<string, string> = {
  kafka_consumer_lag: "Consumer lag",
  checkout_latency_ms: "Checkout latency",
  error_rate: "Error rate",
  throughput: "Throughput",
  redis_used_memory_pct: "Redis memory",
  redis_evicted_keys_per_sec: "Redis evictions/sec",
};

const DEFAULT_METRIC_ORDER = [
  "kafka_consumer_lag",
  "checkout_latency_ms",
  "error_rate",
  "throughput",
  "redis_used_memory_pct",
  "redis_evicted_keys_per_sec",
] as const;

function formatValue(metric: string, value: number): string {
  if (metric === "kafka_consumer_lag") {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
    return String(value);
  }
  if (metric === "error_rate") return `${(value * 100).toFixed(1)}%`;
  if (metric === "checkout_latency_ms") return `${value.toFixed(0)} ms`;
  return String(Math.round(value));
}

function barPercent(metric: string, latest: number, baseline: number): number {
  if (metric === "throughput") {
    if (baseline <= 0) return 50;
    return Math.min(100, Math.max(8, (latest / baseline) * 100));
  }
  const max = Math.max(latest, baseline, 1);
  return Math.min(100, Math.max(8, (latest / max) * 100));
}

function isWorsening(metric: string, latest: number, baseline: number): boolean {
  if (metric === "throughput") return latest < baseline;
  return latest > baseline;
}

export function MetricsChart({
  findings,
  compact,
}: {
  findings: Incident["metrics_findings"];
  compact?: boolean;
}) {
  const available = new Set((findings || []).map((item) => String(item.metric)));
  const order = DEFAULT_METRIC_ORDER.filter((name) => available.has(name));
  const extra = [...available].filter((name) => !order.includes(name as (typeof DEFAULT_METRIC_ORDER)[number]));
  const metricOrder = [...order, ...extra];

  const rows = metricOrder
    .map((name) => (findings || []).find((item) => item.metric === name))
    .filter(Boolean) as Array<Record<string, unknown>>;

  if (!rows.length) {
    return (
      <div className={compact ? "p-2" : "card p-4"}>
        {!compact && (
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-war-accent">
            Live Metrics
          </h3>
        )}
        <p className="text-sm text-slate-400">No metrics available yet — run replay or re-analyze.</p>
      </div>
    );
  }

  return (
    <div className={compact ? "p-1" : "card p-4"}>
      {!compact && (
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-war-accent">
            Live Metrics
          </h3>
          <span className="badge bg-rose-950 text-war-danger">degrading</span>
        </div>
      )}
      <div className="space-y-4">
        {rows.map((row) => {
          const metric = String(row.metric);
          const baseline = Number(row.baseline ?? 0);
          const latest = Number(row.latest ?? 0);
          const worsening = isWorsening(metric, latest, baseline);
          const width = barPercent(metric, latest, baseline);
          return (
            <div key={metric}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-slate-300">{LABELS[metric] || metric}</span>
                <span className={worsening ? "text-rose-300" : "text-emerald-300"}>
                  {formatValue(metric, baseline)} → {formatValue(metric, latest)}
                </span>
              </div>
              <div className="relative h-3 overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${
                    worsening
                      ? "bg-gradient-to-r from-rose-700 to-rose-400"
                      : "bg-gradient-to-r from-emerald-800 to-emerald-500"
                  }`}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
