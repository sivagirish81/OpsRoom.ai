import weave

from backend.agents.common import finish_agent, start_agent
from backend.state import IncidentGraphState, get_incident, update_incident
from backend.vector_memory import search_runbooks


@weave.op()
def runbook_memory_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Runbook Memory Agent")
    incident = get_incident(incident_id)
    query = " ".join(
        [
            str(incident.get("service", "")),
            str(incident.get("metrics_findings", "")),
            str(incident.get("log_findings", "")),
            str(incident.get("deploy_findings", "")),
        ]
    )
    matches = search_runbooks(query, top_k=3)
    update_incident(incident_id, {"runbook_matches": matches})
    finish_agent(
        incident_id,
        "Runbook Memory Agent",
        f"Retrieved {len(matches)} similar incidents and runbooks.",
        {"matches": matches},
    )
    return {"runbook_matches": matches}

