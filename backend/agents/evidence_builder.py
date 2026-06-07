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


def _metric_latest(incident: dict[str, Any], name: str) -> float | None:
    metric = _metric(incident, name)
    if not metric or metric.get("latest") is None:
        return None
    return float(metric["latest"])


def _log_count(incident: dict[str, Any], pattern: str) -> int:
    return next(
        (int(item.get("count", 0)) for item in incident.get("log_findings", []) if item.get("pattern") == pattern),
        0,
    )


def _is_smoking_gun(line: str) -> bool:
    lowered = line.lower()
    return any(
        keyword in lowered
        for keyword in (
            "deep_scan",
            "deserial",
            "avrotypeexception",
            "schema fingerprint",
            "schema_deserialization",
        )
    )


def _filter_evidence(lines: list[str], *keywords: str) -> list[str]:
    filtered = [line for line in lines if any(keyword in line.lower() for keyword in keywords)]
    return filtered[:4] if filtered else lines[:3]


def _prioritize_deploy_evidence(lines: list[str]) -> list[str]:
    """Put schema/deep-scan smoking-gun lines first on the winning deploy hypothesis."""
    smoking = [line for line in lines if _is_smoking_gun(line)]
    deploy = [line for line in lines if line not in smoking and "deploy" in line.lower()]
    metrics = [
        line
        for line in lines
        if line not in smoking
        and line not in deploy
        and any(keyword in line.lower() for keyword in ("lag", "latency", "error_rate", "throughput"))
    ]
    ordered = smoking + deploy + metrics + [line for line in lines if line not in smoking + deploy + metrics]
    return ordered[:4] if ordered else lines[:3]


def _filter_evidence_without_smoking_gun(lines: list[str], *keywords: str) -> list[str]:
    filtered = [
        line
        for line in lines
        if not _is_smoking_gun(line) and any(keyword in line.lower() for keyword in keywords)
    ]
    return filtered[:4] if filtered else [line for line in lines if not _is_smoking_gun(line)][:3]


def _add_candidate(candidates: list[dict[str, Any]], title: str, confidence: float, evidence: list[str]) -> None:
    candidates.append(
        {
            "rank": 0,
            "title": title.strip(),
            "confidence": round(min(max(confidence, 0.05), 0.97), 2),
            "evidence": evidence,
        }
    )


def _build_kafka_lag_hypotheses(
    incident: dict[str, Any],
    lines: list[str],
    service: str,
    lag: dict[str, Any],
    deploys: list[dict[str, Any]],
    schema_logs: int,
    deep_scan: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    lag_latest = float(lag.get("latest", 0))
    error_rate = _metric_latest(incident, "error_rate")
    throughput = _metric(incident, "throughput")
    latency = _metric_latest(incident, "checkout_latency_ms")
    deploy_ref = deploys[0] if deploys else {}

    if lag_latest <= 0:
        return candidates

    # #1 candidate: recent deploy broke message compatibility
    if deploys or schema_logs:
        conf = 0.45
        if schema_logs:
            conf += min(0.30, schema_logs * 0.04)
        if deploys:
            conf += 0.14
            minutes = deploy_ref.get("minutes_before_incident")
            if minutes is not None and int(minutes) <= 15:
                conf += 0.05
        if deep_scan:
            conf += 0.05
        if lag_latest >= 500_000:
            conf += 0.04
        title = (
            f"Bad {deploy_ref.get('service', service)} {deploy_ref.get('version', '')} deploy broke message compatibility"
            if deploys
            else f"{service} cannot process incoming messages (schema/deserialization failures)"
        )
        _add_candidate(
            candidates,
            title,
            conf,
            _prioritize_deploy_evidence(lines),
        )

    # #2 candidate: poison / incompatible records blocking the consumer
    if lag_latest >= 50_000:
        conf = 0.30
        if schema_logs:
            conf += 0.14
        if error_rate is not None and error_rate >= 0.05:
            conf += min(0.12, error_rate * 0.4)
        if lag_latest >= 500_000:
            conf += 0.04
        _add_candidate(
            candidates,
            f"Poison or incompatible checkout records are blocking {service} from committing offsets",
            conf,
            _filter_evidence_without_smoking_gun(lines, "error", "lag", "error_rate"),
        )

    # #3 candidate: consumer capacity / ingest rate mismatch
    if throughput and lag_latest >= 50_000:
        baseline = float(throughput.get("baseline", 0))
        latest = float(throughput.get("latest", 0))
        if baseline > 0 and latest < baseline * 0.75:
            drop_ratio = (baseline - latest) / baseline
            conf = 0.26 + min(0.14, drop_ratio * 0.25)
            if latency is not None and latency >= 500:
                conf += 0.04
            _add_candidate(
                candidates,
                f"Consumer capacity saturated — {service} cannot keep up with ingest rate",
                conf,
                _filter_evidence(lines, "throughput", "lag", "latency", "checkout_latency"),
            )

    # #4 candidate: infra / rebalance distractor
    conf = 0.20
    if lag_latest >= 100_000:
        conf += 0.04
    if latency is not None and latency >= 500:
        conf += 0.05
    if deploys and not schema_logs:
        conf += 0.03
    _add_candidate(
        candidates,
        f"Partition rebalance or broker instability is slowing {service}",
        conf,
        _filter_evidence(lines, "lag", "latency", "throughput"),
    )

    return candidates


def build_hypotheses(incident: dict[str, Any]) -> tuple[str, float, list[dict[str, Any]]]:
    lines = evidence_lines(incident)
    service = str(incident.get("service", "unknown"))
    lag = _metric(incident, "kafka_consumer_lag")
    memory = _metric(incident, "redis_used_memory_pct")
    evictions = _metric(incident, "redis_evicted_keys_per_sec")
    schema_logs = _log_count(incident, "schema_deserialization_error")
    deep_scan = _log_count(incident, "deep_scan_schema_fingerprint")
    deploys = incident.get("deploy_findings", [])

    candidates: list[dict[str, Any]] = []

    if lag:
        candidates.extend(
            _build_kafka_lag_hypotheses(incident, lines, service, lag, deploys, schema_logs, deep_scan)
        )

    if memory or _log_count(incident, "redis_memory_pressure") or evictions:
        conf = 0.5 + (0.2 if memory and float(memory.get("latest", 0)) >= 85 else 0.1)
        conf += min(0.15, _log_count(incident, "redis_memory_pressure") * 0.04)
        if evictions and float(evictions.get("latest", 0)) > 0:
            conf += 0.12
        _add_candidate(
            candidates,
            f"Redis memory pressure on {service} causing evictions and elevated latency",
            conf,
            _filter_evidence(lines, "redis", "evict", "memory", "oom"),
        )

    if _log_count(incident, "downstream_timeout"):
        _add_candidate(
            candidates,
            f"Downstream timeouts are slowing {service}",
            0.35,
            _filter_evidence(lines, "timeout"),
        )

    if not candidates:
        _add_candidate(
            candidates,
            f"Insufficient telemetry to isolate root cause for {service}",
            0.25,
            lines[:3] or ["No correlated metrics, logs, or deploys yet"],
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
