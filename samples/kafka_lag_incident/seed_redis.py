#!/usr/bin/env python3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.priority import update_priority
from backend.redis_client import get_redis
from backend.state import create_incident
from backend.streams import ALERTS, DEPLOYS, LOGS, METRICS, add_stream_event, ensure_consumer_groups
from backend.vector_memory import seed_runbooks

INCIDENT_ID = "inc-kafka-lag-001"
ROOT = Path(__file__).resolve().parent


def main() -> None:
    client = get_redis()
    for stream in (ALERTS, METRICS, LOGS, DEPLOYS, "opsroom:timeline", "opsroom:actions"):
        client.delete(stream)
    client.delete(f"incident:{INCIDENT_ID}", "opsroom:incident_priority")

    now = datetime.now(UTC)
    start = now - timedelta(minutes=5)
    deploy_time = start - timedelta(minutes=7)
    create_incident(INCIDENT_ID, "SEV1", "checkout-consumer", start.isoformat())
    update_priority(INCIDENT_ID, "SEV1", 35, start.isoformat(), 0)

    add_stream_event(
        ALERTS,
        {
            "incident_id": INCIDENT_ID,
            "severity": "SEV1",
            "service": "checkout-consumer",
            "title": "Kafka consumer lag above critical threshold",
            "value": 1_000_000,
            "timestamp": start.isoformat(),
        },
    )
    add_stream_event(
        DEPLOYS,
        {
            "incident_id": INCIDENT_ID,
            "service": "checkout-consumer",
            "version": "v2",
            "commit": "8e3a7f2",
            "actor": "deploy-bot",
            "timestamp": deploy_time.isoformat(),
        },
    )
    for index, (lag, latency, errors, throughput) in enumerate(
        [
            (0, 180, 0.001, 2400),
            (125_000, 420, 0.08, 1800),
            (480_000, 850, 0.21, 920),
            (1_000_000, 1650, 0.39, 180),
        ]
    ):
        timestamp = (start + timedelta(minutes=index)).isoformat()
        for metric, value, unit in (
            ("kafka_consumer_lag", lag, "messages"),
            ("checkout_latency_ms", latency, "ms"),
            ("error_rate", errors, "ratio"),
            ("throughput", throughput, "messages_per_second"),
        ):
            add_stream_event(
                METRICS,
                {
                    "incident_id": INCIDENT_ID,
                    "service": "checkout-consumer",
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                    "timestamp": timestamp,
                },
            )
    for index in range(6):
        add_stream_event(
            LOGS,
            {
                "incident_id": INCIDENT_ID,
                "service": "checkout-consumer",
                "level": "ERROR",
                "message": (
                    "Kafka record deserialization failed: AvroTypeException; "
                    "writer schema checkout.v3 incompatible with reader checkout.v2; "
                    f"partition={index % 3} offset={98120 + index}"
                ),
                "timestamp": (start + timedelta(seconds=20 * index)).isoformat(),
            },
        )

    seeded = seed_runbooks(str(ROOT / "runbooks"))
    ensure_consumer_groups(client)
    print(f"Seeded {INCIDENT_ID}, 22 stream events, and {seeded} vector runbooks.")


if __name__ == "__main__":
    main()

