#!/usr/bin/env python3
"""Weave evaluation for OpsRoom incident response agents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import weave

from backend.graph import run_incident_workflow
from backend.observability import initialize_weave, weave_ui_url
from backend.state import get_incident
from samples.kafka_lag_incident.seed_redis import main as seed_redis

DATASET_PATH = Path(__file__).resolve().parent / "incident_eval_dataset.json"


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


@weave.op()
def root_cause_contains_schema_error(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    root_cause = str(output.get("suspected_root_cause", ""))
    expected_text = str(expected.get("expected_root_cause", ""))
    keywords = ["schema", "deserial", "checkout-consumer", "v2"]
    score = 1.0 if _contains_any(root_cause, keywords) else 0.0
    return {"score": score, "root_cause": root_cause, "expected": expected_text}


@weave.op()
def mitigation_requires_human_approval(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    status = str(output.get("status", ""))
    action = str(output.get("recommended_action", ""))
    requires = bool(expected.get("requires_human_approval", True))
    rollback = "rollback" in action.lower()
    awaiting = status == "awaiting_approval"
    score = 1.0 if requires and rollback and awaiting else 0.0
    return {"score": score, "status": status, "recommended_action": action}


@weave.op()
def cites_evidence_from_logs(output: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    keywords = expected.get("expected_evidence_keywords", [])
    evidence_sources = [
        str(output.get("suspected_root_cause", "")),
        json.dumps(output.get("log_findings", [])),
        json.dumps(output.get("commander_summary", {})),
        json.dumps(output.get("hypotheses", [])),
    ]
    combined = " ".join(evidence_sources).lower()
    hits = sum(1 for keyword in keywords if keyword.lower() in combined)
    score = 1.0 if hits >= min(3, len(keywords)) else hits / max(len(keywords), 1)
    return {"score": score, "keyword_hits": hits, "keywords": keywords}


@weave.op()
def uses_recent_deploy_signal(output: dict[str, Any], _: dict[str, Any]) -> dict[str, Any]:
    deploys = output.get("deploy_findings", [])
    root_cause = str(output.get("suspected_root_cause", "")).lower()
    deploy_hit = any("v2" in str(item.get("version", "")).lower() for item in deploys)
    text_hit = "deploy" in root_cause or "v2" in root_cause
    score = 1.0 if deploy_hit and text_hit else 0.5 if deploy_hit or text_hit else 0.0
    return {"score": score, "deploy_findings": deploys}


@weave.op()
def run_eval_case(case: dict[str, Any]) -> dict[str, Any]:
    incident_id = case["incident_id"]
    output = run_incident_workflow(incident_id, case.get("prompt", ""))
    return {
        "incident_id": incident_id,
        "output": output,
        "scores": {
            "root_cause_contains_schema_error": root_cause_contains_schema_error(output, case),
            "mitigation_requires_human_approval": mitigation_requires_human_approval(output, case),
            "cites_evidence_from_logs": cites_evidence_from_logs(output, case),
            "uses_recent_deploy_signal": uses_recent_deploy_signal(output, case),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OpsRoom incident agents with Weave.")
    parser.add_argument("--seed", action="store_true", help="Seed Redis before running evals.")
    parser.add_argument("--dataset", default=str(DATASET_PATH), help="Path to eval dataset JSON.")
    args = parser.parse_args()

    initialize_weave()
    if args.seed:
        seed_redis()

    dataset = json.loads(Path(args.dataset).read_text())
    results = [run_eval_case(case) for case in dataset]

    print("\nOpsRoom.ai incident agent evaluation\n" + "=" * 40)
    weave_url = weave_ui_url()
    if weave_url:
        print(f"Weave traces: {weave_url}")
    for result in results:
        print(f"\nIncident: {result['incident_id']}")
        output = result["output"]
        print(f"  Root cause: {output.get('suspected_root_cause')}")
        print(f"  Status: {output.get('status')}")
        for name, payload in result["scores"].items():
            print(f"  {name}: {payload['score']:.2f}")

    avg = sum(
        score["score"]
        for result in results
        for score in result["scores"].values()
    ) / max(len(results) * 4, 1)
    print(f"\nAverage score: {avg:.2f}")
    if weave_url:
        print(f"\nInspect eval traces in Weave:\n  {weave_url}")
    else:
        print("\nWeave cloud tracing unavailable — set WANDB_API_KEY in .env")


if __name__ == "__main__":
    main()
