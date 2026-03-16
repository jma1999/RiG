from __future__ import annotations
from ..models import SynthesizedAnswer
from ..llm.structured import call_structured

SYNTHESIS_SYSTEM = """
You answer building knowledge questions using only the provided retrieval evidence.

Rules:
- Do not invent data.
- Prefer concise direct answers.
- Mention uncertainty only if the available evidence is genuinely insufficient.
- If SQL and SPARQL both succeed but conflict, prefer:
  - SQL for telemetry-backed questions, metric availability, counts, rankings, latest readings, and aggregates
  - SPARQL for canonical identity or graph-only semantic membership
- Do not mention failed retrieval attempts if one successful modality already provides sufficient evidence to answer the question.
- If the result is tabular, summarize the key answer in prose.
"""

def synthesis_node(state):
    question = state["question"]
    router = state.get("router")
    plan = state.get("plan")
    sql_result = state.get("sql_result")
    sparql_result = state.get("sparql_result")
    errors = state.get("errors", [])

    sql_ok = bool(sql_result and getattr(sql_result, "ok", False))
    sparql_ok = bool(sparql_result and getattr(sparql_result, "ok", False))

    sql_rows = getattr(sql_result, "row_count", 0) if sql_result else 0
    sparql_rows = getattr(sparql_result, "row_count", 0) if sparql_result else 0

    if (not sql_ok and not sparql_ok) or (sql_rows == 0 and sparql_rows == 0 and errors):
        return {
            "final_answer": "Retrieval failed before a safe answer could be produced.",
            "evidence": {
                "errors": errors,
                "sql_rows": sql_rows,
                "sparql_rows": sparql_rows,
            },
        }

    user_prompt = f"""
Question:
{question}

Router:
{router.model_dump_json(indent=2) if router else "null"}

Plan:
{plan.model_dump_json(indent=2) if plan else "null"}

SQL Result:
{sql_result.model_dump_json(indent=2) if sql_result else "null"}

SPARQL Result:
{sparql_result.model_dump_json(indent=2) if sparql_result else "null"}
"""

    obj = call_structured(
        system_prompt=SYNTHESIS_SYSTEM,
        user_prompt=user_prompt,
        schema=SynthesizedAnswer.model_json_schema(),
        schema_name="synthesized_answer",
    )
    parsed = SynthesizedAnswer.model_validate(obj)

    return {
        "final_answer": parsed.answer_markdown,
        "evidence": {
            "summary": parsed.evidence_summary,
            "sql_rows": sql_rows,
            "sparql_rows": sparql_rows,
        },
    }