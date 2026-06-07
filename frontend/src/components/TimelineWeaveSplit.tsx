"use client";

import { useEffect, useRef, useState } from "react";
import { TimelineCard } from "@/components/generative/Cards";
import type { TimelineEvent } from "@/lib/api";

type Health = { status: string; redis: boolean; weave: string | null };

export function TimelineWeaveSplit({
  events,
  apiUrl,
}: {
  events: TimelineEvent[];
  apiUrl: string;
}) {
  const [weaveUrl, setWeaveUrl] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const prevCount = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
        if (!response.ok) return;
        const health = (await response.json()) as Health;
        if (!cancelled) setWeaveUrl(health.weave);
      } catch {
        if (!cancelled) setWeaveUrl(null);
      }
    };
    load();
    const timer = setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [apiUrl]);

  useEffect(() => {
    if (events.length > prevCount.current) {
      setLive(true);
      const timer = setTimeout(() => setLive(false), 4000);
      prevCount.current = events.length;
      return () => clearTimeout(timer);
    }
    prevCount.current = events.length;
  }, [events.length]);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="relative">
        {live && (
          <span className="absolute -top-2 right-2 z-10 flex items-center gap-1.5 rounded-full border border-emerald-800 bg-emerald-950 px-2 py-0.5 text-xs text-war-ok">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            LIVE
          </span>
        )}
        <TimelineCard events={events} />
      </div>

      <div className="card flex flex-col p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-violet-300">
            W&B Weave Traces
          </h3>
          <span className="badge bg-violet-950 text-violet-300">split-screen</span>
        </div>
        <p className="mb-3 text-sm text-slate-300">
          Every agent step is traced — root cause, runbook retrieval, hypotheses, and mitigation
          decisions appear here in real time.
        </p>
        {weaveUrl ? (
          <>
            <a
              href={weaveUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mb-3 break-all rounded-lg border border-violet-900 bg-violet-950/40 px-3 py-2 text-sm text-violet-200 underline-offset-2 hover:underline"
            >
              {weaveUrl}
            </a>
            <a
              href={weaveUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex w-fit rounded-lg bg-violet-700 px-3 py-2 text-sm font-medium hover:bg-violet-600"
            >
              Open Weave in new tab →
            </a>
            <p className="mt-4 text-xs text-slate-500">
              Demo tip: drag this panel beside the war room on a second monitor, or snap browser
              windows side-by-side (UI left · Weave right).
            </p>
          </>
        ) : (
          <p className="text-sm text-slate-400">
            Weave URL unavailable. Set <code className="text-xs">WANDB_API_KEY</code> in{" "}
            <code className="text-xs">.env</code> and restart the backend, or set{" "}
            <code className="text-xs">WEAVE_DISABLED=false</code>.
          </p>
        )}
      </div>
    </div>
  );
}
