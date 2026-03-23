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
- averages and aggregates over telemetry
- metric availability
- telemetry-backed counts/rankings
- telemetry-backed room/sensor membership
- comfort reasoning inputs
- project room counts over supported spaces

Use SPARQL for:
- semantic identity resolution that cannot be answered from SQL joins alone
- canonical URI lookups
- room/sensor graph membership when telemetry evidence is not required
- graph-wide counts of spaces/rooms when telemetry is not required

Use both only when graph grounding is genuinely required before SQL.

Metric normalization rules:
- Normalize "humidity" to "relative_humidity"
- Normalize "temperature" to "temperature"

Reasoning rules:
- If the question asks about comfort, too hot, or too cold, retrieve the relevant temperature first, then send the result to a derived reasoning step.
- For project room counts in this demo system, count supported project spaces from the operational room mapping rather than arbitrary labeled graph nodes.
- If a vague space phrase appears, use the resolved label from entity resolution.

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
    entity_resolution = state.get("entity_resolution")

    user_prompt = f"""
Question:
{question}

Router decision:
{router.model_dump_json(indent=2)}

Entity resolution:
{entity_resolution.model_dump_json(indent=2) if entity_resolution else "null"}
"""

    obj = call_structured(
        system_prompt=PLANNER_SYSTEM,
        user_prompt=user_prompt,
        schema=RetrievalPlan.model_json_schema(),
        schema_name="retrieval_plan",
    )

    plan = RetrievalPlan.model_validate(obj)

    # Force resolved space labels into the plan if available
    if entity_resolution:
        for res in entity_resolution.resolutions:
            if res.entity_type == "space" and res.resolved_value:
                plan.entities.space_label = res.resolved_value
            if res.entity_type == "metric" and res.resolved_value:
                if res.resolved_value not in plan.entities.metric_names:
                    plan.entities.metric_names.append(res.resolved_value)

    return {"plan": plan}