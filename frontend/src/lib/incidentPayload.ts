export type GenerativeViews = {
  metrics: boolean;
  hypotheses: boolean;
  smokingGun: boolean;
  metricFilter: string[];
};

export type ParsedAssistantMessage = {
  visibleText: string;
  payload: Record<string, unknown> | null;
  views: GenerativeViews | null;
};

const STRUCTURED_MARKER = "Structured payload:\n";
const GENERATIVE_MARKER = /\[GENERATIVE:([^\]]+)\]/i;

export function defaultViews(): GenerativeViews {
  return { metrics: false, hypotheses: false, smokingGun: false, metricFilter: [] };
}

export function parseViews(raw: string): GenerativeViews {
  const [viewPart, ...extras] = raw.split("|");
  const parts = viewPart.split(",").map((part) => part.trim().toLowerCase()).filter(Boolean);
  let metricFilter: string[] = [];
  for (const extra of extras) {
    if (extra.startsWith("metrics=")) {
      metricFilter = extra
        .slice("metrics=".length)
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }
  const wantsDashboard = parts.includes("dashboard");
  return {
    metrics: parts.includes("metrics") || wantsDashboard,
    hypotheses: parts.includes("hypotheses") || parts.includes("hypothesis") || wantsDashboard,
    smokingGun:
      parts.includes("smokinggun") ||
      parts.includes("smoking_gun") ||
      wantsDashboard,
    metricFilter,
  };
}

export function tryParseIncidentPayload(content: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(content);
    if (parsed && typeof parsed === "object" && parsed.type === "incident_response") {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Fall through.
  }

  const markerIndex = content.indexOf(STRUCTURED_MARKER);
  if (markerIndex >= 0) {
    try {
      const parsed = JSON.parse(content.slice(markerIndex + STRUCTURED_MARKER.length));
      if (parsed?.type === "incident_response") {
        return parsed as Record<string, unknown>;
      }
    } catch {
      return null;
    }
  }
  return null;
}

export function parseAssistantMessage(content: string): ParsedAssistantMessage {
  let visibleText = content;
  let views: GenerativeViews | null = null;

  const generativeMatch = content.match(GENERATIVE_MARKER);
  if (generativeMatch) {
    views = parseViews(generativeMatch[1]);
    visibleText = visibleText.replace(GENERATIVE_MARKER, "").trim();
  }

  const payload = tryParseIncidentPayload(content);
  if (payload) {
    const markerIndex = visibleText.indexOf(STRUCTURED_MARKER);
    if (markerIndex >= 0) {
      visibleText = visibleText.slice(0, markerIndex).trim();
    }
    if (!views) {
      views = {
        metrics: payload.show_metrics !== false,
        hypotheses: payload.show_hypotheses !== false,
        smokingGun: payload.show_smoking_gun !== false,
        metricFilter: [],
      };
    }
  }

  return { visibleText, payload, views };
}
