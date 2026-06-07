"""Deterministic Copilot generative-panel routing (keyword-based fallback)."""

from __future__ import annotations


def keyword_route_panels(question: str) -> dict:
    """Return which generative panels a user question should open."""
    lowered = question.lower()
    show_metrics = any(
        term in lowered for term in ("metric", "lag", "latency", "throughput", "performance", "chart")
    )
    show_hypotheses = any(
        term in lowered
        for term in ("hypothesis", "hypotheses", "confidence", "rank", "candidate", "ranking")
    )
    show_smoking_gun = any(
        term in lowered
        for term in (
            "smoking gun",
            "smokinggun",
            "avro",
            "schema",
            "proof",
            "deserial",
            "fingerprint",
            "scan log",
            "deep scan",
        )
    )
    metric_filter: list[str] = []
    if "consumer lag" in lowered or "kafka lag" in lowered:
        metric_filter.append("kafka_consumer_lag")
    if "error rate" in lowered:
        metric_filter.append("error_rate")
    for name in (
        "kafka_consumer_lag",
        "checkout_latency_ms",
        "error_rate",
        "throughput",
        "redis_used_memory_pct",
    ):
        if name.replace("_", " ") in lowered or name in lowered:
            metric_filter.append(name)

    wants_dashboard = "dashboard" in lowered or "custom view" in lowered
    if wants_dashboard:
        if "metric" in lowered and "only" in lowered:
            show_metrics, show_hypotheses, show_smoking_gun = True, False, False
        elif "hypothesis" in lowered and "only" in lowered:
            show_metrics, show_hypotheses, show_smoking_gun = False, True, False
        elif "smoking gun" in lowered and "only" in lowered:
            show_metrics, show_hypotheses, show_smoking_gun = False, False, True
        else:
            show_metrics = show_metrics or True
            show_hypotheses = show_hypotheses or True
    elif sum((show_metrics, show_hypotheses, show_smoking_gun)) > 1:
        if show_smoking_gun:
            show_metrics = show_hypotheses = False
        elif show_hypotheses:
            show_metrics = show_smoking_gun = False
        else:
            show_hypotheses = show_smoking_gun = False

    panels = panel_names(show_metrics, show_hypotheses, show_smoking_gun)
    return {
        "show_metrics": show_metrics,
        "show_hypotheses": show_hypotheses,
        "show_smoking_gun": show_smoking_gun,
        "panels": panels,
        "metric_filter": normalize_metric_filter(metric_filter),
        "panel_count": len(panels),
    }


def panel_names(show_metrics: bool, show_hypotheses: bool, show_smoking_gun: bool) -> list[str]:
    panels: list[str] = []
    if show_metrics:
        panels.append("metrics")
    if show_hypotheses:
        panels.append("hypotheses")
    if show_smoking_gun:
        panels.append("smokinggun")
    return panels


def normalize_metric_filter(metric_filter: list[str]) -> list[str]:
    aliases = {
        "consumer_lag": "kafka_consumer_lag",
        "consumer lag": "kafka_consumer_lag",
        "kafka_lag": "kafka_consumer_lag",
        "kafka lag": "kafka_consumer_lag",
        "lag": "kafka_consumer_lag",
        "error rate": "error_rate",
        "latency": "checkout_latency_ms",
        "checkout latency": "checkout_latency_ms",
        "checkout_latency": "checkout_latency_ms",
    }
    normalized: list[str] = []
    for name in metric_filter:
        key = name.strip().lower()
        normalized.append(aliases.get(key, name.strip()))
    return normalized


def generative_view_tag(
    show_metrics: bool, show_hypotheses: bool, show_smoking_gun: bool, metric_filter: list[str]
) -> str:
    parts = panel_names(show_metrics, show_hypotheses, show_smoking_gun)
    if not parts:
        return ""
    tag = ",".join(parts)
    if metric_filter:
        tag += f"|metrics={','.join(normalize_metric_filter(metric_filter))}"
    return tag
