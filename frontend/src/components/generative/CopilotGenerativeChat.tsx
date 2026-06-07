"use client";

import { TextMessage, Role } from "@copilotkit/runtime-client-gql";
import { useCopilotChat } from "@copilotkit/react-core";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { useIncidentContext } from "@/context/IncidentContext";
import { parseViews } from "@/lib/incidentPayload";

function detectGenerativeIntent(message: string): string | null {
  const lowered = message.toLowerCase();
  if (
    lowered.includes("metric") ||
    lowered.includes("lag") ||
    lowered.includes("latency") ||
    lowered.includes("throughput") ||
    lowered.includes("chart")
  ) {
    return "metrics";
  }
  if (
    lowered.includes("hypothesis") ||
    lowered.includes("confidence") ||
    lowered.includes("rank")
  ) {
    return "hypotheses";
  }
  if (
    lowered.includes("smoking gun") ||
    lowered.includes("avro") ||
    lowered.includes("schema") ||
    lowered.includes("fingerprint")
  ) {
    return "smokinggun";
  }
  if (lowered.includes("dashboard") || lowered.includes("custom view")) {
    return "metrics,hypotheses";
  }
  return null;
}

function responseForView(view: string, service: string): string {
  const views = parseViews(view);
  const parts: string[] = [];
  if (views.metrics) parts.push("live metrics");
  if (views.hypotheses) parts.push("hypothesis ranking");
  if (views.smokingGun) parts.push("schema evidence");
  return `Here is the ${parts.join(" and ")} for ${service}.\n\n[GENERATIVE:${view}]`;
}

export function useCopilotGenerativeSubmit() {
  const { appendMessage } = useCopilotChat();
  const { selectedId, incident } = useIncidentContext();

  return useCallback(
    async (message: string) => {
      const view = detectGenerativeIntent(message);
      if (!view || !selectedId) {
        return false;
      }

      let service = incident?.service || "the active incident";
      if (!incident) {
        try {
          const detail = await api.incident(selectedId);
          service = detail.service;
        } catch {
          return false;
        }
      }

      await appendMessage(
        new TextMessage({ role: Role.User, content: message }),
        { followUp: false },
      );
      await appendMessage(
        new TextMessage({
          role: Role.Assistant,
          content: responseForView(view, service),
        }),
        { followUp: false },
      );
      return true;
    },
    [appendMessage, incident, selectedId],
  );
}
