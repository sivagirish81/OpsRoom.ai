"""Unit tests for deterministic Copilot routing used in Weave evals."""

from backend.copilot_routing import keyword_route_panels


def test_hypothesis_question_routes_to_hypotheses_panel():
    routed = keyword_route_panels("Show hypothesis ranking")
    assert routed["panels"] == ["hypotheses"]
    assert routed["panel_count"] == 1


def test_smoking_gun_routes_to_single_panel():
    routed = keyword_route_panels("What's the smoking gun?")
    assert routed["panels"] == ["smokinggun"]


def test_metrics_question_includes_metric_filter():
    routed = keyword_route_panels("Show live metrics for consumer lag and error rate")
    assert routed["panels"] == ["metrics"]
    assert "kafka_consumer_lag" in routed["metric_filter"]
    assert "error_rate" in routed["metric_filter"]


def test_dashboard_allows_multiple_panels():
    routed = keyword_route_panels("Open a custom dashboard with metrics and hypotheses")
    assert "metrics" in routed["panels"]
    assert "hypotheses" in routed["panels"]
