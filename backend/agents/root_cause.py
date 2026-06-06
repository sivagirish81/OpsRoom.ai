import json

import weave

from backend.agents.common import finish_agent, start_agent
from backend.agents.evidence_builder import build_hypotheses, evidence_lines
from backend.llm import complete_json
from backend.priority import update_priority
from backend.state import IncidentGraphState, get_incident, update_incident


@weave.op()
def root_cause_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Root Cause Agent")
    incident = get_incident(incident_id)
    derived_root, derived_confidence, derived_hypotheses = build_hypotheses(incident)
    result = complete_json(
        "You are an incident root cause analyst. Use ONLY the supplied evidence. "
        "Return JSON with suspected_root_cause (one concise sentence) and confidence (0-1). "
        "Do not invent services or deploys not present in the evidence.",
        json.dumps(
            {
                "service": incident.get("service"),
                "severity": incident.get("severity"),
                "evidence_lines": evidence_lines(incident),
                "metrics": incident.get("metrics_findings", []),
                "logs": incident.get("log_findings", []),
                "deploys": incident.get("deploy_findings", []),
                "runbooks": incident.get("runbook_matches", []),
                "derived_hypotheses": derived_hypotheses,
            },
            default=str,
        ),
        {"suspected_root_cause": derived_root, "confidence": derived_confidence},
    )
    changes = {
        "suspected_root_cause": result.get("suspected_root_cause", derived_root),
        "confidence": float(result.get("confidence", derived_confidence)),
        "hypotheses": derived_hypotheses,
    }
    update_incident(incident_id, changes)
    refreshed = get_incident(incident_id)
    update_priority(
        incident_id,
        str(refreshed["severity"]),
        float(refreshed.get("customer_impact", 25)),
        str(refreshed["start_time"]),
        float(changes["confidence"]),
    )
    finish_agent(
        incident_id,
        "Root Cause Agent",
        str(changes["suspected_root_cause"]),
        changes,
    )
    return changes
