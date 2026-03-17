from __future__ import annotations

from ..models import DerivedReasoningOutput
from ..llm.structured import call_structured

DERIVED_REASONING_SYSTEM = """
You perform grounded facility-management interpretation using only retrieved evidence.

Rules:
- Do not invent values.
- Use the provided retrieval evidence only.
- Apply the comfort heuristic exactly as follows unless the prompt says otherwise:

Temperature comfort heuristic:
- below 68°F -> too cold
- 68°F to 75°F inclusive -> comfortable
- above 75°F -> too hot

If there is no usable temperature value, say that comfort cannot be assessed.

Return valid JSON with:
- judgment
- rationale
- applied_rule
"""

def derived_reasoning_node(state):
    question = state["question"]
    sql_result = state.get("sql_result")
    sparql_result = state.get("sparql_result")

    user_prompt = f"""
Question:
{question}

SQL Result:
{sql_result.model_dump_json(indent=2) if sql_result else "null"}

SPARQL Result:
{sparql_result.model_dump_json(indent=2) if sparql_result else "null"}
"""

    obj = call_structured(
        system_prompt=DERIVED_REASONING_SYSTEM,
        user_prompt=user_prompt,
        schema=DerivedReasoningOutput.model_json_schema(),
        schema_name="derived_reasoning_output",
    )

    return {
        "derived_reasoning": DerivedReasoningOutput.model_validate(obj)
    }