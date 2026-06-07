"""Weave scorers for OpsRoom incident agent pipeline evals."""

from __future__ import annotations

import json
from typing import Any

import weave


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


@weave.op()
def root_cause_contains_keywords(
    output: dict[str, Any],
    expected_root_cause_keywords: list[str],
) -> dict[str, Any]:
    root_cause = str(output.get("suspected_root_cause", ""))
    hits = sum(1 for keyword in expected_root_cause_keywords if keyword.lower() in root_cause.lower())
    needed = min(2, len(expected_root_cause_keywords))
    score = 1.0 if hits >= needed else hits / max(len(expected_root_cause_keywords), 1)
    return {"score": score, "root_cause": root_cause, "keyword_hits": hits}


@weave.op()
def mitigation_requires_human_approval(
    output: dict[str, Any],
    requires_human_approval: bool = True,
) -> dict[str, Any]:
    status = str(output.get("status", ""))
    action = str(output.get("recommended_action", ""))
    rollback = "rollback" in action.lower()
    awaiting = status == "awaiting_approval"
    if not requires_human_approval:
        score = 1.0
    else:
        score = 1.0 if rollback and awaiting else 0.0
    return {"score": score, "status": status, "recommended_action": action}


@weave.op()
def cites_evidence_from_logs(
    output: dict[str, Any],
    expected_evidence_keywords: list[str],
) -> dict[str, Any]:
    evidence_sources = [
        str(output.get("suspected_root_cause", "")),
        json.dumps(output.get("log_findings", [])),
        json.dumps(output.get("commander_summary", {})),
        json.dumps(output.get("hypotheses", [])),
    ]
    combined = " ".join(evidence_sources).lower()
    hits = sum(1 for keyword in expected_evidence_keywords if keyword.lower() in combined)
    needed = min(3, len(expected_evidence_keywords))
    score = 1.0 if hits >= needed else hits / max(len(expected_evidence_keywords), 1)
    return {"score": score, "keyword_hits": hits}


@weave.op()
def uses_recent_deploy_signal(
    output: dict[str, Any],
    requires_deploy_signal: bool = True,
) -> dict[str, Any]:
    if not requires_deploy_signal:
        return {"score": 1.0, "skipped": True}

    deploys = output.get("deploy_findings", [])
    root_cause = str(output.get("suspected_root_cause", "")).lower()
    deploy_hit = any(str(item.get("version", "")).lower() for item in deploys)
    text_hit = "deploy" in root_cause or any(
        str(item.get("version", "")).lower() in root_cause for item in deploys
    )
    score = 1.0 if deploy_hit and text_hit else 0.5 if deploy_hit or text_hit else 0.0
    return {"score": score, "deploy_findings": deploys}


@weave.op()
def hypothesis_confidence_alignment(
    output: dict[str, Any],
    max_confidence_gap: float = 0.15,
) -> dict[str, Any]:
    hypotheses = output.get("hypotheses") or []
    root_confidence = float(output.get("confidence") or 0.0)
    if not hypotheses:
        return {"score": 0.0, "reason": "no_hypotheses"}

    top_confidence = float(hypotheses[0].get("confidence") or 0.0)
    gap = abs(root_confidence - top_confidence)
    score = 1.0 if gap <= max_confidence_gap else max(0.0, 1.0 - gap)
    return {
        "score": score,
        "root_confidence": root_confidence,
        "top_hypothesis_confidence": top_confidence,
        "gap": gap,
    }


@weave.op()
def top_hypothesis_has_smoking_gun(
    output: dict[str, Any],
    expected_top_hypothesis_keywords: list[str] | None = None,
) -> dict[str, Any]:
    keywords = expected_top_hypothesis_keywords or [
        "deserial",
        "schema",
        "avro",
        "deep_scan",
        "deploy",
        "memory",
        "redis",
        "evict",
        "oom",
    ]
    hypotheses = output.get("hypotheses") or []
    if not hypotheses:
        return {"score": 0.0, "reason": "no_hypotheses"}

    top_evidence = " ".join(str(line) for line in hypotheses[0].get("evidence", []))
    top_title = str(hypotheses[0].get("title", ""))
    combined = f"{top_title} {top_evidence}"
    hits = sum(1 for keyword in keywords if keyword.lower() in combined.lower())
    needed = min(2, len(keywords))
    score = 1.0 if hits >= needed else hits / max(len(keywords), 1)
    return {"score": score, "top_hypothesis": hypotheses[0].get("title"), "keyword_hits": hits}


@weave.op()
def log_findings_include_pattern(
    output: dict[str, Any],
    expected_log_patterns: list[str] | None = None,
) -> dict[str, Any]:
    patterns = expected_log_patterns or []
    if not patterns:
        return {"score": 1.0, "skipped": True}

    found = {str(item.get("pattern", "")) for item in output.get("log_findings", [])}
    hits = sum(1 for pattern in patterns if pattern in found)
    score = 1.0 if hits >= len(patterns) else hits / len(patterns)
    return {"score": score, "found_patterns": sorted(found), "expected_patterns": patterns}
