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

INCIDENT_ID = "inc-kafka-lag-001"
ROOT = Path(__file__).resolve().parent


def emit(stream: str, delay: float, **event: object) -> None:
    event["incident_id"] = INCIDENT_ID
    event["timestamp"] = datetime.now(UTC).isoformat()
    row_id = add_stream_event(stream, event)
    print(f"{stream:<22} {row_id}  {event.get('message') or event.get('metric') or event.get('title')}")
    time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the OpsRoom.ai Kafka lag incident.")
    parser.add_argument("--delay", type=float, default=1.2, help="Seconds between event batches.")
    parser.add_argument("--reset", action="store_true", help="Clear the previous demo incident.")
    args = parser.parse_args()

    client = get_redis()
    if args.reset:
        for stream in (ALERTS, METRICS, LOGS, DEPLOYS, "opsroom:timeline", "opsroom:actions"):
            client.delete(stream)
        client.delete(f"incident:{INCIDENT_ID}", "opsroom:incident_priority")

    start = datetime.now(UTC)
    create_incident(INCIDENT_ID, "SEV1", "checkout-consumer", start.isoformat())
    update_priority(INCIDENT_ID, "SEV1", 35, start.isoformat(), 0)
    seed_runbooks(str(ROOT / "runbooks"))

    emit(
        DEPLOYS,
        args.delay,
        service="checkout-consumer",
        version="v2",
        commit="8e3a7f2",
        actor="deploy-bot",
    )
    emit(
        ALERTS,
        args.delay,
        severity="SEV1",
        service="checkout-consumer",
        title="Kafka consumer lag above critical threshold",
        value=1_000_000,
    )

    for lag, latency, error_rate, throughput in (
        (0, 180, 0.001, 2400),
        (150_000, 440, 0.09, 1750),
        (510_000, 910, 0.23, 850),
        (1_000_000, 1680, 0.41, 160),
    ):
        for metric, value, unit in (
            ("kafka_consumer_lag", lag, "messages"),
            ("checkout_latency_ms", latency, "ms"),
            ("error_rate", error_rate, "ratio"),
            ("throughput", throughput, "messages_per_second"),
        ):
            emit(
                METRICS,
                0.05,
                service="checkout-consumer",
                metric=metric,
                value=value,
                unit=unit,
            )
        time.sleep(args.delay)

    for partition in range(6):
        emit(
            LOGS,
            args.delay / 2,
            service="checkout-consumer",
            level="ERROR",
            message=(
                "Kafka record deserialization failed: AvroTypeException; "
                "writer schema checkout.v3 incompatible with reader checkout.v2; "
                f"partition={partition % 3}"
            ),
        )
    print("Replay complete. The backend stream consumer is coordinating the agent workflow.")


if __name__ == "__main__":
    main()

