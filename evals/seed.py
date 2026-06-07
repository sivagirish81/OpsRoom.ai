"""Seed Redis with the incident scenario required by an eval case."""

from __future__ import annotations

from collections.abc import Callable

INCIDENT_SEEDERS: dict[str, Callable[[], None]] = {}


def _register_seeders() -> None:
    if INCIDENT_SEEDERS:
        return
    from samples.kafka_lag_incident.seed_redis import main as seed_kafka
    from samples.redis_memory_incident.seed_redis import main as seed_redis

    INCIDENT_SEEDERS["inc-kafka-lag-001"] = seed_kafka
    INCIDENT_SEEDERS["inc-redis-memory-001"] = seed_redis


def seed_incident(incident_id: str) -> None:
    _register_seeders()
    seeder = INCIDENT_SEEDERS.get(incident_id)
    if seeder is None:
        raise ValueError(f"No Redis seeder registered for incident {incident_id}")
    seeder()
