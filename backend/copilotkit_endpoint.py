import json
from typing import Any

import weave
from copilotkit import LangGraphAGUIAgent
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from backend.graph import run_incident_workflow
from backend.priority import highest_priority_incident
from backend.state import get_incident


def _last_user_message(messages: list[Any]) -> str:
    for message in reversed(messages):
        role = getattr(message, "type", None) or getattr(message, "role", None)
        if role in {"human", "user"}:
            return str(getattr(message, "content", message))
    return ""


@weave.op()
def answer_incident_question(state: MessagesState) -> dict[str, list[AIMessage]]:
    question = _last_user_message(state.get("messages", []))
    incident_id = highest_priority_incident()
    if not incident_id:
        return {
            "messages": [
                AIMessage(content="No active incident is available. Run the sample replay first.")
            ]
        }
    lowered = question.lower()
    if any(term in lowered for term in ("deeper", "analyze", "investigate", "refresh")):
        incident = run_incident_workflow(incident_id, question)
    else:
        incident = get_incident(incident_id)
    summary = incident.get("commander_summary", {})
    payload = {
        "type": "incident_response",
        "incident_id": incident_id,
        "question": question,
        "root_cause": incident.get("suspected_root_cause"),
        "confidence": incident.get("confidence"),
        "evidence": summary.get("evidence", []),
        "recent_deploys": incident.get("deploy_findings", []),
        "recommended_action": incident.get("recommended_action"),
        "requires_human_approval": incident.get("status") == "awaiting_approval",
        "runbooks": incident.get("runbook_matches", []),
    }
    answer = (
        f"Most likely root cause: {payload['root_cause']}\n\n"
        f"Confidence: {float(payload['confidence'] or 0) * 100:.0f}%\n"
        f"Recommended action: {payload['recommended_action']}\n\n"
        f"Structured payload:\n{json.dumps(payload)}"
    )
    return {"messages": [AIMessage(content=answer)]}


chat_builder = StateGraph(MessagesState)
chat_builder.add_node("answer", answer_incident_question)
chat_builder.add_edge(START, "answer")
chat_builder.add_edge("answer", END)
copilot_graph = chat_builder.compile(checkpointer=MemorySaver())

opsroom_chat_agent = LangGraphAGUIAgent(
    name="opsroom",
    description="OpsRoom incident commander with live Redis-backed incident context.",
    graph=copilot_graph,
)

