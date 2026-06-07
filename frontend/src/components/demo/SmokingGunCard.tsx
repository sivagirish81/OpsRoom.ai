"use client";

import type { Incident } from "@/lib/api";

function extractSmokingGun(logFindings: Incident["log_findings"]) {
  for (const finding of logFindings || []) {
    const pattern = String(finding.pattern || "");
    if (pattern === "deep_scan_schema_fingerprint" || pattern === "schema_deserialization_error") {
      const evidence = (finding.evidence as string[] | undefined) || [];
      return {
        pattern,
        count: Number(finding.count || evidence.length || 1),
        sample: evidence[0] || "Schema fingerprint mismatch detected",
      };
    }
  }
  return null;
}

export function SmokingGunCard({
  logFindings,
  deployFindings,
  revealed,
}: {
  logFindings: Incident["log_findings"];
  deployFindings?: Incident["deploy_findings"];
  revealed: boolean;
}) {
  const gun = extractSmokingGun(logFindings);
  const deploy = deployFindings?.[0];

  if (!gun) {
    if (!revealed) return null;
    return (
      <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4">
        <p className="text-sm text-amber-100">
          Schema log proof not in stream yet. Ask{" "}
          <span className="font-medium">“Scan logs for the smoking gun”</span> to surface
          AvroTypeException lines.
        </p>
        {deploy && (
          <p className="mt-2 text-xs text-slate-400">
            Correlated deploy: {String(deploy.service)} {String(deploy.version)} (
            {String(deploy.minutes_before_incident)} min before incident)
          </p>
        )}
      </div>
    );
  }

  const isDeepScan = gun.pattern === "deep_scan_schema_fingerprint";

  return (
    <div
      className={`overflow-hidden rounded-xl border transition-all duration-700 ${
        revealed
          ? "border-amber-500/80 bg-gradient-to-br from-amber-950/60 to-rose-950/40 shadow-lg shadow-amber-900/20"
          : "border-war-border bg-war-panel/80"
      }`}
    >
      <div className="flex items-center gap-2 border-b border-amber-900/40 px-4 py-2">
        <span
          className={`h-2.5 w-2.5 rounded-full ${revealed ? "animate-pulse bg-amber-400" : "bg-slate-500"}`}
        />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-amber-300">
          {isDeepScan ? "Smoking gun found" : "Schema errors detected"}
        </h3>
        {revealed && (
          <span className="ml-auto badge bg-amber-900/80 text-amber-200">NEW EVIDENCE</span>
        )}
      </div>
      <div className="space-y-3 p-4">
        <p className="font-mono text-sm leading-relaxed text-amber-100">{gun.sample}</p>
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-lg border border-rose-900/50 bg-rose-950/40 px-3 py-2">
            <p className="text-xs uppercase text-rose-300">Writer schema</p>
            <p className="font-mono text-sm text-rose-100">checkout.v3</p>
          </div>
          <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/40 px-3 py-2">
            <p className="text-xs uppercase text-cyan-300">Reader schema</p>
            <p className="font-mono text-sm text-cyan-100">checkout.v2</p>
          </div>
        </div>
        <p className="text-xs text-slate-400">
          {gun.count} matching log line{gun.count === 1 ? "" : "s"}
          {isDeepScan ? " surfaced by your deep log scan" : " in the stream"} — hypothesis #1
          confidence should jump.
        </p>
      </div>
    </div>
  );
}
