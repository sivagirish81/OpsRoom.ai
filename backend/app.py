import asyncio
from contextlib import asynccontextmanager
from typing import Any

import weave
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.copilotkit_endpoint import opsroom_chat_agent
from backend.graph import run_incident_workflow
from backend.incident_demo import inject_deep_log_scan
from backend.observability import initialize_weave, weave_ui_url
from backend.redis_client import redis_healthcheck
from backend.state import get_incident, list_incidents, update_incident
from backend.streams import LOGS, TIMELINE, add_stream_event, append_timeline, recent_events
from backend.worker import consume_incident_events


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_weave()
    stop = asyncio.Event()
    worker = asyncio.create_task(consume_incident_events(stop))
    yield
    stop.set()
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)


app = FastAPI(
    title="OpsRoom.ai API",
    description="Redis-backed multi-agent incident response war room",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_langgraph_fastapi_endpoint(app, opsroom_chat_agent, path="/agui")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "redis": redis_healthcheck(),
        "weave": weave_ui_url(),
    }


@app.get("/api/incidents")
def incidents() -> list[dict[str, Any]]:
    return list_incidents()


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str) -> dict[str, Any]:
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/api/incidents/{incident_id}/timeline")
def incident_timeline(
    incident_id: str,
    count: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    return recent_events(TIMELINE, incident_id=incident_id, count=count)


@app.post("/api/incidents/{incident_id}/analyze")
def analyze(incident_id: str) -> dict[str, Any]:
    if not get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return run_incident_workflow(incident_id, "Run a full incident analysis")


@weave.op()
def record_approval(incident_id: str, approved: bool, actor: str = "human") -> dict[str, Any]:
    incident = get_incident(incident_id)
    if not incident:
        raise ValueError("Incident not found")
    if approved:
        changes = {"human_approved": True, "status": "mitigated", "active_agent": "Complete"}
        event_type = "rollback_approved"
        message = "Human approved rollback. Local mitigation action recorded; no infrastructure command ran."
    else:
        changes = {"human_approved": False, "status": "investigating"}
        event_type = "rollback_rejected"
        message = "Human rejected rollback. Incident returned to investigation."
    update_incident(incident_id, changes)
    add_stream_event(
        "opsroom:actions",
        {
            "incident_id": incident_id,
            "action": "rollback checkout-consumer v2",
            "approved": approved,
            "actor": actor,
            "execution_mode": "record_only",
        },
    )
    append_timeline(incident_id, actor, event_type, message, changes)
    return get_incident(incident_id)


@app.post("/api/incidents/{incident_id}/approval")
def approval(incident_id: str, approved: bool) -> dict[str, Any]:
    try:
        return record_approval(incident_id, approved)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/incidents/{incident_id}/deeper-log-analysis")
def deeper_log_analysis(incident_id: str) -> dict[str, Any]:
    if not get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        return inject_deep_log_scan(incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/incidents/{incident_id}/explain-hypothesis")
def explain_hypothesis(incident_id: str) -> dict[str, Any]:
    if not get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    append_timeline(
        incident_id,
        "human",
        "analysis_requested",
        "Human asked why the top hypothesis is likely.",
    )
    return run_incident_workflow(incident_id, "Explain why the top hypothesis is likely")

