from __future__ import annotations
from ..models import RetrievalPlan
from ..llm.structured import call_structured

PLANNER_SYSTEM = """
You produce retrieval plans for a building knowledge system.

Available SQL tables:
- telemetry_observations
- telemetry_latest
- sensor_space_enriched_clean
- dt_sensor_map

Available SPARQL named graphs:
- https://example.com/case-office/g/overlay
- https://example.com/case-office/g/223p

Use SQL for:
- telemetry values
- latest readings
- averages and aggregates
- metric availability
- telemetry-backed counts/rankings
- telemetry-backed room/sensor membership
- telemetry-backed coverage

Use SPARQL for:
- semantic identity resolution that cannot be answered from SQL joins alone
- canonical URI lookups
- room/sensor graph membership when telemtry evidence is not required

Use both only when graph grounding is genuinely required before SQL.

Important examples:
- "Which room has the most humidity sensors?" requires SQL over telemetry-backed humidity observations joined with room mapping.
- "Which spaces have telemetry available?" requires SQL over telemetry_observations joined with sensor_space_enriched_clean.
- "What metrics are available for Office1?" requires SQL over telemetry_observations.
- "Which sensors are located in Office1?" can use SPARQL or SQL room membership.
- "Which sensors in Office1 have humidity?" -> SQL only
- "What metrics are available for Reception6?" -> SQL only
- "Which room has the highest number of telemetry-backed sensors?" -> SQL only
- "Which canonical URI corresponds to Sensor41?" -> SPARQL only

Return only a valid JSON plan.
"""

def planner_node(state):
    question = state["question"]
    router = state["router"]

    user_prompt = f"""
Question:
{question}

Router decision:
{router.model_dump_json(indent=2)}
"""

    obj = call_structured(
        system_prompt=PLANNER_SYSTEM,
        user_prompt=user_prompt,
        schema=RetrievalPlan.model_json_schema(),
        schema_name="retrieval_plan",
    )
    return {"plan": RetrievalPlan.model_validate(obj)}