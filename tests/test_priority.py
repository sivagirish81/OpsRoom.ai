from datetime import UTC, datetime, timedelta

from backend.priority import calculate_priority_score, update_priority


def test_calculate_priority_score_sev1_with_confidence():
    start = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    score = calculate_priority_score("SEV1", 35, start, 0.9)
    assert score >= 100 + 35 + 10 + 18


def test_calculate_priority_score_lower_severity():
    start = datetime.now(UTC).isoformat()
    sev1 = calculate_priority_score("SEV1", 10, start, 0.0)
    sev3 = calculate_priority_score("SEV3", 10, start, 0.0)
    assert sev1 > sev3


def test_update_priority_writes_sorted_set(redis_client):
    incident_id = "test-incident-priority"
    start = datetime.now(UTC).isoformat()
    score = update_priority(incident_id, "SEV1", 20, start, 0.5)
    stored = redis_client.zscore("opsroom:incident_priority", incident_id)
    assert stored == score
    redis_client.zrem("opsroom:incident_priority", incident_id)
