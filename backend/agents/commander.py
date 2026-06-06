import weave

from backend.agents.common import finish_agent, start_agent
from backend.agents.evidence_builder import evidence_lines
from backend.state import IncidentGraphState, get_incident, update_incident


@weave.op()
def commander_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Incident Commander")
    incident = get_incident(incident_id)
    lines = evidence_lines(incident)
    top = (incident.get("hypotheses") or [{}])[0]
    summary = {
        "what_happened": (
            f"{incident.get('severity')} incident on {incident.get('service')}: "
            f"{len(incident.get('metrics_findings', []))} metric shifts, "
            f"{len(incident.get('log_findings', []))} log patterns, "
            f"{len(incident.get('deploy_findings', []))} correlated deploys."
        ),
        "why": incident.get("suspected_root_cause"),
        "evidence": top.get("evidence") or lines[:5],
        "confidence": incident.get("confidence", 0),
        "recommended_mitigation": incident.get("recommended_action"),
        "next_steps": [
            "Confirm or reject recommended mitigation",
            "Watch primary service metrics for recovery",
            "Validate fix against retrieved runbook guidance",
        ],
    }
    update_incident(incident_id, {"commander_summary": summary, "active_agent": "Complete"})
    finish_agent(
        incident_id,
        "Incident Commander",
        "Situation report ready for the incident channel.",
        summary,
    )
    return {"commander_summary": summary}
