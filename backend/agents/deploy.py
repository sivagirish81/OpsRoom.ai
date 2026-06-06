from datetime import datetime

import weave

from backend.agents.common import finish_agent, start_agent
from backend.state import IncidentGraphState, get_incident, update_incident
from backend.streams import DEPLOYS, recent_events


@weave.op()
def deploy_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Deploy Agent")
    incident = get_incident(incident_id)
    start = datetime.fromisoformat(str(incident["start_time"]).replace("Z", "+00:00"))
    findings = []
    for event in recent_events(DEPLOYS, incident_id=incident_id):
        deployed_at = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
        delta_minutes = (start - deployed_at).total_seconds() / 60
        if -5 <= delta_minutes <= 60:
            findings.append(
                {
                    "service": event.get("service"),
                    "version": event.get("version"),
                    "commit": event.get("commit"),
                    "deployed_at": event["timestamp"],
                    "minutes_before_incident": round(delta_minutes, 1),
                }
            )
    message = (
        f"{findings[0]['service']} {findings[0]['version']} deployed "
        f"{findings[0]['minutes_before_incident']} minutes before the incident."
        if findings
        else "No deployment correlated with the incident window."
    )
    update_incident(incident_id, {"deploy_findings": findings})
    finish_agent(incident_id, "Deploy Agent", message, {"findings": findings})
    return {"deploy_findings": findings}

