from __future__ import annotations

from ..models import EntityResolutionOutput
from ..llm.structured import call_structured

ENTITY_RESOLVER_SYSTEM = """
You resolve vague building-related user references into known schema entities.

Known space labels in this project:
- Kitchen5
- Meeting Room3
- Office1
- Reception6
- Work Area & Storage2
- Work Area & Storage4

Known metric names:
- relative_humidity
- temperature

Rules:
- Resolve vague terms like "the office" to the most likely known space label.
- Resolve "humidity" to "relative_humidity".
- Keep exact labels unchanged.
- If unsure, set resolved_value to null and explain briefly in notes.
- Return only valid JSON.
"""

def entity_resolver_node(state):
    question = state["question"]

    user_prompt = f"""
Question:
{question}
"""

    obj = call_structured(
        system_prompt=ENTITY_RESOLVER_SYSTEM,
        user_prompt=user_prompt,
        schema=EntityResolutionOutput.model_json_schema(),
        schema_name="entity_resolution_output",
    )

    return {
        "entity_resolution": EntityResolutionOutput.model_validate(obj)
    }