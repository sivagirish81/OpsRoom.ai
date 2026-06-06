from datetime import UTC, datetime

import weave

from backend.agents.common import finish_agent, start_agent
from backend.priority import update_priority
from backend.state import IncidentGraphState, create_incident, get_incident, update_incident
from backend.streams import ALERTS, recent_events


@weave.op()
def intake_agent(state: IncidentGraphState) -> dict:
    incident_id = state["incident_id"]
    current = get_incident(incident_id)
    if not current:
        alerts = recent_events(ALERTS, incident_id=incident_id)
        alert = alerts[-1] if alerts else {}
        current = create_incident(
            incident_id,
            str(alert.get("severity", "SEV1")),
            str(alert.get("service", "checkout-consumer")),
            str(alert.get("timestamp", datetime.now(UTC).isoformat())),
        )
    start_agent(state, "Intake Agent")
    update_priority(
        incident_id,
        str(current.get("severity", "SEV1")),
        float(current.get("customer_impact", 25)),
        str(current["start_time"]),
        float(current.get("confidence", 0)),
    )
    update_incident(incident_id, {"status": "investigating"})
    finish_agent(incident_id, "Intake Agent", "Incident accepted and prioritized.")
    return current

