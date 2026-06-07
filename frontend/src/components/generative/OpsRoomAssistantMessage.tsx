"use client";

import { AssistantMessageProps } from "@copilotkit/react-ui";
import { Markdown } from "@copilotkit/react-ui";
import { useIncidentContext } from "@/context/IncidentContext";
import { parseAssistantMessage } from "@/lib/incidentPayload";
import { GenerativeViewRenderer } from "@/components/generative/GenerativeViewRenderer";

export function OpsRoomAssistantMessage(props: AssistantMessageProps) {
  const { message, isLoading, markdownTagRenderers } = props;
  const { selectedId } = useIncidentContext();
  const rawContent = String(message?.content || "");
  const { visibleText, payload, views } = parseAssistantMessage(rawContent);
  const hasGenerative = Boolean(views || payload);

  return (
    <>
      {visibleText && (
        <div className="copilotKitMessage copilotKitAssistantMessage">
          <Markdown content={visibleText} components={markdownTagRenderers} />
        </div>
      )}
      {!isLoading && hasGenerative && (
        <GenerativeViewRenderer
          incidentId={selectedId || (payload?.incident_id as string | undefined) || null}
          views={views}
          payload={payload}
        />
      )}
      {isLoading && !visibleText && (
        <div className="copilotKitMessage copilotKitAssistantMessage">
          <p className="text-sm text-slate-400">Analyzing incident…</p>
        </div>
      )}
    </>
  );
}
