from datetime import UTC, datetime

import weave

from backend.redis_client import get_redis

SEVERITY_WEIGHTS = {"SEV1": 100.0, "SEV2": 70.0, "SEV3": 40.0, "SEV4": 10.0}


@weave.op()
def calculate_priority_score(
    severity: str,
    customer_impact: float,
    start_time: str,
    confidence: float,
    now: datetime | None = None,
) -> float:
    current = now or datetime.now(UTC)
    started = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    duration_minutes = max(0.0, (current - started).total_seconds() / 60)
    duration_score = min(duration_minutes, 60.0)
    confidence_boost = max(0.0, min(confidence, 1.0)) * 20.0
    return round(
        SEVERITY_WEIGHTS.get(severity.upper(), 0.0)
        + max(0.0, customer_impact)
        + duration_score
        + confidence_boost,
        2,
    )


@weave.op()
def update_priority(
    incident_id: str,
    severity: str,
    customer_impact: float,
    start_time: str,
    confidence: float,
) -> float:
    score = calculate_priority_score(severity, customer_impact, start_time, confidence)
    get_redis().zadd("opsroom:incident_priority", {incident_id: score})
    return score


@weave.op()
def highest_priority_incident() -> str | None:
    rows = get_redis().zrevrange("opsroom:incident_priority", 0, 0)
    return rows[0] if rows else None

