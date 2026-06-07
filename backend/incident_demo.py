"""Shared incident demo actions used by API and Copilot."""

from __future__ import annotations

from backend.graph import run_incident_workflow
from backend.state import get_incident
from backend.streams import LOGS, add_stream_event, append_timeline


def inject_deep_log_scan(incident_id: str) -> dict:
    incident = get_incident(incident_id)
    if not incident:
        raise ValueError("Incident not found")
    service = str(incident.get("service", "checkout-consumer"))
    deep_scan_message = (
        "Deep scan: AvroTypeException schema fingerprint mismatch; "
        "writer schema checkout.v3 is incompatible with reader checkout.v2"
    )
    for partition in range(4):
        add_stream_event(
            LOGS,
            {
                "incident_id": incident_id,
                "service": service,
                "level": "ERROR",
                "message": f"{deep_scan_message}; partition={partition % 3}",
            },
        )
    append_timeline(
        incident_id,
        "human",
        "evidence_discovered",
        "Deep log scan surfaced schema fingerprint mismatch (checkout.v3 → checkout.v2).",
    )
    return run_incident_workflow(incident_id, "Perform deeper log analysis")
