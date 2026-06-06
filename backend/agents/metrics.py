import weave

from backend.agents.common import finish_agent, start_agent
from backend.state import IncidentGraphState, update_incident
from backend.streams import METRICS, recent_events


@weave.op()
def metrics_agent(state: IncidentGraphState) -> dict:
    incident_id = start_agent(state, "Metrics Agent")
    events = recent_events(METRICS, incident_id=incident_id)
    metric_names = list(dict.fromkeys(str(event.get("metric")) for event in events if event.get("metric")))
    findings = []
    for metric in metric_names:
        samples = [event for event in events if event.get("metric") == metric]
        values = [float(sample["value"]) for sample in samples]
        finding = {
            "metric": metric,
            "baseline": values[0],
            "latest": values[-1],
            "peak": max(values),
            "change": values[-1] - values[0],
            "samples": len(values),
        }
        findings.append(finding)

    highlight = findings[0] if findings else None
    if highlight:
        message = (
            f"{highlight['metric']} moved from {highlight['baseline']} to {highlight['latest']} "
            f"across {highlight['samples']} samples."
        )
    else:
        message = "No metric samples are available yet."

    update_incident(incident_id, {"metrics_findings": findings})
    finish_agent(incident_id, "Metrics Agent", message, {"findings": findings})
    return {"metrics_findings": findings}
