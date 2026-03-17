from __future__ import annotations
from ..models import RouterOutput
from ..llm.structured import call_structured

ROUTER_SYSTEM = """
You classify building knowledge questions for a controlled retrieval system.

Return valid JSON only.

Allowed intents:
- graph_only
- timeseries_only
- graph_plus_timeseries
- unsupported

Allowed answer_type values:
- identity_lookup
- set_membership
- latest_reading
- aggregation
- coverage
- comfort_assessment
- count
- unknown

Rules:
- graph_only: asks about room/sensor/canonical identity or graph-wide counts of spaces/sensors without telemetry
- timeseries_only: asks only about telemetry values, averages, aggregates, metric availability, telemetry-backed counts, telemetry-backed membership, telemetry-backed coverage, or comfort judgements that can be derived from telemetry
- graph_plus_timeseries: needs graph grounding plus telemetry, especially when a sensor/device/room first needs semantic resolution before SQL retrieval
- unsupported: cannot be answered from the known schemas

Important:
- "How many rooms are in this project?" is a graph-only count question.
- "What is the average temperature in the office?" is a timeseries question and may require entity normalization.
- "Is the temperature in the office comfortable?" is a timeseries question with derived reasoning.
- "comfortable", "too hot", "too cold" imply derived reasoning after retrieval.
- Questions about "telemetry available", "metrics available", "have humidity", "have temperature", "have both humidity and temperature", "latest telemetry", "latest reading", "average", or "highest number of telemetry-backed sensors" are NOT graph_only.
- If the question can be answered directly by joining telemetry_observations or telemetry_latest with sensor_space_enriched_clean, prefer timeseries_only.
- Use graph_plus_timeseries only when graph grounding is truly needed first.
"""

def router_node(state):
    question = state["question"]
    obj = call_structured(
        system_prompt=ROUTER_SYSTEM,
        user_prompt=question,
        schema=RouterOutput.model_json_schema(),
        schema_name="router_output",
    )
    return {"router": RouterOutput.model_validate(obj)}