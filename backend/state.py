import json
from datetime import UTC, datetime
from typing import Any, TypedDict

import weave

from backend.redis_client import get_redis


class IncidentGraphState(TypedDict, total=False):
    incident_id: str
    user_message: str
    status: str
    severity: str
    service: str
    start_time: str
    active_agent: str
    metrics_findings: list[dict[str, Any]]
    log_findings: list[dict[str, Any]]
    deploy_findings: list[dict[str, Any]]
    runbook_matches: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    suspected_root_cause: str
    confidence: float
    recommended_action: str
    human_approved: bool
    commander_summary: dict[str, Any]
    messages: list[Any]


JSON_FIELDS = {
    "metrics_findings",
    "log_findings",
    "deploy_findings",
    "runbook_matches",
    "hypotheses",
    "commander_summary",
}


def incident_key(incident_id: str) -> str:
    return f"incident:{incident_id}"


def _encode(value: Any) -> str:
    if isinstance(value, (dict, list, bool)):
        return json.dumps(value)
    return str(value)


def _decode(field: str, value: str) -> Any:
    if field in JSON_FIELDS or field == "human_approved":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if field == "confidence":
        return float(value)
    return value


@weave.op()
def create_incident(
    incident_id: str,
    severity: str,
    service: str,
    start_time: str | None = None,
) -> dict[str, Any]:
    initial = {
        "id": incident_id,
        "status": "investigating",
        "severity": severity,
        "service": service,
        "start_time": start_time or datetime.now(UTC).isoformat(),
        "suspected_root_cause": "Analysis in progress",
        "confidence": 0.0,
        "recommended_action": "Gather metrics, logs, and deployment evidence",
        "human_approved": False,
        "active_agent": "Intake Agent",
    }
    get_redis().hset(incident_key(incident_id), mapping={k: _encode(v) for k, v in initial.items()})
    return initial


@weave.op()
def update_incident(incident_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if changes:
        get_redis().hset(
            incident_key(incident_id),
            mapping={key: _encode(value) for key, value in changes.items()},
        )
    return get_incident(incident_id)


@weave.op()
def get_incident(incident_id: str) -> dict[str, Any]:
    raw = get_redis().hgetall(incident_key(incident_id))
    return {field: _decode(field, value) for field, value in raw.items()}


@weave.op()
def list_incidents() -> list[dict[str, Any]]:
    client = get_redis()
    incident_ids = client.zrevrange("opsroom:incident_priority", 0, -1, withscores=True)
    result = []
    for incident_id, score in incident_ids:
        incident = get_incident(incident_id)
        if incident:
            incident["priority_score"] = round(float(score), 2)
            result.append(incident)
    return result

