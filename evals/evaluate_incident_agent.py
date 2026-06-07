#!/usr/bin/env python3
"""Run OpsRoom agent evals in Weave Evaluations (Traces + Evals tab)."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import weave

from backend.copilot_routing import keyword_route_panels
from backend.graph import run_incident_workflow
from backend.observability import initialize_weave, weave_ui_url
from evals.copilot_scorers import (
    copilot_metric_filter_accuracy,
    copilot_panel_routing_accuracy,
    copilot_single_panel_rule,
)
from evals.scorers import (
    cites_evidence_from_logs,
    hypothesis_confidence_alignment,
    log_findings_include_pattern,
    mitigation_requires_human_approval,
    root_cause_contains_keywords,
    top_hypothesis_has_smoking_gun,
    uses_recent_deploy_signal,
)
from evals.seed import seed_incident

INCIDENT_DATASET_PATH = Path(__file__).resolve().parent / "incident_eval_dataset.json"
COPILOT_DATASET_PATH = Path(__file__).resolve().parent / "copilot_eval_dataset.json"

INCIDENT_SCORERS = [
    root_cause_contains_keywords,
    mitigation_requires_human_approval,
    cites_evidence_from_logs,
    uses_recent_deploy_signal,
    hypothesis_confidence_alignment,
    top_hypothesis_has_smoking_gun,
    log_findings_include_pattern,
]

COPILOT_SCORERS = [
    copilot_panel_routing_accuracy,
    copilot_single_panel_rule,
    copilot_metric_filter_accuracy,
]

_SEED_EACH_CASE = False


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def _average_score(summary: dict[str, Any]) -> float | None:
    scorer_means: list[float] = []
    skip_keys = {"output", "model_latency"}
    for name, payload in summary.items():
        if name in skip_keys or not isinstance(payload, dict):
            continue
        score_block = payload.get("score")
        if isinstance(score_block, dict) and isinstance(score_block.get("mean"), (int, float)):
            scorer_means.append(float(score_block["mean"]))
        elif isinstance(score_block, (int, float)):
            scorer_means.append(float(score_block))
    if not scorer_means:
        return None
    return sum(scorer_means) / len(scorer_means)


def _print_summary(title: str, summary: dict[str, Any]) -> None:
    print(f"\n{title}\n" + "-" * len(title))
    print(json.dumps(summary, indent=2, default=str))
    average = _average_score(summary)
    if average is not None:
        print(f"\nAverage score: {average:.2f}")


@weave.op()
def predict_incident_case(incident_id: str, prompt: str = "") -> dict[str, Any]:
    if _SEED_EACH_CASE:
        seed_incident(incident_id)
    return run_incident_workflow(incident_id, prompt)


@weave.op()
def predict_copilot_routing(question: str) -> dict[str, Any]:
    return keyword_route_panels(question)


async def run_incident_evaluation(
    dataset: list[dict[str, Any]],
    *,
    evaluation_name: str,
) -> dict[str, Any]:
    evaluation = weave.Evaluation(
        dataset=dataset,
        scorers=INCIDENT_SCORERS,
        evaluation_name=evaluation_name,
    )
    return await evaluation.evaluate(predict_incident_case)


async def run_copilot_evaluation(
    dataset: list[dict[str, Any]],
    *,
    evaluation_name: str,
) -> dict[str, Any]:
    evaluation = weave.Evaluation(
        dataset=dataset,
        scorers=COPILOT_SCORERS,
        evaluation_name=evaluation_name,
    )
    return await evaluation.evaluate(predict_copilot_routing)


async def run_all_evaluations(
    *,
    incident_dataset_path: Path,
    copilot_dataset_path: Path,
    run_incident: bool,
    run_copilot: bool,
    seed_before_each_case: bool,
    evaluation_name: str,
) -> dict[str, dict[str, Any]]:
    global _SEED_EACH_CASE
    _SEED_EACH_CASE = seed_before_each_case

    results: dict[str, dict[str, Any]] = {}
    if run_incident:
        incident_dataset = _load_dataset(incident_dataset_path)
        results["incident"] = await run_incident_evaluation(
            incident_dataset,
            evaluation_name=f"{evaluation_name}-incident-agents",
        )
    if run_copilot:
        copilot_dataset = _load_dataset(copilot_dataset_path)
        results["copilot"] = await run_copilot_evaluation(
            copilot_dataset,
            evaluation_name=f"{evaluation_name}-copilot-routing",
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OpsRoom agents with Weave Evaluations.")
    parser.add_argument("--seed", action="store_true", help="Seed Redis before each incident case.")
    parser.add_argument("--incident-dataset", default=str(INCIDENT_DATASET_PATH))
    parser.add_argument("--copilot-dataset", default=str(COPILOT_DATASET_PATH))
    parser.add_argument(
        "--suite",
        choices=("all", "incident", "copilot"),
        default="all",
        help="Which evaluation suite to run.",
    )
    parser.add_argument(
        "--evaluation-name",
        default="opsroom-eval",
        help="Prefix for Weave evaluation runs (shows in Evals tab).",
    )
    args = parser.parse_args()

    initialize_weave()
    weave_url = weave_ui_url()

    print("\nOpsRoom.ai — Weave Evaluations\n" + "=" * 32)
    if weave_url:
        print(f"Weave UI: {weave_url}")
        print("Open Evals tab after this run to compare scorer columns across cases.")
    else:
        print("Weave cloud unavailable — set WANDB_API_KEY in .env for Evals dashboard.")

    results = asyncio.run(
        run_all_evaluations(
            incident_dataset_path=Path(args.incident_dataset),
            copilot_dataset_path=Path(args.copilot_dataset),
            run_incident=args.suite in {"all", "incident"},
            run_copilot=args.suite in {"all", "copilot"},
            seed_before_each_case=args.seed,
            evaluation_name=args.evaluation_name,
        )
    )

    if "incident" in results:
        _print_summary("Incident agent evaluation", results["incident"])
    if "copilot" in results:
        _print_summary("Copilot routing evaluation", results["copilot"])

    if weave_url:
        print(f"\nInspect results in Weave:\n  {weave_url}")


if __name__ == "__main__":
    main()
