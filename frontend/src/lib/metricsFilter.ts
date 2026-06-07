import type { Incident } from "@/lib/api";

const METRIC_ALIASES: Record<string, string> = {
  consumer_lag: "kafka_consumer_lag",
  kafka_lag: "kafka_consumer_lag",
  lag: "kafka_consumer_lag",
  error_rate: "error_rate",
  "error rate": "error_rate",
  latency: "checkout_latency_ms",
  checkout_latency: "checkout_latency_ms",
  "checkout latency": "checkout_latency_ms",
  throughput: "throughput",
};

export function normalizeMetricFilter(metricFilter: string[]): string[] {
  return metricFilter
    .map((name) => METRIC_ALIASES[name.trim().toLowerCase()] || name.trim())
    .filter(Boolean);
}

export function filterMetrics(
  findings: Incident["metrics_findings"],
  metricFilter: string[],
): Incident["metrics_findings"] {
  if (!findings?.length) return findings;
  if (!metricFilter.length) return findings;

  const normalized = normalizeMetricFilter(metricFilter);
  const filtered = findings.filter((row) => normalized.includes(String(row.metric)));
  return filtered.length ? filtered : findings;
}
