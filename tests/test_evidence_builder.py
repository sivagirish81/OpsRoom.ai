from backend.agents.evidence_builder import build_hypotheses, evidence_lines


def test_evidence_lines_from_metrics_and_logs():
    incident = {
        "service": "checkout-consumer",
        "metrics_findings": [
            {"metric": "kafka_consumer_lag", "baseline": 0, "latest": 1_000_000},
        ],
        "log_findings": [
            {
                "pattern": "schema_deserialization_error",
                "count": 4,
                "evidence": ["AvroTypeException on checkout.v3"],
            }
        ],
        "deploy_findings": [
            {"service": "checkout-consumer", "version": "v2", "commit": "abc", "minutes_before_incident": 5}
        ],
    }
    lines = evidence_lines(incident)
    assert any("kafka_consumer_lag" in line for line in lines)
    assert any("schema_deserialization_error" in line for line in lines)

    root, confidence, hypotheses = build_hypotheses(incident)
    assert confidence > 0.5
    assert "schema" in root.lower() or "deploy" in root.lower() or "deserial" in root.lower()
    assert hypotheses[0]["rank"] == 1


def test_redis_memory_hypothesis():
    incident = {
        "service": "session-cache",
        "metrics_findings": [
            {"metric": "redis_used_memory_pct", "baseline": 62, "latest": 92},
            {"metric": "redis_evicted_keys_per_sec", "baseline": 0, "latest": 2400},
        ],
        "log_findings": [
            {
                "pattern": "redis_memory_pressure",
                "count": 3,
                "evidence": ["OOM command not allowed when used memory > maxmemory"],
            }
        ],
        "deploy_findings": [],
    }
    root, confidence, hypotheses = build_hypotheses(incident)
    assert "redis" in hypotheses[0]["title"].lower() or "memory" in hypotheses[0]["title"].lower()
    assert confidence >= 0.5
    assert "memory" in root.lower() or "redis" in root.lower()
