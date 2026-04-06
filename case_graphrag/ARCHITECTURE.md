# CASE GraphRAG — Architecture Overview

## What Is This?

CASE GraphRAG is a **retrieval-augmented generation pipeline** for answering natural-language questions about the CASE Office building. It combines two retrieval backends — a **SPARQL knowledge graph** (ASHRAE 223P ontology + a semantic overlay in GraphDB) and a **SQL relational database** (PostgreSQL telemetry tables) — and uses an LLM to dynamically route, plan, generate queries, and synthesize answers.

The pipeline is implemented as a **LangGraph state machine** where each node is an LLM call or database operation, and conditional edges encode the control flow.

---

## Pipeline Flow

```
  ┌──────────┐     ┌──────────────────┐     ┌──────────┐
  │  Router   │────▶│ Entity Resolver  │────▶│ Planner  │
  └──────────┘     └──────────────────┘     └────┬─────┘
                                                  │
                        ┌─────────────────────────┼─────────────────────┐
                        ▼                         ▼                     ▼
                 ┌──────────────┐         ┌──────────────┐       ┌──────────┐
                 │   SPARQL     │         │     SQL      │       │ Fallback │
                 │   Branch     │         │    Branch    │       └──────────┘
                 └──────┬───────┘         └──────┬───────┘
                        │                        │
                        │  (hybrid: SPARQL       │
                        │   feeds into SQL)      │
                        ▼                        ▼
                 ┌─────────────────┐    ┌────────────────────┐
                 │                 │    │ Derived Reasoning   │ (comfort questions only)
                 │                 │    └────────┬───────────┘
                 │                 │             │
                 └────────┬───────┘             │
                          ▼                     ▼
                       ┌─────────────────────────┐
                       │       Synthesis          │
                       └─────────────────────────┘
                                  │
                                  ▼
                            Final Answer
```

---

## Intents and Routing Strategy

The **Router** classifies every question into one of four intents, which determines which retrieval branches execute:

| Intent | When | Branch(es) |
|---|---|---|
| `graph_only` | Semantic identity, canonical URIs, ontology membership | SPARQL only |
| `timeseries_only` | Telemetry values, averages, latest readings, metric availability, counts | SQL only |
| `graph_plus_timeseries` | Needs graph grounding first, then telemetry | SPARQL → SQL (sequential) |
| `unsupported` | Cannot be answered from available schemas | Fallback |

---

## Node-by-Node Breakdown

### 1. Router (`nodes/router.py`)

Classifies the incoming question into an **intent** and an **answer type** (identity lookup, set membership, latest reading, aggregation, coverage, comfort assessment, count). Uses structured output to return a `RouterOutput` Pydantic model with a confidence score and short rationale.

Key routing rules:
- Questions about room/sensor identity without telemetry → `graph_only`
- Questions about telemetry values, averages, counts, metric availability, comfort → `timeseries_only`
- Questions needing graph grounding before telemetry retrieval → `graph_plus_timeseries`

### 2. Entity Resolver (`nodes/entity_resolver.py`)

Normalizes vague user references into exact schema values before any query is generated:
- `"the office"` → `"Office1"`
- `"humidity"` → `"relative_humidity"`
- Exact labels are left unchanged

This prevents downstream query generators from hallucinating non-existent entity names. The resolver knows the fixed set of space labels (Kitchen5, Meeting Room3, Office1, Reception6, Work Area & Storage2, Work Area & Storage4) and metric names (relative_humidity, temperature).

### 3. Planner (`nodes/planner.py`)

Produces a `RetrievalPlan` consisting of:
- **Intent** (echoed from the router)
- **Entity hints** — resolved space label, sensor label, device ID, metric names, aggregation function
- **Ordered steps** — each step specifies a tool (`sparql`, `sql`, or `synthesis`) and its purpose
- **Output style** — `concise`, `table`, or `hybrid`

The planner receives the router decision and entity resolutions, and decides *which tools to call and in what order*. Resolved entity labels from the entity resolver are injected into the plan's entity hints.

### 4. SPARQL Branch

Four nodes form a generate → validate → execute → repair loop:

| Node | File | Role |
|---|---|---|
| **SPARQL Generator** | `nodes/sparql_generator.py` | LLM generates a SPARQL SELECT against the overlay and/or 223p named graphs |
| **SPARQL Validator** | `validators/sparql_validator.py` | Regex-based safety checks: no mutation keywords, must be SELECT, must reference allowed graphs, required prefixes present |
| **SPARQL Executor** | `nodes/sparql_executor.py` | POSTs the query to GraphDB and parses the SPARQL JSON results |
| **SPARQL Repair** | `nodes/sparql_repair.py` | On failure, LLM receives the error context and produces a revised query (max 1 repair attempt) |

**Allowed named graphs:**
- `https://example.com/case-office/g/overlay` — canonical sensor entities, alignment links
- `https://example.com/case-office/g/223p` — physical locations, ASHRAE 223P topology

### 5. SQL Branch

Mirrors the SPARQL branch with the same generate → validate → execute → repair pattern:

| Node | File | Role |
|---|---|---|
| **SQL Generator** | `nodes/sql_generator.py` | LLM generates PostgreSQL SQL against the allowed tables |
| **SQL Validator** | `validators/sql_validator.py` | Parses with `sqlglot`, rejects non-SELECT statements and forbidden keywords, checks that at least one allowed table is referenced |
| **SQL Executor** | `nodes/sql_executor.py` | Runs via SQLAlchemy against PostgreSQL |
| **SQL Repair** | `nodes/sql_repair.py` | On failure, LLM rewrites the query with error context (max 1 repair attempt) |

**Allowed tables:**
| Table | Purpose |
|---|---|
| `telemetry_observations` | Historical sensor readings (used for aggregates, coverage) |
| `telemetry_latest` | Most recent reading per sensor (used for latest-value questions) |
| `sensor_space_enriched_clean` | Sensor-to-space mapping with canonical URIs, labels, device IDs |
| `dt_sensor_map` | Disruptive Technologies device-to-sensor mapping |

### 6. Hybrid Execution (`graph_plus_timeseries`)

When the intent is `graph_plus_timeseries`, the workflow runs **SPARQL first** to resolve semantic identity, then **SQL second** using the graph-resolved entities. The conditional routing in `workflow.py` handles this:

1. After the planner, route to `sparql_generator`
2. After SPARQL execution succeeds, route to `sql_generator`
3. After SQL execution succeeds, route to `synthesis`

**Graceful degradation:** If SPARQL returns zero rows but the plan contains a space label (from entity resolution), the pipeline continues to SQL anyway rather than failing outright. This allows SQL's `sensor_space_enriched_clean` joins to often answer the question independently.

### 7. Derived Reasoning (`nodes/derived_reasoning.py`)

An optional interpretation layer that activates for **comfort assessment** questions. After SQL retrieves temperature data, this node applies a deterministic heuristic:

| Temperature | Judgment |
|---|---|
| Below 68°F | Too cold |
| 68°F – 75°F | Comfortable |
| Above 75°F | Too hot |

The output (`judgment`, `rationale`, `applied_rule`) is passed to synthesis as an additional evidence source.

### 8. Synthesis (`nodes/synthesis.py`)

Combines all retrieved evidence — SQL rows, SPARQL rows, derived reasoning — into a final natural-language answer. Key rules:

- Does not invent data; answers only from retrieved evidence
- If both SQL and SPARQL succeed but conflict, prefers **SQL for telemetry questions** and **SPARQL for identity questions**
- Does not mention failed retrieval attempts if one successful modality already suffices
- If derived reasoning is present, uses it as the primary interpretation layer
- Summarizes tabular results in prose

### 9. Fallback (`nodes/fallback.py`)

Terminal node reached when all retrieval paths fail or the question is unsupported. Simply records `"retrieval_failed"` in the errors list.

---

## Self-Repair Mechanism

Both SPARQL and SQL branches support **one LLM-powered repair attempt** before falling to fallback. The repair loop works as follows:

1. Generator produces a query
2. Validator checks it — if invalid, route to repair (if no prior repair) or fallback
3. Executor runs it — if execution fails or returns zero rows, route to repair (if no prior repair) or fallback
4. Repair node receives the original question, plan, bad query, and failure context, then produces a revised query
5. Revised query re-enters the validator

The `sql_repair_count` and `sparql_repair_count` fields in the state track attempts and enforce the single-retry limit.

---

## Shared State

All nodes read from and write to a single `GraphState` TypedDict (`state.py`):

```python
class GraphState(TypedDict, total=False):
    question: str
    router: RouterOutput
    entity_resolution: EntityResolutionOutput
    plan: RetrievalPlan

    sparql_query: QueryArtifact
    sparql_validation: Dict[str, Any]
    sparql_result: ExecutionResult

    sql_query: QueryArtifact
    sql_validation: Dict[str, Any]
    sql_result: ExecutionResult

    sql_repair_count: int
    sparql_repair_count: int

    derived_reasoning: DerivedReasoningOutput

    final_answer: str
    evidence: Dict[str, Any]
    errors: List[str]
```

---

## LLM Integration

All LLM calls go through a single function, `call_structured()` in `llm/structured.py`, which:

1. Takes a system prompt, user prompt, and a Pydantic JSON Schema
2. Enforces OpenAI's **strict structured output** mode (adds `additionalProperties: false` and explicit `required` fields recursively)
3. Calls the OpenAI Responses API with `gpt-4.1-mini` (configurable via `OPENAI_MODEL` env var)
4. Parses the JSON response into a dict that is then validated into a Pydantic model by the calling node

This guarantees type-safe outputs at every pipeline stage with no free-text parsing.

---

## Database Clients

| Backend | File | Connection |
|---|---|---|
| GraphDB (SPARQL) | `db/graphdb.py` | HTTP POST to `GRAPHDB_ENDPOINT`, parses SPARQL JSON results |
| PostgreSQL (SQL) | `db/postgres.py` | SQLAlchemy engine using `POSTGRES_URL`, returns dicts via `text()` queries |

---

## Validation & Safety

Both validators enforce a strict **read-only sandbox**:

- **SPARQL validator** (`validators/sparql_validator.py`): Blocks `INSERT`, `DELETE`, `CLEAR`, `LOAD`, `CREATE`, `DROP`, `MOVE`, `COPY`, `ADD`. Requires SELECT and at least one allowed named graph. Checks prefix declarations.
- **SQL validator** (`validators/sql_validator.py`): Blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`. Parses with `sqlglot` to confirm SELECT/WITH. Requires at least one allowed table.

No mutation query can reach either database.

---

## Evaluation Framework

The `eval/` and `scripts/` directories provide a structured evaluation pipeline:

| File | Purpose |
|---|---|
| `eval/runner.py` | Runs the full GraphRAG pipeline on a gold evaluation set and writes predicted outputs |
| `eval/metrics.py` | Scores predictions per answer type using recall, set overlap, exact match, and numeric closeness |
| `scripts/run_eval.py` | Entry point: runs the evaluation |
| `scripts/run_scoring.py` | Computes and prints pass/partial/fail scores with root-cause analysis |
| `scripts/run_surprise.py` | Runs unseen "surprise" questions to test generalization |

**Answer-type-specific scoring functions** in `metrics.py`:
- `score_identity_lookup` — URI recall, sensor recall, space match
- `score_set_membership` — sensor set recall
- `score_latest_reading` — combined sensor, metric, URI recall
- `score_aggregation` — numeric closeness (±0.01 tolerance)
- `score_metric_availability` — metric name recall
- `score_ranking_count` — top-space exact match
- `score_coverage` — space set overlap
- `score_device_to_room` — space label match

Each produces a score (0–1), a status (`pass` / `partial` / `fail`), and a `root_cause_guess` for debugging.

---

## Directory Structure

```
case_graphrag/
├── ARCHITECTURE.md              ← this file
├── pyproject.toml               ← package metadata and dependencies
├── .env                         ← environment variables (API keys, DB URLs)
├── data/
│   ├── CASE_EvaluationSet.normalized.json   ← gold evaluation questions
│   ├── CASE_EvaluationResults.json          ← pipeline outputs per question
│   ├── CASE_EvaluationScores.json           ← scored results
│   ├── CASE_SurpriseQuestions.json          ← held-out surprise questions
│   └── CASE_SurpriseResults.json            ← surprise question outputs
└── src/case_graphrag/
    ├── state.py                 ← GraphState TypedDict
    ├── models.py                ← Pydantic models for all pipeline artifacts
    ├── config.py                ← (reserved for future configuration)
    ├── graph/
    │   └── workflow.py          ← LangGraph state machine definition
    ├── nodes/
    │   ├── router.py            ← intent classification
    │   ├── entity_resolver.py   ← vague reference normalization
    │   ├── planner.py           ← retrieval plan generation
    │   ├── sparql_generator.py  ← SPARQL query generation
    │   ├── sparql_validator.py  ← SPARQL safety checks (node wrapper)
    │   ├── sparql_executor.py   ← SPARQL execution against GraphDB
    │   ├── sparql_repair.py     ← SPARQL query repair
    │   ├── sql_generator.py     ← SQL query generation
    │   ├── sql_validator.py     ← SQL safety checks (node wrapper)
    │   ├── sql_executor.py      ← SQL execution against PostgreSQL
    │   ├── sql_repair.py        ← SQL query repair
    │   ├── derived_reasoning.py ← comfort heuristic interpretation
    │   ├── synthesis.py         ← final answer generation
    │   └── fallback.py          ← terminal failure node
    ├── validators/
    │   ├── sparql_validator.py  ← SPARQL validation logic
    │   └── sql_validator.py     ← SQL validation logic (sqlglot-based)
    ├── llm/
    │   ├── client.py            ← OpenAI client initialization
    │   └── structured.py        ← structured output wrapper
    ├── db/
    │   ├── graphdb.py           ← GraphDB HTTP client
    │   └── postgres.py          ← PostgreSQL SQLAlchemy client
    ├── eval/
    │   ├── runner.py            ← evaluation runner
    │   ├── metrics.py           ← per-answer-type scoring functions
    │   └── loader.py            ← (reserved)
    ├── tools/
    │   ├── run_sparql.py        ← (reserved)
    │   └── run_sql.py           ← (reserved)
    ├── prompts/
    │   ├── router.txt           ← (reserved, prompts are inline in nodes)
    │   ├── planner.txt
    │   ├── sparql_generator.txt
    │   ├── sql_generator.txt
    │   └── synthesis.txt
    └── scripts/
        ├── run_eval.py          ← entry point for evaluation
        ├── run_scoring.py       ← entry point for scoring
        ├── run_surprise.py      ← entry point for surprise questions
        ├── test_one.py          ← single-question test harness
        ├── trace_one.py         ← single-question tracing
        ├── test_repair.py       ← repair loop testing
        ├── test_extended_reasoning.py
        └── test_operational_reasoning.py
```
