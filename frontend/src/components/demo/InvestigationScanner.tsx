"use client";

const SCAN_LINES = [
  "Tailing checkout-consumer /var/log/app.log …",
  "Filtering ERROR level events (last 15 min) …",
  "Pattern match: AvroTypeException …",
  "Cross-referencing schema registry fingerprints …",
  "MATCH: writer checkout.v3 ≠ reader checkout.v2",
];

export function InvestigationScanner({ active }: { active: boolean }) {
  if (!active) return null;

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-slate-950/85 backdrop-blur-sm">
      <div className="w-full max-w-md px-6">
        <div className="mb-4 flex items-center gap-2">
          <span className="h-3 w-3 animate-ping rounded-full bg-cyan-400" />
          <p className="text-sm font-semibold uppercase tracking-wide text-cyan-300">
            Deep log scan in progress
          </p>
        </div>
        <div className="rounded-lg border border-cyan-900/50 bg-black/60 p-4 font-mono text-xs">
          {SCAN_LINES.map((line, index) => (
            <p
              key={line}
              className="text-cyan-100/90"
              style={{ animation: `fadeIn 0.4s ease ${index * 0.35}s both` }}
            >
              <span className="text-cyan-500">{">"}</span> {line}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
