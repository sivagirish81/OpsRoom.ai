from typing import Any

from backend.state import IncidentGraphState, update_incident
from backend.streams import append_timeline


def start_agent(state: IncidentGraphState, name: str) -> str:
    incident_id = state["incident_id"]
    update_incident(incident_id, {"active_agent": name})
    append_timeline(incident_id, name, "agent_started", f"{name} started analysis.")
    return incident_id


def finish_agent(
    incident_id: str,
    name: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    append_timeline(incident_id, name, "agent_completed", message, data)

