from __future__ import annotations

from ..models import QueryArtifact, QueryRepair
from ..llm.structured import call_structured

SPARQL_REPAIR_SYSTEM = """
You repair SPARQL SELECT queries for a controlled building knowledge system.

Allowed named graphs:
- https://example.com/case-office/g/overlay
- https://example.com/case-office/g/223p

Rules:
- Return exactly one repaired SPARQL SELECT query
- Never use INSERT, DELETE, CLEAR, LOAD, CREATE, DROP, MOVE, COPY, ADD
- Fix missing prefixes, wrong predicates, wrong graph usage, and zero-row issues if possible
- Preserve the intent of the original question
"""

def sparql_repair_node(state):
    question = state["question"]
    plan = state["plan"]
    bad_query = state["sparql_query"].query_text
    validation = state.get("sparql_validation")
    result = state.get("sparql_result")

    error_info = {
        "validation": validation,
        "execution_result": result.model_dump() if result else None,
    }

    user_prompt = f"""
Question:
{question}

Plan:
{plan.model_dump_json(indent=2)}

Original SPARQL:
{bad_query}

Failure context:
{error_info}
"""

    obj = call_structured(
        system_prompt=SPARQL_REPAIR_SYSTEM,
        user_prompt=user_prompt,
        schema=QueryRepair.model_json_schema(),
        schema_name="sparql_repair",
    )
    repaired = QueryRepair.model_validate(obj)

    return {
        "sparql_query": QueryArtifact(
            query_text=repaired.revised_query,
            dialect="sparql",
            warnings=[f"repair_reason:{repaired.reasoning}"],
        ),
        "sparql_repair_count": state.get("sparql_repair_count", 0) + 1,
    }