from __future__ import annotations

from ..models import QueryArtifact, QueryRepair
from ..llm.structured import call_structured

SQL_REPAIR_SYSTEM = """
You repair PostgreSQL SQL queries for a controlled building telemetry system.

Allowed tables:
- telemetry_observations
- telemetry_latest
- sensor_space_enriched_clean
- dt_sensor_map

Rules:
- Return exactly one repaired SQL SELECT or WITH query
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE
- Fix schema mismatches, wrong metric names, wrong join paths, and zero-row issues if possible
- Preserve the intent of the original question
"""

def sql_repair_node(state):
    question = state["question"]
    plan = state["plan"]
    bad_query = state["sql_query"].query_text
    validation = state.get("sql_validation")
    result = state.get("sql_result")

    error_info = {
        "validation": validation,
        "execution_result": result.model_dump() if result else None,
    }

    user_prompt = f"""
Question:
{question}

Plan:
{plan.model_dump_json(indent=2)}

Original SQL:
{bad_query}

Failure context:
{error_info}
"""

    obj = call_structured(
        system_prompt=SQL_REPAIR_SYSTEM,
        user_prompt=user_prompt,
        schema=QueryRepair.model_json_schema(),
        schema_name="sql_repair",
    )
    repaired = QueryRepair.model_validate(obj)

    return {
        "sql_query": QueryArtifact(
            query_text=repaired.revised_query,
            dialect="sql",
            warnings=[f"repair_reason:{repaired.reasoning}"],
        ),
        "sql_repair_count": state.get("sql_repair_count", 0) + 1,
    }