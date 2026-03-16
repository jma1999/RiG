from langgraph.graph import StateGraph, END
from ..state import GraphState
from ..nodes.router import router_node
from ..nodes.planner import planner_node
from ..nodes.sql_generator import sql_generator_node
from ..nodes.sql_validator import sql_validator_node
from ..nodes.sql_executor import sql_executor_node
from ..nodes.sparql_generator import sparql_generator_node
from ..nodes.sparql_validator import sparql_validator_node
from ..nodes.sparql_executor import sparql_executor_node
from ..nodes.synthesis import synthesis_node
from ..nodes.fallback import fallback_node
from ..nodes.sql_repair import sql_repair_node
from ..nodes.sparql_repair import sparql_repair_node

def route_after_planner(state: GraphState) -> str:
    intent = state["plan"].intent
    if intent == "graph_only":
        return "sparql_generator"
    if intent == "timeseries_only":
        return "sql_generator"
    if intent == "graph_plus_timeseries":
        return "sparql_generator"
    return "fallback"


def route_after_sparql_exec(state: GraphState) -> str:
    intent = state["plan"].intent
    if intent == "graph_plus_timeseries":
        return "sql_generator"
    return "synthesis"


def route_after_validation(kind: str):
    def _inner(state: GraphState) -> str:
        key = f"{kind}_validation"
        return f"{kind}_executor" if state[key]["ok"] else "fallback"
    return _inner

def route_after_sql_validation(state: GraphState) -> str:
    validation = state["sql_validation"]
    if validation["ok"]:
        return "sql_executor"
    if state.get("sql_repair_count", 0) < 1:
        return "sql_repair"
    return "fallback"


def route_after_sparql_validation(state: GraphState) -> str:
    validation = state["sparql_validation"]
    if validation["ok"]:
        return "sparql_executor"
    if state.get("sparql_repair_count", 0) < 1:
        return "sparql_repair"
    return "fallback"


def route_after_sql_execution(state: GraphState) -> str:
    result = state.get("sql_result")
    if result and result.ok and result.row_count > 0:
        return "synthesis"
    if state.get("sql_repair_count", 0) < 1:
        return "sql_repair"
    return "fallback"


def route_after_sparql_execution(state: GraphState) -> str:
    result = state.get("sparql_result")
    intent = state["plan"].intent
    entities = state["plan"].entities

    if result and result.ok and result.row_count > 0:
        if intent == "graph_plus_timeseries":
            return "sql_generator"
        return "synthesis"
    
    # Graceful degradation:
    # if the plan is graph_plus_timeseries but SQL can still answer from space-level telemetry joins, 
    # continue to SQL even if SPARQL came back empty.
    if intent == "graph_plus_timeseries":
        if entities.space_label and not entities.sensor_label and not entities.device_id:
            return "sql_generator"
            
    if state.get("sparql_repair_count", 0) < 1:
        return "sparql_repair"
    return "fallback"

builder = StateGraph(GraphState)

builder.add_node("router", router_node)
builder.add_node("planner", planner_node)
builder.add_node("sparql_generator", sparql_generator_node)
builder.add_node("sparql_validator", sparql_validator_node)
builder.add_node("sparql_executor", sparql_executor_node)
builder.add_node("sql_generator", sql_generator_node)
builder.add_node("sql_validator", sql_validator_node)
builder.add_node("sql_executor", sql_executor_node)
builder.add_node("synthesis", synthesis_node)
builder.add_node("fallback", fallback_node)
builder.add_node("sql_repair", sql_repair_node)
builder.add_node("sparql_repair", sparql_repair_node)

builder.set_entry_point("router")
builder.add_edge("router", "planner")

builder.add_conditional_edges("planner", route_after_planner, {
    "sparql_generator": "sparql_generator",
    "sql_generator": "sql_generator",
    "fallback": "fallback",
})

builder.add_edge("sparql_generator", "sparql_validator")
builder.add_conditional_edges("sparql_validator", route_after_validation("sparql"), {
    "sparql_executor": "sparql_executor",
    "fallback": "fallback",
})

builder.add_conditional_edges("sparql_executor", route_after_sparql_exec, {
    "sql_generator": "sql_generator",
    "synthesis": "synthesis",
})

builder.add_edge("sql_generator", "sql_validator")
builder.add_conditional_edges("sql_validator", route_after_validation("sql"), {
    "sql_executor": "sql_executor",
    "fallback": "fallback",
})

builder.add_conditional_edges("sparql_validator", route_after_sparql_validation, {
    "sparql_executor": "sparql_executor",
    "sparql_repair": "sparql_repair",
    "fallback": "fallback",
})

builder.add_edge("sparql_repair", "sparql_validator")

builder.add_conditional_edges("sparql_executor", route_after_sparql_execution, {
    "sql_generator": "sql_generator",
    "synthesis": "synthesis",
    "sparql_repair": "sparql_repair",
    "fallback": "fallback",
})

builder.add_conditional_edges("sql_validator", route_after_sql_validation, {
    "sql_executor": "sql_executor",
    "sql_repair": "sql_repair",
    "fallback": "fallback",
})

builder.add_edge("sql_repair", "sql_validator")

builder.add_conditional_edges("sql_executor", route_after_sql_execution, {
    "synthesis": "synthesis",
    "sql_repair": "sql_repair",
    "fallback": "fallback",
})

builder.add_edge("sql_executor", "synthesis")
builder.add_edge("synthesis", END)
builder.add_edge("fallback", END)

graph = builder.compile()