from collections import Counter

import weave

from backend.agents.common import finish_agent, start_agent
from backend.state import IncidentGraphState, update_incident
from backend.streams import LOGS, recent_events

ERROR_PATTERNS = {
    "schema_deserialization_error": ("deserial", "schema", "avro", "compatib"),
    "redis_memory_pressure": ("oom", "maxmemory", "evict", "memory pressure", "used memory"),
    "downstream_timeout": ("timeout", "timed out"),
    "connection_error": ("connection refused", "connection reset"),
}


@weave.op()
def logs_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Logs Agent")
    events = recent_events(LOGS, incident_id=incident_id)
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = {}
    for event in events:
        message = str(event.get("message", ""))
        lowered = message.lower()
        for pattern, needles in ERROR_PATTERNS.items():
            if any(needle in lowered for needle in needles):
                counts[pattern] += 1
                evidence.setdefault(pattern, []).append(message)
    deep_scan = [event for event in events if "deep scan" in str(event.get("message", "")).lower()]
    findings = [
        {"pattern": pattern, "count": count, "evidence": evidence[pattern][:3]}
        for pattern, count in counts.most_common()
    ]
    if deep_scan:
        findings.insert(
            0,
            {
                "pattern": "deep_scan_schema_fingerprint",
                "count": len(deep_scan),
                "evidence": [str(event.get("message", "")) for event in deep_scan[:2]],
            },
        )
    summary = (
        f"Deep scan confirmed schema fingerprint mismatch in {len(deep_scan)} additional log lines."
        if deep_scan
        else (
            f"Detected {findings[0]['count']} recurring {findings[0]['pattern']} log events."
            if findings
            else "No recurring error pattern found."
        )
    )
    update_incident(incident_id, {"log_findings": findings})
    finish_agent(incident_id, "Logs Agent", summary, {"findings": findings})
    return {"log_findings": findings}

