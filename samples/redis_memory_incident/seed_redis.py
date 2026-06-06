#!/usr/bin/env python3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.priority import update_priority
from backend.redis_client import get_redis
from backend.state import create_incident
from backend.streams import ALERTS, DEPLOYS, LOGS, METRICS, add_stream_event, ensure_consumer_groups
from backend.vector_memory import seed_runbooks

INCIDENT_ID = "inc-redis-memory-001"
KAFKA_RUNBOOKS = Path(__file__).resolve().parents[1] / "kafka_lag_incident" / "runbooks"


def main() -> None:
    client = get_redis()
    for stream in (ALERTS, METRICS, LOGS, DEPLOYS, "opsroom:timeline", "opsroom:actions"):
        client.delete(stream)
    client.delete(f"incident:{INCIDENT_ID}", "opsroom:incident_priority")

    now = datetime.now(UTC)
    start = now - timedelta(minutes=8)
    deploy_time = start - timedelta(minutes=12)
    create_incident(INCIDENT_ID, "SEV2", "session-cache", start.isoformat())
    update_priority(INCIDENT_ID, "SEV2", 28, start.isoformat(), 0)

    add_stream_event(
        ALERTS,
        {
            "incident_id": INCIDENT_ID,
            "severity": "SEV2",
            "service": "session-cache",
            "title": "Redis used memory above safe threshold",
            "value": 92,
            "timestamp": start.isoformat(),
        },
    )
    add_stream_event(
        DEPLOYS,
        {
            "incident_id": INCIDENT_ID,
            "service": "session-cache",
            "version": "v5",
            "commit": "c4a91e0",
            "actor": "deploy-bot",
            "timestamp": deploy_time.isoformat(),
        },
    )

    for index, (memory_pct, evictions, latency, errors) in enumerate(
        [(62, 0, 45, 0.002), (78, 120, 110, 0.04), (88, 890, 280, 0.11), (92, 2400, 540, 0.22)]
    ):
        timestamp = (start + timedelta(minutes=index * 2)).isoformat()
        for metric, value in (
            ("redis_used_memory_pct", memory_pct),
            ("redis_evicted_keys_per_sec", evictions),
            ("api_latency_ms", latency),
            ("error_rate", errors),
        ):
            add_stream_event(
                METRICS,
                {
                    "incident_id": INCIDENT_ID,
                    "service": "session-cache",
                    "metric": metric,
                    "value": value,
                    "timestamp": timestamp,
                },
            )

    for index in range(5):
        add_stream_event(
            LOGS,
            {
                "incident_id": INCIDENT_ID,
                "service": "session-cache",
                "level": "ERROR",
                "message": (
                    f"Redis command timeout: OOM command not allowed when used memory > maxmemory; "
                    f"evicted_keys={400 + index * 80}; keyspace=session:v2"
                ),
                "timestamp": (start + timedelta(seconds=30 * index)).isoformat(),
            },
        )

    seeded = seed_runbooks(str(KAFKA_RUNBOOKS))
    ensure_consumer_groups(client)
    print(f"Seeded {INCIDENT_ID} (Redis memory pressure) and {seeded} runbooks.")


if __name__ == "__main__":
    main()
