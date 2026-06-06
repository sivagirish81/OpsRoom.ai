"use client";

import { useMemo } from "react";
import { useCopilotChat } from "@copilotkit/react-core";
import { IncidentResponseCards } from "@/components/generative/Cards";

function tryParseIncidentPayload(content: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(content);
    if (parsed && typeof parsed === "object" && parsed.type === "incident_response") {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Fall through to embedded JSON extraction.
  }

  const marker = "Structured payload:\n";
  const index = content.indexOf(marker);
  if (index >= 0) {
    try {
      const parsed = JSON.parse(content.slice(index + marker.length));
      if (parsed?.type === "incident_response") {
        return parsed as Record<string, unknown>;
      }
    } catch {
      return null;
    }
  }
  return null;
}

export function ChatGenerativeRenderer() {
  const { visibleMessages } = useCopilotChat();
  const messages = visibleMessages ?? [];

  const payload = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index] as { role?: string; content?: string };
      if (message.role && message.role !== "assistant") continue;
      const parsed = tryParseIncidentPayload(String(message.content || ""));
      if (parsed) return parsed;
    }
    return null;
  }, [messages]);

  if (!payload) return null;

  return (
    <div className="fixed bottom-4 left-4 z-50 w-full max-w-md">
      <IncidentResponseCards payload={payload} />
    </div>
  );
}
