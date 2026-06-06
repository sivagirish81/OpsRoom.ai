#!/usr/bin/env python3
import argparse
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.priority import update_priority
from backend.redis_client import get_redis
from backend.state import create_incident
from backend.streams import ALERTS, DEPLOYS, LOGS, METRICS, add_stream_event
from backend.vector_memory import seed_runbooks

INCIDENT_ID = "inc-redis-memory-001"
KAFKA_RUNBOOKS = Path(__file__).resolve().parents[1] / "kafka_lag_incident" / "runbooks"


def emit(stream: str, delay: float, **event: object) -> None:
    event["incident_id"] = INCIDENT_ID
    event["timestamp"] = datetime.now(UTC).isoformat()
    row_id = add_stream_event(stream, event)
    print(f"{stream:<22} {row_id}  {event.get('message') or event.get('metric') or event.get('title')}")
    time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the Redis memory pressure incident.")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    client = get_redis()
    if args.reset:
        for stream in (ALERTS, METRICS, LOGS, DEPLOYS, "opsroom:timeline", "opsroom:actions"):
            client.delete(stream)
        client.delete(f"incident:{INCIDENT_ID}", "opsroom:incident_priority")

    start = datetime.now(UTC)
    create_incident(INCIDENT_ID, "SEV2", "session-cache", start.isoformat())
    update_priority(INCIDENT_ID, "SEV2", 28, start.isoformat(), 0)
    seed_runbooks(str(KAFKA_RUNBOOKS))

    emit(DEPLOYS, args.delay, service="session-cache", version="v5", commit="c4a91e0", actor="deploy-bot")
    emit(
        ALERTS,
        args.delay,
        severity="SEV2",
        service="session-cache",
        title="Redis used memory above safe threshold",
        value=92,
    )

    for memory_pct, evictions, latency, errors in (
        (65, 0, 50, 0.003),
        (81, 200, 130, 0.05),
        (92, 2100, 520, 0.21),
    ):
        for metric, value in (
            ("redis_used_memory_pct", memory_pct),
            ("redis_evicted_keys_per_sec", evictions),
            ("api_latency_ms", latency),
            ("error_rate", errors),
        ):
            emit(METRICS, 0.05, service="session-cache", metric=metric, value=value)
        time.sleep(args.delay)

    for index in range(4):
        emit(
            LOGS,
            args.delay / 2,
            service="session-cache",
            level="ERROR",
            message=(
                "Redis command timeout: OOM command not allowed when used memory > maxmemory; "
                f"evicted_keys={500 + index * 100}"
            ),
        )
    print("Replay complete for Redis memory incident.")


if __name__ == "__main__":
    main()
