from typing import Any

import json

import weave
from copilotkit import LangGraphAGUIAgent
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from backend.copilot_routing import generative_view_tag, keyword_route_panels
from backend.graph import run_incident_workflow
from backend.incident_demo import inject_deep_log_scan
from backend.llm import complete_json
from backend.priority import highest_priority_incident
from backend.state import get_incident


def _last_user_message(messages: list[Any]) -> str:
    for message in reversed(messages):
        role = getattr(message, "type", None) or getattr(message, "role", None)
        if role in {"human", "user"}:
            return str(getattr(message, "content", message))
    return ""


def _definitive_block(incident: dict[str, Any], *, include_action: bool = True) -> str:
    root = str(incident.get("suspected_root_cause") or "Root cause is still under investigation.")
    confidence = float(incident.get("confidence") or 0) * 100
    lines = [
        f"**Verdict:** {root}",
        f"**Confidence:** {confidence:.0f}%",
    ]
    if include_action:
        action = str(incident.get("recommended_action") or "").strip()
        if action:
            lines.append(f"**Recommended action:** {action}")
    return "\n\n".join(lines)


def _has_schema_proof(incident: dict[str, Any]) -> bool:
    for finding in incident.get("log_findings") or []:
        pattern = str(finding.get("pattern", ""))
        if pattern in {"deep_scan_schema_fingerprint", "schema_deserialization_error"}:
            return True
    return False


def _ensure_schema_proof(incident_id: str, incident: dict[str, Any]) -> dict[str, Any]:
    if _has_schema_proof(incident):
        return incident
    inject_deep_log_scan(incident_id)
    return get_incident(incident_id) or incident


def _smoking_gun_answer(incident_id: str, incident: dict[str, Any]) -> str:
    incident = _ensure_schema_proof(incident_id, incident)
    return (
        f"{_definitive_block(incident)}\n\n"
        "**Proof:** AvroTypeException — writer schema `checkout.v3` is incompatible with "
        "reader `checkout.v2` on checkout-consumer.\n\n"
        "[GENERATIVE:smokinggun]"
    )


def _generative_views_keyword(question: str) -> tuple[bool, bool, bool, list[str], str]:
    routed = keyword_route_panels(question)
    return (
        routed["show_metrics"],
        routed["show_hypotheses"],
        routed["show_smoking_gun"],
        routed["metric_filter"],
        "",
    )


def _resolve_generative_views(
    question: str, incident: dict[str, Any]
) -> tuple[bool, bool, bool, list[str], str]:
    keyword = keyword_route_panels(question)
    fallback = {
        "show_metrics": keyword["show_metrics"],
        "show_hypotheses": keyword["show_hypotheses"],
        "show_smoking_gun": keyword["show_smoking_gun"],
        "metric_filter": keyword["metric_filter"],
        "definitive_answer": _definitive_block(incident, include_action=False),
    }
    routed = complete_json(
        "You are the OpsRoom copilot. Return JSON only with: "
        "show_metrics, show_hypotheses, show_smoking_gun (booleans), "
        "metric_filter (optional string[] — use exact names: kafka_consumer_lag, checkout_latency_ms, error_rate, throughput), "
        "definitive_answer (2-4 sentences: state facts directly — never use likely/may/might/could). "
        "RULES: Enable ONLY panels the user explicitly asked for. "
        "At most ONE panel unless they said 'dashboard' or named multiple views. "
        "Metrics only for lag/latency/throughput/chart requests. "
        "Hypotheses only for ranking/confidence/candidate requests. "
        "Smoking gun only for proof/schema/Avro/deserial requests. "
        "Root-cause questions get definitive_answer text and NO panels unless they also asked to show something visual.",
        json.dumps(
            {
                "question": question,
                "service": incident.get("service"),
                "status": incident.get("status"),
                "suspected_root_cause": incident.get("suspected_root_cause"),
                "confidence": incident.get("confidence"),
            },
            default=str,
        ),
        fallback,
    )
    show_metrics = bool(routed.get("show_metrics", fallback["show_metrics"]))
    show_hypotheses = bool(routed.get("show_hypotheses", fallback["show_hypotheses"]))
    show_smoking_gun = bool(routed.get("show_smoking_gun", fallback["show_smoking_gun"]))
    enabled_count = sum((show_metrics, show_hypotheses, show_smoking_gun))
    if enabled_count > 1 and "dashboard" not in question.lower():
        if show_smoking_gun:
            show_metrics = show_hypotheses = False
        elif show_hypotheses:
            show_metrics = show_smoking_gun = False
        else:
            show_hypotheses = show_smoking_gun = False
    return (
        show_metrics,
        show_hypotheses,
        show_smoking_gun,
        list(routed.get("metric_filter") or fallback["metric_filter"]),
        str(routed.get("definitive_answer") or fallback["definitive_answer"]),
    )


def _view_tag(
    show_metrics: bool, show_hypotheses: bool, show_smoking_gun: bool, metric_filter: list[str]
) -> str:
    return generative_view_tag(show_metrics, show_hypotheses, show_smoking_gun, metric_filter)


@weave.op()
def answer_incident_question(state: MessagesState) -> dict[str, list[AIMessage]]:
    question = _last_user_message(state.get("messages", []))
    incident_id = highest_priority_incident()
    if not incident_id:
        return {
            "messages": [
                AIMessage(content="No active incident is available. Run the sample replay first.")
            ]
        }
    lowered = question.lower()
    if any(term in lowered for term in ("scan log", "deep scan", "deeper log", "smoking gun scan")):
        inject_deep_log_scan(incident_id)
        incident = get_incident(incident_id)
        answer = (
            f"{_definitive_block(incident)}\n\n"
            "**Proof:** Deep scan confirmed writer schema `checkout.v3` is incompatible with "
            "reader `checkout.v2` on checkout-consumer.\n\n"
            "[GENERATIVE:smokinggun]"
        )
        return {"messages": [AIMessage(content=answer)]}
    if any(term in lowered for term in ("deeper", "analyze", "investigate", "refresh")):
        incident = run_incident_workflow(incident_id, question)
    else:
        incident = get_incident(incident_id)

    show_metrics, show_hypotheses, show_smoking_gun, metric_filter, definitive = _resolve_generative_views(
        question, incident
    )

    if show_smoking_gun and not show_metrics and not show_hypotheses:
        return {"messages": [AIMessage(content=_smoking_gun_answer(incident_id, incident))]}

    view_tag = _view_tag(show_metrics, show_hypotheses, show_smoking_gun, metric_filter)

    if view_tag:
        if show_smoking_gun and ("likely" in definitive.lower() or "may " in definitive.lower()):
            definitive = _definitive_block(incident, include_action=False)
        answer = f"{definitive}\n\n[GENERATIVE:{view_tag}]"
        return {"messages": [AIMessage(content=answer)]}

    summary = incident.get("commander_summary", {})
    evidence = summary.get("evidence", [])[:3]
    evidence_lines = "\n".join(f"- {line}" for line in evidence) if evidence else "- See agent findings in Redis"
    answer = (
        f"{_definitive_block(incident)}\n\n"
        f"**Key evidence:**\n{evidence_lines}\n\n"
        "Ask for **metrics**, **hypothesis ranking**, or **schema proof** if you want a focused visual."
    )
    return {"messages": [AIMessage(content=answer)]}


chat_builder = StateGraph(MessagesState)
chat_builder.add_node("answer", answer_incident_question)
chat_builder.add_edge(START, "answer")
chat_builder.add_edge("answer", END)
copilot_graph = chat_builder.compile(checkpointer=MemorySaver())

opsroom_chat_agent = LangGraphAGUIAgent(
    name="opsroom",
    description="OpsRoom incident commander with live Redis-backed incident context.",
    graph=copilot_graph,
)
