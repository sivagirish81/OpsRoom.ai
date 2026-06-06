from backend.state import create_incident, get_incident, list_incidents, update_incident


def test_create_and_update_incident(redis_client):
    incident_id = "test-incident-state"
    redis_client.delete(f"incident:{incident_id}")
    redis_client.zrem("opsroom:incident_priority", incident_id)

    created = create_incident(incident_id, "SEV2", "payments-api")
    assert created["status"] == "investigating"
    assert created["service"] == "payments-api"

    updated = update_incident(
        incident_id,
        {
            "status": "awaiting_approval",
            "confidence": 0.82,
            "hypotheses": [{"rank": 1, "title": "Bad deploy"}],
        },
    )
    assert updated["status"] == "awaiting_approval"
    assert updated["confidence"] == 0.82
    assert updated["hypotheses"][0]["title"] == "Bad deploy"

    fetched = get_incident(incident_id)
    assert fetched["human_approved"] is False

    redis_client.delete(f"incident:{incident_id}")


def test_list_incidents_returns_priority_score(redis_client):
    incident_id = "test-incident-list"
    redis_client.delete(f"incident:{incident_id}")
    create_incident(incident_id, "SEV1", "checkout-consumer")
    from backend.priority import update_priority

    update_priority(incident_id, "SEV1", 30, get_incident(incident_id)["start_time"], 0.4)
    rows = list_incidents()
    match = next((row for row in rows if row.get("id") == incident_id), None)
    assert match is not None
    assert "priority_score" in match
    redis_client.delete(f"incident:{incident_id}")
    redis_client.zrem("opsroom:incident_priority", incident_id)
