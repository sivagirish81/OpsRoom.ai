from backend.agents.evidence_builder import build_hypotheses, evidence_lines


def test_evidence_lines_from_metrics_and_logs():
    incident = {
        "service": "checkout-consumer",
        "metrics_findings": [
            {"metric": "kafka_consumer_lag", "baseline": 0, "latest": 1_000_000},
            {"metric": "error_rate", "baseline": 0.001, "latest": 0.41},
            {"metric": "throughput", "baseline": 2400, "latest": 160},
            {"metric": "checkout_latency_ms", "baseline": 180, "latest": 1680},
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
    assert len(hypotheses) == 3
    assert "deploy" in hypotheses[0]["title"].lower() or "compat" in hypotheses[0]["title"].lower()


def test_kafka_competing_hypotheses_without_schema_logs():
    incident = {
        "service": "checkout-consumer",
        "metrics_findings": [
            {"metric": "kafka_consumer_lag", "baseline": 0, "latest": 510_000},
            {"metric": "error_rate", "baseline": 0.001, "latest": 0.23},
            {"metric": "throughput", "baseline": 2400, "latest": 850},
            {"metric": "checkout_latency_ms", "baseline": 180, "latest": 910},
        ],
        "log_findings": [],
        "deploy_findings": [
            {"service": "checkout-consumer", "version": "v2", "commit": "abc", "minutes_before_incident": 5}
        ],
    }
    _, confidence, hypotheses = build_hypotheses(incident)
    assert len(hypotheses) == 3
    assert confidence >= 0.55
    assert "insufficient telemetry" not in hypotheses[0]["title"].lower()
    titles = " ".join(item["title"].lower() for item in hypotheses)
    assert "deploy" in titles or "compat" in titles
    assert "poison" in titles or "incompatible" in titles
    assert hypotheses[0]["confidence"] > hypotheses[1]["confidence"] > hypotheses[2]["confidence"]


def test_smoking_gun_evidence_on_top_hypothesis():
    incident = {
        "service": "checkout-consumer",
        "metrics_findings": [
            {"metric": "kafka_consumer_lag", "baseline": 0, "latest": 1_000_000},
            {"metric": "error_rate", "baseline": 0.001, "latest": 0.41},
        ],
        "log_findings": [
            {
                "pattern": "deep_scan_schema_fingerprint",
                "count": 4,
                "evidence": [
                    "Deep scan: AvroTypeException schema fingerprint mismatch; writer schema checkout.v3 is incompatible with reader checkout.v2"
                ],
            },
            {
                "pattern": "schema_deserialization_error",
                "count": 10,
                "evidence": ["Kafka record deserialization failed: AvroTypeException"],
            },
        ],
        "deploy_findings": [
            {"service": "checkout-consumer", "version": "v2", "commit": "abc", "minutes_before_incident": 5}
        ],
    }
    _, _, hypotheses = build_hypotheses(incident)
    top_evidence = " ".join(hypotheses[0]["evidence"]).lower()
    assert "deep_scan" in top_evidence or "avrotypeexception" in top_evidence or "deserial" in top_evidence
    second_evidence = " ".join(hypotheses[1]["evidence"]).lower()
    assert "deep_scan" not in second_evidence


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
