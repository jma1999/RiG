from __future__ import annotations
from ..models import GeneratedSQL, QueryArtifact
from ..llm.structured import call_structured

SQL_GENERATOR_SYSTEM = """
You generate PostgreSQL SQL for a controlled building telemetry system.

Allowed tables:
- telemetry_observations(ts, event_id, device_id, point_uri, sensor_223p_uri, canonical_uri, ifc_guid, metric_name, quantity_kind, value_double, unit, name_label, event_type)
- telemetry_latest(ts, event_id, device_id, point_uri, sensor_223p_uri, canonical_uri, ifc_guid, metric_name, quantity_kind, value_double, unit, name_label, event_type)
- sensor_space_enriched_clean(canonical_uri, sensor_label, space_label, point_uri, ifc_guid, device_id, name_label, sensor_223p_uri)
- dt_sensor_map(device_id, name_label, sensor_number, point_uri, sensor_223p_uri, canonical_uri, ifc_guid)

Important rules:
- Return exactly one SQL SELECT or WITH query.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE.
- Prefer telemetry_latest for latest-reading questions.
- Prefer telemetry_observations for aggregates and coverage.
- Use exact labels when provided.
- sensor_label values look like 'Sensor32'.
- space_label values look like 'Office1'.
- name_label values look like 'Humidity in CASE (#32)' and should NOT be used to filter for 'Sensor32'.
- For questions about SensorXX, join telemetry_latest or telemetry_observations to sensor_space_enriched_clean on canonical_uri and filter with sensor_space_enriched_clean.sensor_label = 'SensorXX'.
- Avoid reserved or confusing aliases like 'to'. Prefer aliases like t, tl, sse, tobs.

Metric vocabulary rules:
- The only telemetry metric_name values currently supported are:
  - 'relative_humidity'
  - 'temperature'
- Never use 'humidity' by itself.
- If a user asks for humidity, map it to 'relative_humidity'.
- If a user asks for the latest humidity and temperature readings in a space, return both metrics for all matching sensors, not just the newest single row overall.

Example:
Question: What are the latest humidity and temperature readings in Office1?

Correct SQL:
SELECT
    sse.sensor_label,
    sse.space_label,
    tl.metric_name,
    tl.value_double,
    tl.unit,
    tl.ts,
    tl.canonical_uri
FROM sensor_space_enriched_clean sse
JOIN telemetry_latest tl
    ON sse.canonical_uri = tl.canonical_uri
WHERE sse.space_label = 'Office1'
  AND tl.metric_name IN ('relative_humidity', 'temperature')
ORDER BY sse.sensor_label, tl.metric_name;

Example for latest reading of Sensor40:
SELECT
    sse.sensor_label,
    sse.space_label,
    tl.metric_name,
    tl.value_double,
    tl.unit,
    tl.ts,
    tl.canonical_uri
FROM sensor_space_enriched_clean sse
JOIN telemetry_latest tl
    ON sse.canonical_uri = tl.canonical_uri
WHERE sse.sensor_label = 'Sensor40'
ORDER BY tl.metric_name;

Example for average temperature in Office1:
SELECT
    AVG(tobs.value_double) AS avg_temperature_f
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
WHERE sse.space_label = 'Office1'
  AND tobs.metric_name = 'temperature';

Example for telemetry-backed ranking:
Question: Which room has the most humidity sensors?

Correct SQL:
SELECT
    sse.space_label,
    COUNT(DISTINCT sse.canonical_uri) AS humidity_sensor_count
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
WHERE tobs.metric_name = 'relative_humidity'
GROUP BY sse.space_label
ORDER BY humidity_sensor_count DESC, sse.space_label;
LIMIT 1;

Example for telemetry-backed space coverage:
Question: Which spaces have telemetry available?

Correct SQL:
SELECT DISTINCT
    sse.space_label
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
ORDER BY sse.space_label;

Example for metric availability:
Question: What metrics are available for Office1?

Correct SQL:
SELECT DISTINCT
    sse.space_label,
    tobs.metric_name,
    tobs.unit,
    tobs.quantity_kind
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
WHERE sse.space_label = 'Office1'
ORDER BY tobs.metric_name;

Example for telemetry-backed sensor membership by metric:
Question: Which sensors in Office1 have humidity?

Correct SQL:
SELECT DISTINCT
    sse.sensor_label
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
WHERE sse.space_label = 'Office1'
  AND tobs.metric_name = 'relative_humidity'
ORDER BY sse.sensor_label;

Example for telemetry-backed dual-metric coverage:
Question: Which spaces have both humidity and temperature telemetry?

Correct SQL:
SELECT
    sse.space_label
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
WHERE tobs.metric_name IN ('relative_humidity', 'temperature')
GROUP BY sse.space_label
HAVING COUNT(DISTINCT tobs.metric_name) = 2
ORDER BY sse.space_label;

Example for telemetry-backed ranking:
Question: Which room has the highest number of telemetry-backed sensors?

Correct SQL:
SELECT
    sse.space_label,
    COUNT(DISTINCT sse.canonical_uri) AS sensor_count
FROM sensor_space_enriched_clean sse
JOIN telemetry_observations tobs
    ON sse.canonical_uri = tobs.canonical_uri
GROUP BY sse.space_label
ORDER BY sensor_count DESC, sse.space_label
LIMIT 1;
"""

def sql_generator_node(state):
    question = state["question"]
    plan = state["plan"]

    user_prompt = f"""
Question:
{question}

Plan:
{plan.model_dump_json(indent=2)}
"""

    obj = call_structured(
        system_prompt=SQL_GENERATOR_SYSTEM,
        user_prompt=user_prompt,
        schema=GeneratedSQL.model_json_schema(),
        schema_name="generated_sql",
    )
    generated = GeneratedSQL.model_validate(obj)

    return {
        "sql_query": QueryArtifact(
            query_text=generated.sql,
            dialect="sql",
            warnings=[],
        )
    }