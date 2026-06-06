import operator
from typing import Annotated, Any

import weave
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from backend.agents.commander import commander_agent
from backend.agents.deploy import deploy_agent
from backend.agents.intake import intake_agent
from backend.agents.logs import logs_agent
from backend.agents.metrics import metrics_agent
from backend.agents.mitigation import mitigation_agent
from backend.agents.root_cause import root_cause_agent
from backend.agents.runbook_memory import runbook_memory_agent
from backend.locks import incident_lock
from backend.priority import highest_priority_incident
from backend.state import IncidentGraphState, get_incident


class OpsRoomState(IncidentGraphState, total=False):
    messages: Annotated[list[Any], operator.add]


builder = StateGraph(OpsRoomState)
builder.add_node("intake", intake_agent)
builder.add_node("metrics", metrics_agent)
builder.add_node("logs", logs_agent)
builder.add_node("deploy", deploy_agent)
builder.add_node("runbook_memory", runbook_memory_agent)
builder.add_node("root_cause", root_cause_agent)
builder.add_node("mitigation", mitigation_agent)
builder.add_node("commander", commander_agent)
builder.add_edge(START, "intake")
builder.add_edge("intake", "metrics")
builder.add_edge("metrics", "logs")
builder.add_edge("logs", "deploy")
builder.add_edge("deploy", "runbook_memory")
builder.add_edge("runbook_memory", "root_cause")
builder.add_edge("root_cause", "mitigation")
builder.add_edge("mitigation", "commander")
builder.add_edge("commander", END)
graph = builder.compile()


@weave.op()
def run_incident_workflow(incident_id: str | None = None, user_message: str = "") -> dict:
    selected = incident_id or highest_priority_incident()
    if not selected:
        raise ValueError("No incidents are available. Seed or replay an incident first.")
    with incident_lock(selected, "diagnosis", timeout=180) as acquired:
        if not acquired:
            return get_incident(selected)
        graph.invoke({"incident_id": selected, "user_message": user_message, "messages": []})
    return get_incident(selected)

