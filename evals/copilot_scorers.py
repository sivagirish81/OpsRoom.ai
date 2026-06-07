"""Weave scorers for Copilot generative UI routing evals."""

from __future__ import annotations

from typing import Any

import weave


@weave.op()
def copilot_panel_routing_accuracy(
    output: dict[str, Any],
    expected_panels: list[str],
) -> dict[str, Any]:
    actual = list(output.get("panels") or [])
    score = 1.0 if actual == expected_panels else 0.0
    return {"score": score, "actual_panels": actual, "expected_panels": expected_panels}


@weave.op()
def copilot_single_panel_rule(
    output: dict[str, Any],
    expected_panels: list[str] | None = None,
) -> dict[str, Any]:
    actual = list(output.get("panels") or [])
    panel_count = len(actual)
    expected = list(expected_panels or [])
    if len(expected) > 1:
        score = 1.0 if panel_count > 1 else 0.0
    else:
        score = 1.0 if panel_count <= 1 else 0.0
    return {"score": score, "panel_count": panel_count, "expected_panels": expected}


@weave.op()
def copilot_metric_filter_accuracy(
    output: dict[str, Any],
    expected_metric_filter: list[str] | None = None,
) -> dict[str, Any]:
    if not expected_metric_filter:
        return {"score": 1.0, "skipped": True}

    actual = list(output.get("metric_filter") or [])
    expected = list(expected_metric_filter)
    score = 1.0 if all(metric in actual for metric in expected) else 0.0
    return {"score": score, "actual_filter": actual, "expected_filter": expected}
