"""Build incident evidence and hypotheses from live Redis-backed findings."""

from __future__ import annotations

from typing import Any


def evidence_lines(incident: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    service = str(incident.get("service", "unknown"))

    for finding in incident.get("metrics_findings", []):
        metric = finding.get("metric", "metric")
        baseline = finding.get("baseline")
        latest = finding.get("latest")
        if baseline is not None and latest is not None:
            lines.append(f"{metric} moved from {baseline} to {latest} on {service}")

    for finding in incident.get("log_findings", []):
        pattern = finding.get("pattern", "error")
        count = finding.get("count", 0)
        sample = (finding.get("evidence") or [""])[0]
        lines.append(f"{count}x {pattern}: {sample[:140]}")

    for deploy in incident.get("deploy_findings", []):
        lines.append(
            f"{deploy.get('service')} {deploy.get('version')} deployed "
            f"{deploy.get('minutes_before_incident')} min before incident (commit {deploy.get('commit')})"
        )

    for match in incident.get("runbook_matches", [])[:2]:
        lines.append(f"Similar runbook: {match.get('title')} (match {match.get('score', 0):.0%})")

    return lines[:12]


def _metric(incident: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((item for item in incident.get("metrics_findings", []) if item.get("metric") == name), None)


def _log_count(incident: dict[str, Any], pattern: str) -> int:
    return next(
        (int(item.get("count", 0)) for item in incident.get("log_findings", []) if item.get("pattern") == pattern),
        0,
    )


def build_hypotheses(incident: dict[str, Any]) -> tuple[str, float, list[dict[str, Any]]]:
    lines = evidence_lines(incident)
    service = str(incident.get("service", "unknown"))
    lag = _metric(incident, "kafka_consumer_lag")
    memory = _metric(incident, "redis_used_memory_pct")
    evictions = _metric(incident, "redis_evicted_keys_per_sec")
    schema_logs = _log_count(incident, "schema_deserialization_error")
    deep_scan = _log_count(incident, "deep_scan_schema_fingerprint")
    memory_logs = _log_count(incident, "redis_memory_pressure")
    deploys = incident.get("deploy_findings", [])

    candidates: list[dict[str, Any]] = []

    if lag and schema_logs:
        conf = 0.55 + min(0.25, schema_logs * 0.03) + (0.15 if deploys else 0) + (0.04 if deep_scan else 0)
        deploy_ref = deploys[0] if deploys else {}
        title = (
            f"Bad {deploy_ref.get('service', service)} {deploy_ref.get('version', '')} deploy broke message compatibility"
            if deploys
            else f"{service} cannot process incoming messages (schema/deserialization failures)"
        )
        candidates.append(
            {
                "rank": 0,
                "title": title.strip(),
                "confidence": round(min(conf, 0.97), 2),
                "evidence": [line for line in lines if any(k in line.lower() for k in ("lag", "deserial", "schema", "deploy"))][:4]
                or lines[:3],
            }
        )

    if memory or memory_logs or evictions:
        conf = 0.5 + (0.2 if memory and float(memory.get("latest", 0)) >= 85 else 0.1)
        conf += min(0.15, _log_count(incident, "redis_memory_pressure") * 0.04)
        if evictions and float(evictions.get("latest", 0)) > 0:
            conf += 0.12
        candidates.append(
            {
                "rank": 0,
                "title": f"Redis memory pressure on {service} causing evictions and elevated latency",
                "confidence": round(min(conf, 0.95), 2),
                "evidence": [line for line in lines if any(k in line.lower() for k in ("redis", "evict", "memory", "oom"))][:4]
                or lines[:3],
            }
        )

    if _log_count(incident, "downstream_timeout"):
        candidates.append(
            {
                "rank": 0,
                "title": f"Downstream timeouts are slowing {service}",
                "confidence": 0.35,
                "evidence": [line for line in lines if "timeout" in line.lower()][:3] or lines[:2],
            }
        )

    if not candidates:
        candidates.append(
            {
                "rank": 0,
                "title": f"Insufficient telemetry to isolate root cause for {service}",
                "confidence": 0.25,
                "evidence": lines[:3] or ["No correlated metrics, logs, or deploys yet"],
            }
        )

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    for index, item in enumerate(candidates[:3], start=1):
        item["rank"] = index

    top = candidates[0]
    root_cause = (
        f"{top['title']}. Key signals: {'; '.join(top['evidence'][:2])}"
        if top.get("evidence")
        else top["title"]
    )
    return root_cause, float(top["confidence"]), candidates[:3]
