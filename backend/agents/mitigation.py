import weave

from backend.agents.common import finish_agent, start_agent
from backend.state import IncidentGraphState, get_incident, update_incident


def _recommendation(incident: dict) -> tuple[str, bool]:
    runbooks = incident.get("runbook_matches") or []
    if runbooks:
        title = str(runbooks[0].get("title", "")).lower()
        content = str(runbooks[0].get("content", "")).lower()
        if "memory" in title or "memory" in content:
            return (
                "Trim bounded streams, enforce retention on hot keys, scale Redis capacity, "
                "and verify eviction policy — do not flush during incident response.",
                True,
            )
        if "schema" in title or "kafka" in title or "lag" in title:
            return (
                "Rollback the recent consumer/producer deploy, pause risky rollout, "
                "and verify schema compatibility before redeploy.",
                True,
            )
    root = str(incident.get("suspected_root_cause", "")).lower()
    if "redis" in root and "memory" in root:
        return (
            "Reduce memory pressure via retention/trimming and approved capacity scale-up; "
            "avoid flush commands during the incident.",
            True,
        )
    if "schema" in root or "deserial" in root or "deploy" in root:
        return (
            "Rollback the suspect deployment and validate message/schema compatibility before redeploy.",
            True,
        )
    return (
        f"Stabilize {incident.get('service', 'the service')} using runbook guidance and monitor recovery.",
        False,
    )


@weave.op()
def mitigation_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Mitigation Agent")
    incident = get_incident(incident_id)
    approved = bool(incident.get("human_approved", False))
    recommendation, requires_approval = _recommendation(incident)
    changes = {
        "recommended_action": recommendation,
        "status": "mitigating" if approved else "awaiting_approval",
    }
    update_incident(incident_id, changes)
    message = (
        "Mitigation approved; recorded local action."
        if approved
        else (
            "Mitigation recommended and paused for human approval."
            if requires_approval
            else "Mitigation guidance recorded."
        )
    )
    finish_agent(
        incident_id,
        "Mitigation Agent",
        message,
        {"requires_human_approval": requires_approval, "approved": approved, **changes},
    )
    return changes
