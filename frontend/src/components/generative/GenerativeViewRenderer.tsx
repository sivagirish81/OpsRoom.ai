"use client";

import { useEffect, useMemo, useState } from "react";
import { api, Incident } from "@/lib/api";
import { useIncidentContext } from "@/context/IncidentContext";
import type { GenerativeViews } from "@/lib/incidentPayload";
import { filterMetrics } from "@/lib/metricsFilter";
import { HypothesisPanel } from "@/components/generative/Cards";
import { MetricsChart } from "@/components/demo/MetricsChart";
import { SmokingGunCard } from "@/components/demo/SmokingGunCard";

export function GenerativeViewRenderer({
  incidentId,
  views,
  payload,
}: {
  incidentId: string | null;
  views: GenerativeViews | null;
  payload: Record<string, unknown> | null;
}) {
  const { incident: contextIncident, selectedId } = useIncidentContext();
  const [fetchedIncident, setFetchedIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);
  const activeIncidentId = incidentId || selectedId;
  const incident = contextIncident || fetchedIncident;

  useEffect(() => {
    if (contextIncident || !activeIncidentId) {
      setFetchedIncident(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const load = async () => {
      try {
        const detail = await api.incident(activeIncidentId);
        if (!cancelled) setFetchedIncident(detail);
      } catch {
        if (!cancelled) setFetchedIncident(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [activeIncidentId, contextIncident]);

  if (!views || (!views.metrics && !views.hypotheses && !views.smokingGun)) {
    return null;
  }

  const metrics = useMemo(
    () =>
      filterMetrics(
        (payload?.metrics_findings as Incident["metrics_findings"]) || incident?.metrics_findings,
        views.metricFilter,
      ),
    [views.metricFilter, incident?.metrics_findings, payload?.metrics_findings],
  );
  const hypotheses = (payload?.hypotheses as Incident["hypotheses"]) || incident?.hypotheses;
  const logFindings = (payload?.log_findings as Incident["log_findings"]) || incident?.log_findings;

  const panelLabel = views.smokingGun
    ? "Schema proof"
    : views.hypotheses
      ? "Hypothesis ranking"
      : "Live metrics";

  return (
    <div className="generative-copilot-panel mt-3 space-y-3 rounded-xl border border-violet-900/50 bg-slate-900/95 p-2 shadow-lg shadow-violet-950/20">
      <p className="px-1 text-[10px] font-semibold uppercase tracking-wide text-violet-300">
        {panelLabel} · live Redis data
      </p>
      {loading && views.metrics && (
        <p className="px-2 py-3 text-sm text-slate-400">Loading live metrics…</p>
      )}
      {views.metrics && !loading && <MetricsChart findings={metrics} compact />}
      {views.hypotheses && (
        <HypothesisPanel hypotheses={hypotheses || []} highlightKeyEvidence compact />
      )}
      {views.smokingGun && (
        <SmokingGunCard
          logFindings={logFindings}
          deployFindings={incident?.deploy_findings}
          revealed
        />
      )}
    </div>
  );
}
