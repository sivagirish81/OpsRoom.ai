"use client";

import type { Incident } from "@/lib/api";

const PROMPTS = [
  "Show me live metrics for consumer lag and error rate",
  "Show the hypothesis ranking with confidence scores",
  "Show the smoking gun schema mismatch evidence",
  "Show a dashboard with metrics and hypotheses only",
  "What is the most likely root cause?",
  "Scan logs for the smoking gun",
];

export function CopilotPrimaryPanel({ incident }: { incident: Incident | null }) {
  return (
    <div className="card flex min-h-[420px] flex-col justify-center p-8">
      <p className="text-xs uppercase tracking-[0.2em] text-violet-300">CopilotKit-first demo</p>
      <h2 className="mt-2 text-2xl font-semibold">Ask the copilot to generate your war room view</h2>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-300">
        Dashboards are not pre-rendered here. Use the{" "}
        <span className="text-war-accent">Incident Copilot</span> sidebar to request metrics charts,
        hypothesis rankings, or schema evidence — CopilotKit renders them inline from live Redis
        incident data.
      </p>

      {incident ? (
        <div className="mt-6 rounded-lg border border-war-border bg-slate-950/40 p-4">
          <p className="text-xs uppercase text-slate-500">Active incident</p>
          <p className="mt-1 font-medium">{incident.service}</p>
          <p className="font-mono text-xs text-slate-400">{incident.id}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="badge bg-rose-950 text-war-danger">{incident.severity}</span>
            <span className="badge bg-slate-800">{incident.status}</span>
            <span className="badge bg-slate-800">{incident.active_agent}</span>
          </div>
        </div>
      ) : (
        <p className="mt-6 text-sm text-slate-400">Seed or replay an incident to begin.</p>
      )}

      <div className="mt-6">
        <p className="mb-2 text-xs uppercase text-slate-500">Try asking</p>
        <ul className="space-y-2 text-sm text-slate-300">
          {PROMPTS.map((prompt) => (
            <li key={prompt} className="rounded-lg border border-war-border/70 px-3 py-2">
              “{prompt}”
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
