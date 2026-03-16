from __future__ import annotations

import pathlib
import sys
from typing import Any, Dict, List, Optional

# Make case_graphrag importable
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_CASE_SRC = _REPO_ROOT / "case_graphrag" / "src"
if str(_CASE_SRC) not in sys.path:
    sys.path.insert(0, str(_CASE_SRC))

from case_graphrag.graph.workflow import graph  # noqa: E402


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x)


def _thinking_from_state(state: Dict[str, Any]) -> List[Dict[str, str]]:
    steps: List[Dict[str, str]] = []

    router = state.get("router")
    if router:
        steps.append({
            "step": "router",
            "title": "Routed question",
            "content": (
                f"intent={getattr(router, 'intent', 'unknown')}, "
                f"answer_type={getattr(router, 'answer_type', 'unknown')}, "
                f"confidence={getattr(router, 'confidence', 'unknown')}"
            ),
        })

    plan = state.get("plan")
    if plan:
        entities = getattr(plan, "entities", None)
        entity_bits = []
        if entities:
            if getattr(entities, "space_label", None):
                entity_bits.append(f"space={entities.space_label}")
            if getattr(entities, "sensor_label", None):
                entity_bits.append(f"sensor={entities.sensor_label}")
            if getattr(entities, "device_id", None):
                entity_bits.append(f"device_id={entities.device_id}")
            metrics = getattr(entities, "metric_names", None) or []
            if metrics:
                entity_bits.append(f"metrics={', '.join(metrics)}")

        steps.append({
            "step": "planner",
            "title": "Built retrieval plan",
            "content": (
                f"intent={getattr(plan, 'intent', 'unknown')}; "
                f"output_style={getattr(plan, 'output_style', 'unknown')}"
                + (f"; entities: {', '.join(entity_bits)}" if entity_bits else "")
            ),
        })

    sparql_query = state.get("sparql_query")
    if sparql_query and getattr(sparql_query, "query_text", None):
        steps.append({
            "step": "sparql",
            "title": "Generated SPARQL query",
            "content": sparql_query.query_text,
        })

    sparql_validation = state.get("sparql_validation")
    if sparql_validation:
        steps.append({
            "step": "sparql_validation",
            "title": "Validated SPARQL",
            "content": _safe_str(sparql_validation),
        })

    sparql_result = state.get("sparql_result")
    if sparql_result:
        steps.append({
            "step": "sparql_results",
            "title": "Executed SPARQL",
            "content": (
                f"ok={getattr(sparql_result, 'ok', None)}, "
                f"rows={getattr(sparql_result, 'row_count', 0)}, "
                f"columns={getattr(sparql_result, 'columns', [])}"
            ),
        })

    sql_query = state.get("sql_query")
    if sql_query and getattr(sql_query, "query_text", None):
        steps.append({
            "step": "sql",
            "title": "Generated SQL query",
            "content": sql_query.query_text,
        })

    sql_validation = state.get("sql_validation")
    if sql_validation:
        steps.append({
            "step": "sql_validation",
            "title": "Validated SQL",
            "content": _safe_str(sql_validation),
        })

    sql_result = state.get("sql_result")
    if sql_result:
        steps.append({
            "step": "sql_results",
            "title": "Executed SQL",
            "content": (
                f"ok={getattr(sql_result, 'ok', None)}, "
                f"rows={getattr(sql_result, 'row_count', 0)}, "
                f"columns={getattr(sql_result, 'columns', [])}"
            ),
        })

    if state.get("sql_repair_count"):
        steps.append({
            "step": "sql_repair",
            "title": "SQL repair applied",
            "content": f"repair_count={state.get('sql_repair_count')}",
        })

    if state.get("sparql_repair_count"):
        steps.append({
            "step": "sparql_repair",
            "title": "SPARQL repair applied",
            "content": f"repair_count={state.get('sparql_repair_count')}",
        })

    errors = state.get("errors") or []
    if errors:
        steps.append({
            "step": "errors",
            "title": "Pipeline notes",
            "content": " | ".join(_safe_str(e) for e in errors),
        })

    return steps


def _evidence_from_state(state: Dict[str, Any]) -> Dict[str, Any]:
    sparql_result = state.get("sparql_result")
    sql_result = state.get("sql_result")

    return {
        "sparql_query": getattr(state.get("sparql_query"), "query_text", "") if state.get("sparql_query") else "",
        "sql_query": getattr(state.get("sql_query"), "query_text", "") if state.get("sql_query") else "",
        "seed_count": 0,
        "node_count": 0,
        "edge_count": 0,
        "seeds": [],
        "sql_row_count": getattr(sql_result, "row_count", 0) if sql_result else 0,
        "sparql_row_count": getattr(sparql_result, "row_count", 0) if sparql_result else 0,
        "sql_columns": getattr(sql_result, "columns", []) if sql_result else [],
        "sparql_columns": getattr(sparql_result, "columns", []) if sparql_result else [],
    }


def _tool_from_state(question: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    q = (question or "").lower()

    plan = state.get("plan")
    entities = getattr(plan, "entities", None) if plan else None

    wants_graph = any(w in q for w in ("show graph", "visualize", "knowledge graph", "graph of"))
    wants_telemetry = any(w in q for w in ("telemetry", "reading", "readings", "time series", "sensor data", "live data"))
    asks_sensor_set = ("which sensors" in q) or ("what sensors" in q) or ("list sensors" in q)

    if wants_graph:
        return {"action": "search", "query": question}

    # If the answer is telemetry-driven and tied to a space/sensor/device, switch to telemetry panel
    if entities:
        if getattr(entities, "device_id", None):
            return {"action": "telemetry", "asset_id": entities.device_id, "query": question}

        if getattr(entities, "sensor_label", None):
            return {"action": "telemetry", "asset_id": entities.sensor_label, "query": question}

        # For space-level telemetry questions like:
        # "Which sensors in Office1 have humidity?"
        if getattr(entities, "space_label", None) and (
            wants_telemetry
            or asks_sensor_set
            or (getattr(plan, "intent", None) == "timeseries_only")
        ):
            return {
                "action": "telemetry",
                "space_label": entities.space_label,
                "metrics": getattr(entities, "metric_names", []) or [],
                "query": question,
            }

    if any(w in q for w in ("search", "find", "where", "list")):
        return {"action": "search", "query": question}

    return None


def run_case_graphrag(question: str) -> Dict[str, Any]:
    state = graph.invoke({"question": question})

    final_answer = state.get("final_answer") or "I could not produce an answer from the current retrieval pipeline."
    thinking = _thinking_from_state(state)
    evidence = _evidence_from_state(state)
    tool = _tool_from_state(question, state)

    return {
        "reply": final_answer,
        "thinking": thinking,
        "tool": tool,
        "evidence": evidence,
        "sparql_query": evidence.get("sparql_query", ""),
        "sql_query": evidence.get("sql_query", ""),
        "debug": {
            "router": state.get("router").model_dump() if state.get("router") else None,
            "plan": state.get("plan").model_dump() if state.get("plan") else None,
            "errors": state.get("errors", []),
            "sql_repair_count": state.get("sql_repair_count", 0),
            "sparql_repair_count": state.get("sparql_repair_count", 0),
        },
    }