from __future__ import annotations

from ..models import GeneratedSPARQL, QueryArtifact
from ..llm.structured import call_structured

SPARQL_GENERATOR_SYSTEM = """
You generate SPARQL SELECT queries for a controlled building knowledge system.

Allowed named graphs:
- https://example.com/case-office/g/overlay
- https://example.com/case-office/g/223p

Required prefixes when relevant:
PREFIX ex: <https://example.com/case-office/align/>
PREFIX s223: <http://data.ashrae.org/standard223#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Important schema rules:
- The overlay graph contains canonical sensor entities.
- Canonical sensor labels such as Sensor32 are found with rdfs:label in the overlay graph.
- Use GRAPH <https://example.com/case-office/g/overlay> for canonical identity queries.
- Use GRAPH <https://example.com/case-office/g/223p> for physical location queries.
- If a query uses rdfs:label, you MUST include PREFIX rdfs.
- In the 223P graph, physical location is represented with:
  s223:hasPhysicalLocation
- Do not use s223:hasLocation unless explicitly present in the schema.
- If using s223 terms, you MUST include:
  PREFIX s223: <http://data.ashrae.org/standard223#>
- If using rdfs labels, you MUST include:
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
- Return exactly one SPARQL SELECT query.
- Never use INSERT, DELETE, CLEAR, LOAD, CREATE, DROP, MOVE, COPY, ADD.
- For project-wide room or space counting, count distinct labeled spaces in the 223p graph unless the planner specifies a different graph path.

Example:
Question: Which sensors are located in Office1?

Correct SPARQL:
PREFIX ex: <https://example.com/case-office/align/>
PREFIX s223: <http://data.ashrae.org/standard223#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sensor_label ?canonical_uri WHERE {
  GRAPH <https://example.com/case-office/g/overlay> {
    ?canonical_uri a ex:CanonicalSensorEntity ;
                   rdfs:label ?sensor_label ;
                   ex:aligns223p ?sensor223 .
  }

  GRAPH <https://example.com/case-office/g/223p> {
    ?sensor223 s223:hasPhysicalLocation ?space .
    ?space rdfs:label "Office1" .
  }
}
ORDER BY ?sensor_label

Example:
PREFIX ex: <https://example.com/case-office/align/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?canonical_uri WHERE {
  GRAPH <https://example.com/case-office/g/overlay> {
    ?canonical_uri a ex:CanonicalSensorEntity ;
                   rdfs:label "Sensor32" .
  }
}
LIMIT 1

Example for project-wide room count:
Question: How many rooms are in this project?

Correct SPARQL:
PREFIX s223: <http://data.ashrae.org/standard223#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT (COUNT(DISTINCT ?space) AS ?room_count) WHERE {
  GRAPH <https://example.com/case-office/g/223p> {
    ?space rdfs:label ?space_label .
  }
}
"""

def sparql_generator_node(state):
    question = state["question"]
    plan = state["plan"]
    entity_resolution = state.get("entity_resolution")

    user_prompt = f"""
Question:
{question}

Plan:
{plan.model_dump_json(indent=2)}

Entity Resolution:
{entity_resolution.model_dump_json(indent=2) if entity_resolution else "null"}
"""

    obj = call_structured(
        system_prompt=SPARQL_GENERATOR_SYSTEM,
        user_prompt=user_prompt,
        schema=GeneratedSPARQL.model_json_schema(),
        schema_name="generated_sparql",
    )
    generated = GeneratedSPARQL.model_validate(obj)

    return {
        "sparql_query": QueryArtifact(
            query_text=generated.sparql,
            dialect="sparql",
            warnings=[],
        )
    }