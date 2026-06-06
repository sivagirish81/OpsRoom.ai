import json
from datetime import UTC, datetime
from typing import Any

import redis
import weave

from backend.redis_client import get_redis

ALERTS = "opsroom:alerts"
METRICS = "opsroom:metrics"
LOGS = "opsroom:logs"
DEPLOYS = "opsroom:deploys"
TIMELINE = "opsroom:timeline"
STREAMS = (ALERTS, METRICS, LOGS, DEPLOYS)
GROUP = "opsroom-agents"


def _serialized(fields: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in fields.items():
        if isinstance(value, (dict, list, bool)):
            result[key] = json.dumps(value)
        else:
            result[key] = str(value)
    result.setdefault("timestamp", datetime.now(UTC).isoformat())
    return result


def _decoded(fields: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in fields.items():
        try:
            result[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            result[key] = value
    return result


@weave.op()
def add_stream_event(stream: str, fields: dict[str, Any]) -> str:
    return str(get_redis().xadd(stream, _serialized(fields), maxlen=10_000, approximate=True))


@weave.op()
def append_timeline(
    incident_id: str,
    agent: str,
    event_type: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> str:
    return add_stream_event(
        TIMELINE,
        {
            "incident_id": incident_id,
            "agent": agent,
            "event_type": event_type,
            "message": message,
            "data": data or {},
        },
    )


@weave.op()
def recent_events(
    stream: str,
    incident_id: str | None = None,
    count: int = 200,
) -> list[dict[str, Any]]:
    rows = get_redis().xrevrange(stream, count=count)
    events = [{"id": row_id, **_decoded(fields)} for row_id, fields in reversed(rows)]
    if incident_id:
        events = [
            event
            for event in events
            if event.get("incident_id") in (None, "", incident_id)
        ]
    return events


def ensure_consumer_groups(client: redis.Redis | None = None) -> None:
    client = client or get_redis()
    for stream in STREAMS:
        try:
            client.xgroup_create(stream, GROUP, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise


@weave.op()
def read_group_events(consumer: str, block_ms: int = 1000) -> list[dict[str, Any]]:
    client = get_redis()
    ensure_consumer_groups(client)
    response = client.xreadgroup(
        GROUP,
        consumer,
        {stream: ">" for stream in STREAMS},
        count=100,
        block=block_ms,
    )
    events: list[dict[str, Any]] = []
    for stream, rows in response:
        for row_id, fields in rows:
            events.append({"stream": stream, "id": row_id, **_decoded(fields)})
            client.xack(stream, GROUP, row_id)
    return events

